import json

import pytest
from werkzeug.test import Client
from werkzeug.wrappers import Response

from localstack.gcp.services.storage import CloudStorageProvider, StorageJsonRouter


@pytest.fixture
def client():
    p = CloudStorageProvider()
    return Client(StorageJsonRouter(provider=p), Response)


def test_create_bucket(client):
    r = client.post(
        "/storage/v1/b?project=p1",
        data=json.dumps({"name": "b1"}),
        content_type="application/json",
    )
    assert r.status_code == 200
    body = json.loads(r.data)
    assert body["name"] == "b1"


def test_list_buckets(client):
    client.post("/storage/v1/b?project=p1", data=json.dumps({"name": "b1"}), content_type="application/json")
    client.post("/storage/v1/b?project=p1", data=json.dumps({"name": "b2"}), content_type="application/json")
    r = client.get("/storage/v1/b?project=p1")
    body = json.loads(r.data)
    names = {b["name"] for b in body["items"]}
    assert names == {"b1", "b2"}


def test_create_bucket_missing_project(client):
    r = client.post("/storage/v1/b", data=json.dumps({"name": "b1"}), content_type="application/json")
    assert r.status_code == 400


def test_create_bucket_missing_name(client):
    r = client.post("/storage/v1/b?project=p1", data=json.dumps({}), content_type="application/json")
    assert r.status_code == 400


def test_get_delete_bucket(client):
    client.post("/storage/v1/b?project=p1", data=json.dumps({"name": "b1"}), content_type="application/json")
    r = client.get("/storage/v1/b/b1")
    assert r.status_code == 200
    r = client.delete("/storage/v1/b/b1")
    assert r.status_code == 204
    r = client.get("/storage/v1/b/b1")
    assert r.status_code == 404


def test_upload_and_download_object(client):
    client.post("/storage/v1/b?project=p1", data=json.dumps({"name": "b1"}), content_type="application/json")
    r = client.post("/upload/storage/v1/b/b1/o?name=hello.txt", data=b"hello world", content_type="text/plain")
    assert r.status_code == 200
    meta = json.loads(r.data)
    assert meta["size"] == "11"

    r = client.get("/storage/v1/b/b1/o/hello.txt?alt=media")
    assert r.status_code == 200
    assert r.data == b"hello world"


def test_get_object_metadata(client):
    client.post("/storage/v1/b?project=p1", data=json.dumps({"name": "b1"}), content_type="application/json")
    client.post("/upload/storage/v1/b/b1/o?name=k", data=b"x")
    r = client.get("/storage/v1/b/b1/o/k")
    assert r.status_code == 200
    assert json.loads(r.data)["name"] == "k"


def test_list_objects(client):
    client.post("/storage/v1/b?project=p1", data=json.dumps({"name": "b1"}), content_type="application/json")
    for i in range(3):
        client.post(f"/upload/storage/v1/b/b1/o?name=k{i}", data=b"v")
    r = client.get("/storage/v1/b/b1/o")
    items = json.loads(r.data)["items"]
    assert {o["name"] for o in items} == {"k0", "k1", "k2"}


def test_delete_object(client):
    client.post("/storage/v1/b?project=p1", data=json.dumps({"name": "b1"}), content_type="application/json")
    client.post("/upload/storage/v1/b/b1/o?name=k", data=b"v")
    r = client.delete("/storage/v1/b/b1/o/k")
    assert r.status_code == 204
    r = client.get("/storage/v1/b/b1/o/k")
    assert r.status_code == 404


def test_get_missing_object(client):
    client.post("/storage/v1/b?project=p1", data=json.dumps({"name": "b1"}), content_type="application/json")
    r = client.get("/storage/v1/b/b1/o/missing")
    assert r.status_code == 404


def test_delete_nonempty_bucket_fails(client):
    client.post("/storage/v1/b?project=p1", data=json.dumps({"name": "b1"}), content_type="application/json")
    client.post("/upload/storage/v1/b/b1/o?name=k", data=b"v")
    r = client.delete("/storage/v1/b/b1")
    assert r.status_code == 400


def test_duplicate_bucket_conflict(client):
    client.post("/storage/v1/b?project=p1", data=json.dumps({"name": "b1"}), content_type="application/json")
    r = client.post("/storage/v1/b?project=p1", data=json.dumps({"name": "b1"}), content_type="application/json")
    assert r.status_code == 409
