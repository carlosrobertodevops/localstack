import base64
import json

import pytest
from werkzeug.test import Client
from werkzeug.wrappers import Response

from localstack.gcp.services.secretmanager import SecretManagerProvider, SecretManagerRouter


@pytest.fixture
def client():
    return Client(SecretManagerRouter(provider=SecretManagerProvider()), Response)


def _create(client, project="p1", sid="s1"):
    return client.post(f"/v1/projects/{project}/secrets?secretId={sid}", data=b"{}", content_type="application/json")


def _add_version(client, project="p1", sid="s1", payload=b"hello"):
    data = base64.b64encode(payload).decode("ascii")
    return client.post(
        f"/v1/projects/{project}/secrets/{sid}:addVersion",
        data=json.dumps({"payload": {"data": data}}),
        content_type="application/json",
    )


def test_create_secret(client):
    r = _create(client)
    assert r.status_code == 200
    body = json.loads(r.data)
    assert body["name"] == "projects/p1/secrets/s1"


def test_create_requires_secret_id(client):
    r = client.post("/v1/projects/p1/secrets", data=b"{}", content_type="application/json")
    assert r.status_code == 400


def test_duplicate_secret_conflict(client):
    _create(client)
    r = _create(client)
    assert r.status_code == 409


def test_list_secrets(client):
    _create(client, sid="s1")
    _create(client, sid="s2")
    r = client.get("/v1/projects/p1/secrets")
    body = json.loads(r.data)
    assert len(body["secrets"]) == 2


def test_get_secret(client):
    _create(client)
    r = client.get("/v1/projects/p1/secrets/s1")
    assert r.status_code == 200


def test_get_secret_missing(client):
    r = client.get("/v1/projects/p1/secrets/ghost")
    assert r.status_code == 404


def test_delete_secret(client):
    _create(client)
    r = client.delete("/v1/projects/p1/secrets/s1")
    assert r.status_code == 200
    r = client.get("/v1/projects/p1/secrets/s1")
    assert r.status_code == 404


def test_add_version_and_list(client):
    _create(client)
    r = _add_version(client, payload=b"v1")
    assert r.status_code == 200
    assert json.loads(r.data)["name"].endswith("/versions/1")
    _add_version(client, payload=b"v2")
    r = client.get("/v1/projects/p1/secrets/s1/versions")
    assert len(json.loads(r.data)["versions"]) == 2


def test_access_decodes_payload(client):
    _create(client)
    _add_version(client, payload=b"super-secret")
    r = client.get("/v1/projects/p1/secrets/s1/versions/1:access")
    assert r.status_code == 200
    body = json.loads(r.data)
    assert base64.b64decode(body["payload"]["data"]) == b"super-secret"


def test_access_latest_alias(client):
    _create(client)
    _add_version(client, payload=b"old")
    _add_version(client, payload=b"new")
    r = client.get("/v1/projects/p1/secrets/s1/versions/latest:access")
    assert base64.b64decode(json.loads(r.data)["payload"]["data"]) == b"new"


def test_disable_then_access_fails(client):
    _create(client)
    _add_version(client, payload=b"x")
    client.post("/v1/projects/p1/secrets/s1/versions/1:disable")
    r = client.get("/v1/projects/p1/secrets/s1/versions/1:access")
    assert r.status_code == 400


def test_enable_after_disable(client):
    _create(client)
    _add_version(client, payload=b"x")
    client.post("/v1/projects/p1/secrets/s1/versions/1:disable")
    r = client.post("/v1/projects/p1/secrets/s1/versions/1:enable")
    assert json.loads(r.data)["state"] == "ENABLED"


def test_destroy_clears_payload(client):
    _create(client)
    _add_version(client, payload=b"x")
    r = client.post("/v1/projects/p1/secrets/s1/versions/1:destroy")
    assert json.loads(r.data)["state"] == "DESTROYED"
    r = client.get("/v1/projects/p1/secrets/s1/versions/1:access")
    assert r.status_code == 400


def test_get_version(client):
    _create(client)
    _add_version(client)
    r = client.get("/v1/projects/p1/secrets/s1/versions/1")
    assert r.status_code == 200
