import json

import pytest
from werkzeug.test import Client
from werkzeug.wrappers import Response

from localstack.azure.services.tablestorage import TableStorageProvider, TableStorageRouter


@pytest.fixture
def provider():
    return TableStorageProvider()


@pytest.fixture
def client(provider):
    return Client(TableStorageRouter(provider=provider), Response)


# -- provider --


def test_provider_create_table(provider):
    t = provider.create_table("acct1", "MyTable")
    assert t.name == "MyTable"


def test_provider_create_table_duplicate_raises(provider):
    from localstack.azure.exceptions import AzureInvalidRequest

    provider.create_table("acct1", "T")
    with pytest.raises(AzureInvalidRequest):
        provider.create_table("acct1", "T")


def test_provider_upsert_get_delete_entity(provider):
    from localstack.azure.exceptions import AzureNotFound

    provider.create_table("acct1", "T")
    entity = {"PartitionKey": "p", "RowKey": "1", "Name": "Alice"}
    provider.upsert_entity("acct1", "T", entity)
    got = provider.get_entity("acct1", "T", "p", "1")
    assert got["Name"] == "Alice"
    provider.delete_entity("acct1", "T", "p", "1")
    with pytest.raises(AzureNotFound):
        provider.get_entity("acct1", "T", "p", "1")


def test_provider_query_filters_by_partition_key(provider):
    provider.create_table("acct1", "T")
    for i, pk in enumerate(["p1", "p1", "p2"]):
        provider.upsert_entity("acct1", "T", {"PartitionKey": pk, "RowKey": str(i)})
    p1 = provider.query_entities("acct1", "T", partition_key="p1")
    assert len(p1) == 2
    all_entities = provider.query_entities("acct1", "T")
    assert len(all_entities) == 3


def test_provider_entity_requires_keys(provider):
    from localstack.azure.exceptions import AzureInvalidRequest

    provider.create_table("acct1", "T")
    with pytest.raises(AzureInvalidRequest):
        provider.upsert_entity("acct1", "T", {"Name": "X"})


# -- REST --


def test_rest_create_table_returns_201(client):
    resp = client.post(
        "/acct1/Tables",
        data=json.dumps({"TableName": "T"}),
        content_type="application/json",
    )
    assert resp.status_code == 201
    assert json.loads(resp.data)["TableName"] == "T"


def test_rest_list_tables(client):
    for n in ("A", "B"):
        client.post(
            "/acct1/Tables", data=json.dumps({"TableName": n}), content_type="application/json"
        )
    resp = client.get("/acct1/Tables")
    names = sorted(t["TableName"] for t in json.loads(resp.data)["value"])
    assert names == ["A", "B"]


def test_rest_delete_table(client):
    client.post(
        "/acct1/Tables", data=json.dumps({"TableName": "T"}), content_type="application/json"
    )
    resp = client.delete("/acct1/Tables('T')")
    assert resp.status_code == 204


def test_rest_upsert_entity(client):
    client.post(
        "/acct1/Tables", data=json.dumps({"TableName": "T"}), content_type="application/json"
    )
    resp = client.post(
        "/acct1/T()",
        data=json.dumps({"PartitionKey": "p", "RowKey": "1", "Name": "X"}),
        content_type="application/json",
    )
    assert resp.status_code == 201
    body = json.loads(resp.data)
    assert body["Name"] == "X"


def test_rest_get_entity_by_keys(client):
    client.post(
        "/acct1/Tables", data=json.dumps({"TableName": "T"}), content_type="application/json"
    )
    client.post(
        "/acct1/T()",
        data=json.dumps({"PartitionKey": "p", "RowKey": "1", "Name": "X"}),
        content_type="application/json",
    )
    resp = client.get("/acct1/T(PartitionKey='p',RowKey='1')")
    assert resp.status_code == 200
    assert json.loads(resp.data)["Name"] == "X"


def test_rest_query_with_filter(client):
    client.post(
        "/acct1/Tables", data=json.dumps({"TableName": "T"}), content_type="application/json"
    )
    for i, pk in enumerate(["a", "a", "b"]):
        client.post(
            "/acct1/T()",
            data=json.dumps({"PartitionKey": pk, "RowKey": str(i)}),
            content_type="application/json",
        )
    resp = client.get("/acct1/T()?$filter=PartitionKey%20eq%20%27a%27")
    body = json.loads(resp.data)
    assert len(body["value"]) == 2


def test_rest_delete_entity(client):
    client.post(
        "/acct1/Tables", data=json.dumps({"TableName": "T"}), content_type="application/json"
    )
    client.post(
        "/acct1/T()",
        data=json.dumps({"PartitionKey": "p", "RowKey": "1"}),
        content_type="application/json",
    )
    assert client.delete("/acct1/T(PartitionKey='p',RowKey='1')").status_code == 204
    assert client.get("/acct1/T(PartitionKey='p',RowKey='1')").status_code == 404


def test_rest_unknown_path(client):
    assert client.get("/acct1/random").status_code == 404


def test_rest_create_table_missing_name_returns_400(client):
    resp = client.post(
        "/acct1/Tables", data=json.dumps({}), content_type="application/json"
    )
    assert resp.status_code == 400
