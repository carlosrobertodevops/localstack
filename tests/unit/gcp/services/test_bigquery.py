import json

import pytest
from werkzeug.test import Client
from werkzeug.wrappers import Response

from localstack.gcp.services.bigquery import BigQueryProvider, BigQueryRouter

P = "/bigquery/v2/projects/p1"


@pytest.fixture
def client():
    return Client(BigQueryRouter(provider=BigQueryProvider()), Response)


def _create_ds(client, ds="ds1", location="US"):
    return client.post(
        f"{P}/datasets",
        data=json.dumps(
            {"datasetReference": {"datasetId": ds, "projectId": "p1"}, "location": location}
        ),
        content_type="application/json",
    )


def _create_table(client, ds="ds1", tbl="t1", schema=None):
    return client.post(
        f"{P}/datasets/{ds}/tables",
        data=json.dumps(
            {
                "tableReference": {"projectId": "p1", "datasetId": ds, "tableId": tbl},
                "schema": schema or {"fields": [{"name": "x", "type": "STRING"}]},
            }
        ),
        content_type="application/json",
    )


def test_create_dataset(client):
    r = _create_ds(client)
    assert r.status_code == 200
    body = json.loads(r.data)
    assert body["datasetReference"]["datasetId"] == "ds1"


def test_duplicate_dataset(client):
    _create_ds(client)
    r = _create_ds(client)
    assert r.status_code == 409


def test_list_datasets(client):
    _create_ds(client, "a")
    _create_ds(client, "b")
    r = client.get(f"{P}/datasets")
    assert len(json.loads(r.data)["datasets"]) == 2


def test_get_dataset(client):
    _create_ds(client)
    r = client.get(f"{P}/datasets/ds1")
    assert r.status_code == 200


def test_get_dataset_missing(client):
    r = client.get(f"{P}/datasets/ghost")
    assert r.status_code == 404


def test_delete_dataset(client):
    _create_ds(client)
    r = client.delete(f"{P}/datasets/ds1")
    assert r.status_code == 200
    r = client.get(f"{P}/datasets/ds1")
    assert r.status_code == 404


def test_create_table(client):
    _create_ds(client)
    r = _create_table(client)
    assert r.status_code == 200
    body = json.loads(r.data)
    assert body["tableReference"]["tableId"] == "t1"


def test_list_tables(client):
    _create_ds(client)
    _create_table(client, tbl="a")
    _create_table(client, tbl="b")
    r = client.get(f"{P}/datasets/ds1/tables")
    assert len(json.loads(r.data)["tables"]) == 2


def test_delete_table(client):
    _create_ds(client)
    _create_table(client)
    r = client.delete(f"{P}/datasets/ds1/tables/t1")
    assert r.status_code == 200
    r = client.get(f"{P}/datasets/ds1/tables/t1")
    assert r.status_code == 404


def test_insert_all_increments_num_rows(client):
    _create_ds(client)
    _create_table(client)
    r = client.post(
        f"{P}/datasets/ds1/tables/t1/insertAll",
        data=json.dumps({"rows": [{"json": {"x": "a"}}, {"json": {"x": "b"}}]}),
        content_type="application/json",
    )
    assert r.status_code == 200
    assert json.loads(r.data)["inserted"] == 2
    r = client.get(f"{P}/datasets/ds1/tables/t1")
    assert json.loads(r.data)["numRows"] == "2"


def test_query_job_done(client):
    r = client.post(
        f"{P}/jobs",
        data=json.dumps({"configuration": {"query": {"query": "SELECT 1"}}}),
        content_type="application/json",
    )
    body = json.loads(r.data)
    assert body["status"]["state"] == "DONE"
    assert body["configuration"]["query"]["query"] == "SELECT 1"


def test_get_job(client):
    r = client.post(
        f"{P}/jobs",
        data=json.dumps({"configuration": {"query": {"query": "SELECT 1"}}}),
        content_type="application/json",
    )
    job_id = json.loads(r.data)["jobReference"]["jobId"]
    r = client.get(f"{P}/jobs/{job_id}")
    assert r.status_code == 200


def test_table_in_missing_dataset_404(client):
    r = _create_table(client, ds="ghost")
    assert r.status_code == 404


def test_delete_dataset_cascades_tables(client):
    _create_ds(client)
    _create_table(client)
    client.delete(f"{P}/datasets/ds1")
    _create_ds(client)
    r = client.get(f"{P}/datasets/ds1/tables")
    assert json.loads(r.data) == {"tables": []}
