import json

import pytest
from werkzeug.test import Client
from werkzeug.wrappers import Response

from localstack.azure.services.cosmos import CosmosSqlRouter, MicrosoftDocumentDBProvider


@pytest.fixture
def provider():
    p = MicrosoftDocumentDBProvider()
    p.data_store.ensure_account("acct1")
    p.create_sql_database("acct1", "db1")
    p.create_sql_container("acct1", "db1", "c1")
    return p


@pytest.fixture
def client(provider):
    return Client(CosmosSqlRouter(provider=provider), Response)


def test_post_item_returns_201(client):
    resp = client.post(
        "/acct1/dbs/db1/colls/c1/docs",
        data=json.dumps({"id": "1", "name": "alice"}),
        content_type="application/json",
    )
    assert resp.status_code == 201
    body = json.loads(resp.data)
    assert body["id"] == "1"
    assert body["name"] == "alice"


def test_post_item_missing_id_returns_400(client):
    resp = client.post(
        "/acct1/dbs/db1/colls/c1/docs",
        data=json.dumps({"name": "no-id"}),
        content_type="application/json",
    )
    assert resp.status_code == 400
    assert json.loads(resp.data)["code"] == "BadRequest"


def test_post_item_invalid_json_returns_400(client):
    resp = client.post(
        "/acct1/dbs/db1/colls/c1/docs",
        data=b"not json",
        content_type="application/json",
    )
    assert resp.status_code == 400


def test_post_into_missing_container_returns_404(client):
    resp = client.post(
        "/acct1/dbs/db1/colls/no-coll/docs",
        data=json.dumps({"id": "1"}),
        content_type="application/json",
    )
    assert resp.status_code == 404
    assert json.loads(resp.data)["code"] == "NotFound"


def test_get_item_returns_200(client):
    client.post(
        "/acct1/dbs/db1/colls/c1/docs",
        data=json.dumps({"id": "1", "v": 42}),
        content_type="application/json",
    )
    resp = client.get("/acct1/dbs/db1/colls/c1/docs/1")
    assert resp.status_code == 200
    assert json.loads(resp.data) == {"id": "1", "v": 42}


def test_get_missing_item_returns_404(client):
    resp = client.get("/acct1/dbs/db1/colls/c1/docs/missing")
    assert resp.status_code == 404


def test_put_item_replaces(client):
    client.post(
        "/acct1/dbs/db1/colls/c1/docs",
        data=json.dumps({"id": "1", "v": 1}),
        content_type="application/json",
    )
    resp = client.put(
        "/acct1/dbs/db1/colls/c1/docs/1",
        data=json.dumps({"id": "1", "v": 99}),
        content_type="application/json",
    )
    assert resp.status_code == 200
    assert json.loads(resp.data)["v"] == 99


def test_put_id_mismatch_returns_400(client):
    resp = client.put(
        "/acct1/dbs/db1/colls/c1/docs/1",
        data=json.dumps({"id": "different", "v": 1}),
        content_type="application/json",
    )
    assert resp.status_code == 400


def test_list_items_returns_documents_array(client):
    for i in (1, 2, 3):
        client.post(
            "/acct1/dbs/db1/colls/c1/docs",
            data=json.dumps({"id": str(i)}),
            content_type="application/json",
        )
    resp = client.get("/acct1/dbs/db1/colls/c1/docs")
    assert resp.status_code == 200
    body = json.loads(resp.data)
    assert body["_count"] == 3
    assert sorted(d["id"] for d in body["Documents"]) == ["1", "2", "3"]


def test_delete_item_returns_204(client):
    client.post(
        "/acct1/dbs/db1/colls/c1/docs",
        data=json.dumps({"id": "1"}),
        content_type="application/json",
    )
    resp = client.delete("/acct1/dbs/db1/colls/c1/docs/1")
    assert resp.status_code == 204
    assert client.get("/acct1/dbs/db1/colls/c1/docs/1").status_code == 404


def test_delete_missing_item_returns_404(client):
    resp = client.delete("/acct1/dbs/db1/colls/c1/docs/missing")
    assert resp.status_code == 404


def test_unknown_route_returns_404(client):
    assert client.get("/foo").status_code == 404
