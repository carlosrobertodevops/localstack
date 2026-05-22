from xml.etree import ElementTree as ET

import pytest
from werkzeug.test import Client
from werkzeug.wrappers import Response

from localstack.azure.services.storage import BlobRouter, MicrosoftStorageProvider


@pytest.fixture
def provider():
    return MicrosoftStorageProvider()


@pytest.fixture
def client(provider):
    return Client(BlobRouter(provider=provider), Response)


def test_put_container_returns_201(client):
    resp = client.put("/acct1/c1?restype=container")
    assert resp.status_code == 201
    assert resp.headers.get("x-ms-version")
    assert resp.headers.get("x-ms-request-id")


def test_put_container_idempotent_returns_409(client):
    client.put("/acct1/c1?restype=container")
    resp = client.put("/acct1/c1?restype=container")
    assert resp.status_code == 409
    body = ET.fromstring(resp.data)
    assert body.tag == "Error"
    assert body.findtext("Code") == "ContainerAlreadyExists"


def test_delete_container_returns_202(client):
    client.put("/acct1/c1?restype=container")
    resp = client.delete("/acct1/c1?restype=container")
    assert resp.status_code == 202


def test_delete_missing_container_returns_404(client):
    resp = client.delete("/acct1/missing?restype=container")
    assert resp.status_code == 404
    body = ET.fromstring(resp.data)
    assert body.findtext("Code") == "ContainerNotFound"


def test_put_blob_returns_201_with_etag(client):
    client.put("/acct1/c1?restype=container")
    resp = client.put(
        "/acct1/c1/hello.txt",
        data=b"hello",
        headers={"x-ms-blob-type": "BlockBlob", "Content-Type": "text/plain"},
    )
    assert resp.status_code == 201
    assert resp.headers.get("ETag")
    assert resp.headers.get("Last-Modified")


def test_put_blob_requires_blob_type(client):
    client.put("/acct1/c1?restype=container")
    resp = client.put("/acct1/c1/x", data=b"a")
    assert resp.status_code == 400
    body = ET.fromstring(resp.data)
    assert body.findtext("Code") == "MissingRequiredHeader"


def test_put_blob_into_missing_container_returns_404(client):
    resp = client.put(
        "/acct1/no-c/x",
        data=b"a",
        headers={"x-ms-blob-type": "BlockBlob"},
    )
    assert resp.status_code == 404
    body = ET.fromstring(resp.data)
    assert body.findtext("Code") == "ContainerNotFound"


def test_get_blob_returns_body_and_metadata(client):
    client.put("/acct1/c1?restype=container")
    client.put(
        "/acct1/c1/foo",
        data=b"abc",
        headers={
            "x-ms-blob-type": "BlockBlob",
            "Content-Type": "application/octet-stream",
            "x-ms-meta-Owner": "alice",
        },
    )
    resp = client.get("/acct1/c1/foo")
    assert resp.status_code == 200
    assert resp.data == b"abc"
    assert resp.headers.get("Content-Type") == "application/octet-stream"
    assert resp.headers.get("x-ms-meta-Owner") == "alice"
    assert resp.headers.get("ETag")


def test_head_blob_returns_headers_no_body(client):
    client.put("/acct1/c1?restype=container")
    client.put("/acct1/c1/foo", data=b"abc", headers={"x-ms-blob-type": "BlockBlob"})
    resp = client.head("/acct1/c1/foo")
    assert resp.status_code == 200
    assert resp.data == b""
    assert resp.headers.get("Content-Length") == "3"


def test_get_missing_blob_returns_404(client):
    client.put("/acct1/c1?restype=container")
    resp = client.get("/acct1/c1/missing")
    assert resp.status_code == 404
    body = ET.fromstring(resp.data)
    assert body.findtext("Code") == "BlobNotFound"


def test_delete_blob_returns_202(client):
    client.put("/acct1/c1?restype=container")
    client.put("/acct1/c1/foo", data=b"abc", headers={"x-ms-blob-type": "BlockBlob"})
    resp = client.delete("/acct1/c1/foo")
    assert resp.status_code == 202
    assert client.get("/acct1/c1/foo").status_code == 404


def test_list_blobs_returns_xml(client):
    client.put("/acct1/c1?restype=container")
    for name in ("a.txt", "b.txt"):
        client.put(
            f"/acct1/c1/{name}",
            data=b"x",
            headers={"x-ms-blob-type": "BlockBlob"},
        )
    resp = client.get("/acct1/c1?restype=container&comp=list")
    assert resp.status_code == 200
    assert resp.headers["Content-Type"].startswith("application/xml")
    root = ET.fromstring(resp.data)
    assert root.tag == "EnumerationResults"
    names = sorted(b.findtext("Name") for b in root.findall(".//Blob"))
    assert names == ["a.txt", "b.txt"]


def test_list_blobs_supports_prefix(client):
    client.put("/acct1/c1?restype=container")
    for name in ("foo/1", "foo/2", "bar/1"):
        client.put(
            f"/acct1/c1/{name}",
            data=b"x",
            headers={"x-ms-blob-type": "BlockBlob"},
        )
    resp = client.get("/acct1/c1?restype=container&comp=list&prefix=foo/")
    root = ET.fromstring(resp.data)
    names = sorted(b.findtext("Name") for b in root.findall(".//Blob"))
    assert names == ["foo/1", "foo/2"]


def test_unknown_method_returns_405(client):
    resp = client.open("/acct1/c1/blob", method="PATCH", data=b"x")
    assert resp.status_code == 405
