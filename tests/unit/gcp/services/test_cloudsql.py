import json

import pytest
from werkzeug.test import Client
from werkzeug.wrappers import Response

from localstack.gcp.services.cloudsql import CloudSqlProvider, CloudSqlRouter

P = "/sql/v1beta4/projects/p1/instances"


@pytest.fixture
def client():
    return Client(CloudSqlRouter(provider=CloudSqlProvider()), Response)


def _create(client, name="i1", tier="db-n1-standard-1"):
    return client.post(
        P,
        data=json.dumps(
            {
                "name": name,
                "region": "us-central1",
                "databaseVersion": "MYSQL_8_0",
                "settings": {"tier": tier},
            }
        ),
        content_type="application/json",
    )


def test_create_instance(client):
    r = _create(client)
    assert r.status_code == 200
    body = json.loads(r.data)
    assert body["name"] == "i1"
    assert body["state"] == "RUNNABLE"


def test_duplicate_instance(client):
    _create(client)
    r = _create(client)
    assert r.status_code == 409


def test_list_instances(client):
    _create(client, "a")
    _create(client, "b")
    r = client.get(P)
    assert len(json.loads(r.data)["items"]) == 2


def test_get_instance(client):
    _create(client)
    r = client.get(f"{P}/i1")
    assert r.status_code == 200


def test_get_instance_missing(client):
    r = client.get(f"{P}/ghost")
    assert r.status_code == 404


def test_delete_instance(client):
    _create(client)
    r = client.delete(f"{P}/i1")
    assert r.status_code == 200
    r = client.get(f"{P}/i1")
    assert r.status_code == 404


def test_patch_instance_tier(client):
    _create(client)
    r = client.patch(
        f"{P}/i1",
        data=json.dumps({"settings": {"tier": "db-n1-standard-4"}}),
        content_type="application/json",
    )
    assert json.loads(r.data)["settings"]["tier"] == "db-n1-standard-4"


def test_create_database(client):
    _create(client)
    r = client.post(
        f"{P}/i1/databases",
        data=json.dumps({"name": "appdb"}),
        content_type="application/json",
    )
    assert r.status_code == 200
    assert json.loads(r.data)["name"] == "appdb"


def test_duplicate_database(client):
    _create(client)
    body = json.dumps({"name": "appdb"})
    client.post(f"{P}/i1/databases", data=body, content_type="application/json")
    r = client.post(f"{P}/i1/databases", data=body, content_type="application/json")
    assert r.status_code == 409


def test_list_databases(client):
    _create(client)
    for n in ("a", "b"):
        client.post(
            f"{P}/i1/databases",
            data=json.dumps({"name": n}),
            content_type="application/json",
        )
    r = client.get(f"{P}/i1/databases")
    assert len(json.loads(r.data)["items"]) == 2


def test_delete_database(client):
    _create(client)
    client.post(
        f"{P}/i1/databases",
        data=json.dumps({"name": "appdb"}),
        content_type="application/json",
    )
    r = client.delete(f"{P}/i1/databases/appdb")
    assert r.status_code == 200
    r = client.get(f"{P}/i1/databases/appdb")
    assert r.status_code == 404


def test_create_user(client):
    _create(client)
    r = client.post(
        f"{P}/i1/users",
        data=json.dumps({"name": "alice", "host": "%", "password": "x"}),
        content_type="application/json",
    )
    assert r.status_code == 200
    assert json.loads(r.data)["name"] == "alice"


def test_list_users(client):
    _create(client)
    for n in ("a", "b"):
        client.post(
            f"{P}/i1/users",
            data=json.dumps({"name": n}),
            content_type="application/json",
        )
    r = client.get(f"{P}/i1/users")
    assert len(json.loads(r.data)["items"]) == 2


def test_delete_user(client):
    _create(client)
    client.post(
        f"{P}/i1/users",
        data=json.dumps({"name": "alice"}),
        content_type="application/json",
    )
    r = client.delete(f"{P}/i1/users?name=alice&host=%25")
    assert r.status_code == 200


def test_db_on_missing_instance_404(client):
    r = client.post(
        f"{P}/ghost/databases",
        data=json.dumps({"name": "x"}),
        content_type="application/json",
    )
    assert r.status_code == 404
