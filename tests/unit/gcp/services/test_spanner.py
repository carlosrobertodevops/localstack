import json

import pytest
from werkzeug.test import Client
from werkzeug.wrappers import Response

from localstack.gcp.services.spanner import SpannerProvider, SpannerRouter

P = "/v1/projects/p1/instances"


@pytest.fixture
def client():
    return Client(SpannerRouter(provider=SpannerProvider()), Response)


def _create_inst(client, iid="i1"):
    return client.post(
        P,
        data=json.dumps(
            {
                "instanceId": iid,
                "instance": {
                    "config": "projects/_/instanceConfigs/regional-us-central1",
                    "displayName": iid,
                    "nodeCount": 1,
                },
            }
        ),
        content_type="application/json",
    )


def _create_db(client, iid="i1", db="db1"):
    return client.post(
        f"{P}/{iid}/databases",
        data=json.dumps({"databaseId": db}),
        content_type="application/json",
    )


def test_create_instance(client):
    r = _create_inst(client)
    assert r.status_code == 200
    assert json.loads(r.data)["name"].endswith("/instances/i1")


def test_duplicate_instance(client):
    _create_inst(client)
    r = _create_inst(client)
    assert r.status_code == 409


def test_list_instances(client):
    _create_inst(client, "a")
    _create_inst(client, "b")
    r = client.get(P)
    assert len(json.loads(r.data)["instances"]) == 2


def test_delete_instance(client):
    _create_inst(client)
    r = client.delete(f"{P}/i1")
    assert r.status_code == 200


def test_create_database(client):
    _create_inst(client)
    r = _create_db(client)
    assert r.status_code == 200
    assert json.loads(r.data)["name"].endswith("/databases/db1")


def test_create_database_via_create_statement(client):
    _create_inst(client)
    r = client.post(
        f"{P}/i1/databases",
        data=json.dumps({"createStatement": "CREATE DATABASE `mydb`"}),
        content_type="application/json",
    )
    assert json.loads(r.data)["name"].endswith("/databases/mydb")


def test_duplicate_database(client):
    _create_inst(client)
    _create_db(client)
    r = _create_db(client)
    assert r.status_code == 409


def test_list_databases(client):
    _create_inst(client)
    _create_db(client, db="a")
    _create_db(client, db="b")
    r = client.get(f"{P}/i1/databases")
    assert len(json.loads(r.data)["databases"]) == 2


def test_delete_database(client):
    _create_inst(client)
    _create_db(client)
    r = client.delete(f"{P}/i1/databases/db1")
    assert r.status_code == 200


def test_update_ddl(client):
    _create_inst(client)
    _create_db(client)
    r = client.patch(
        f"{P}/i1/databases/db1/ddl",
        data=json.dumps({"statements": ["CREATE TABLE t (id INT64)"]}),
        content_type="application/json",
    )
    assert r.status_code == 200


def test_create_session(client):
    _create_inst(client)
    _create_db(client)
    r = client.post(f"{P}/i1/databases/db1/sessions")
    assert r.status_code == 200
    assert "/sessions/" in json.loads(r.data)["name"]


def test_list_sessions(client):
    _create_inst(client)
    _create_db(client)
    for _ in range(2):
        client.post(f"{P}/i1/databases/db1/sessions")
    r = client.get(f"{P}/i1/databases/db1/sessions")
    assert len(json.loads(r.data)["sessions"]) == 2


def test_execute_sql_returns_empty_rows(client):
    _create_inst(client)
    _create_db(client)
    r = client.post(f"{P}/i1/databases/db1/sessions")
    sess_name = json.loads(r.data)["name"]
    sid = sess_name.rsplit("/", 1)[-1]
    r = client.post(
        f"{P}/i1/databases/db1/sessions/{sid}:executeSql",
        data=json.dumps({"sql": "SELECT 1"}),
        content_type="application/json",
    )
    assert r.status_code == 200
    body = json.loads(r.data)
    assert body["rows"] == []


def test_delete_session(client):
    _create_inst(client)
    _create_db(client)
    r = client.post(f"{P}/i1/databases/db1/sessions")
    sid = json.loads(r.data)["name"].rsplit("/", 1)[-1]
    r = client.delete(f"{P}/i1/databases/db1/sessions/{sid}")
    assert r.status_code == 200


def test_execute_sql_invalid_session(client):
    _create_inst(client)
    _create_db(client)
    r = client.post(
        f"{P}/i1/databases/db1/sessions/ghost:executeSql",
        data=json.dumps({"sql": "SELECT 1"}),
        content_type="application/json",
    )
    assert r.status_code == 404
