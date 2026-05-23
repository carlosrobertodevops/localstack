import json

import pytest
from werkzeug.test import Client
from werkzeug.wrappers import Response

from localstack.gcp.services.firestore import FirestoreProvider, FirestoreRouter


@pytest.fixture
def client():
    return Client(FirestoreRouter(provider=FirestoreProvider()), Response)


def test_create_database(client):
    r = client.post(
        "/v1/projects/p1/databases?databaseId=(default)",
        data=json.dumps({"locationId": "nam5"}),
        content_type="application/json",
    )
    assert r.status_code == 200
    body = json.loads(r.data)
    assert body["name"] == "projects/p1/databases/(default)"


def test_get_database(client):
    client.post("/v1/projects/p1/databases?databaseId=(default)", data=b"{}", content_type="application/json")
    r = client.get("/v1/projects/p1/databases/(default)")
    assert r.status_code == 200


def test_get_database_missing(client):
    r = client.get("/v1/projects/p1/databases/(default)")
    assert r.status_code == 404


def test_create_document_with_id(client):
    client.post("/v1/projects/p1/databases?databaseId=(default)", data=b"{}", content_type="application/json")
    r = client.post(
        "/v1/projects/p1/databases/(default)/documents/users?documentId=u1",
        data=json.dumps({"fields": {"name": {"stringValue": "Alice"}}}),
        content_type="application/json",
    )
    assert r.status_code == 200
    body = json.loads(r.data)
    assert body["name"].endswith("/u1")


def test_create_document_autogen_id(client):
    client.post("/v1/projects/p1/databases?databaseId=(default)", data=b"{}", content_type="application/json")
    r = client.post(
        "/v1/projects/p1/databases/(default)/documents/users",
        data=json.dumps({"fields": {}}),
        content_type="application/json",
    )
    assert r.status_code == 200
    name = json.loads(r.data)["name"]
    assert "/users/" in name


def test_get_document(client):
    client.post("/v1/projects/p1/databases?databaseId=(default)", data=b"{}", content_type="application/json")
    client.post(
        "/v1/projects/p1/databases/(default)/documents/users?documentId=u1",
        data=json.dumps({"fields": {"a": {"stringValue": "b"}}}),
        content_type="application/json",
    )
    r = client.get("/v1/projects/p1/databases/(default)/documents/users/u1")
    assert r.status_code == 200
    body = json.loads(r.data)
    assert body["fields"]["a"]["stringValue"] == "b"


def test_patch_document_merges_fields(client):
    client.post("/v1/projects/p1/databases?databaseId=(default)", data=b"{}", content_type="application/json")
    client.post(
        "/v1/projects/p1/databases/(default)/documents/users?documentId=u1",
        data=json.dumps({"fields": {"a": {"stringValue": "1"}}}),
        content_type="application/json",
    )
    r = client.patch(
        "/v1/projects/p1/databases/(default)/documents/users/u1",
        data=json.dumps({"fields": {"b": {"stringValue": "2"}}}),
        content_type="application/json",
    )
    assert r.status_code == 200
    fields = json.loads(r.data)["fields"]
    assert fields["a"]["stringValue"] == "1"
    assert fields["b"]["stringValue"] == "2"


def test_delete_document(client):
    client.post("/v1/projects/p1/databases?databaseId=(default)", data=b"{}", content_type="application/json")
    client.post(
        "/v1/projects/p1/databases/(default)/documents/users?documentId=u1",
        data=json.dumps({"fields": {}}),
        content_type="application/json",
    )
    r = client.delete("/v1/projects/p1/databases/(default)/documents/users/u1")
    assert r.status_code == 200
    r = client.get("/v1/projects/p1/databases/(default)/documents/users/u1")
    assert r.status_code == 404


def test_list_documents(client):
    client.post("/v1/projects/p1/databases?databaseId=(default)", data=b"{}", content_type="application/json")
    for i in range(3):
        client.post(
            f"/v1/projects/p1/databases/(default)/documents/users?documentId=u{i}",
            data=json.dumps({"fields": {}}),
            content_type="application/json",
        )
    r = client.get("/v1/projects/p1/databases/(default)/documents/users")
    docs = json.loads(r.data)["documents"]
    assert len(docs) == 3


def test_get_missing_document(client):
    client.post("/v1/projects/p1/databases?databaseId=(default)", data=b"{}", content_type="application/json")
    r = client.get("/v1/projects/p1/databases/(default)/documents/users/ghost")
    assert r.status_code == 404


def test_duplicate_document_conflict(client):
    client.post("/v1/projects/p1/databases?databaseId=(default)", data=b"{}", content_type="application/json")
    client.post(
        "/v1/projects/p1/databases/(default)/documents/users?documentId=u1",
        data=json.dumps({"fields": {}}),
        content_type="application/json",
    )
    r = client.post(
        "/v1/projects/p1/databases/(default)/documents/users?documentId=u1",
        data=json.dumps({"fields": {}}),
        content_type="application/json",
    )
    assert r.status_code == 409
