import xml.etree.ElementTree as ET

import pytest
from werkzeug.test import Client
from werkzeug.wrappers import Response

from localstack.gcp.services.storage import CloudStorageProvider, StorageXmlRouter


@pytest.fixture
def client():
    return Client(StorageXmlRouter(provider=CloudStorageProvider()), Response)


def test_put_bucket(client):
    r = client.put("/b1", headers={"x-goog-project-id": "p1"})
    assert r.status_code == 200


def test_put_object_and_get(client):
    client.put("/b1", headers={"x-goog-project-id": "p1"})
    r = client.put("/b1/key.txt", data=b"hello", content_type="text/plain")
    assert r.status_code == 200
    r = client.get("/b1/key.txt")
    assert r.status_code == 200
    assert r.data == b"hello"


def test_list_objects_xml(client):
    client.put("/b1", headers={"x-goog-project-id": "p1"})
    client.put("/b1/a", data=b"1")
    client.put("/b1/b", data=b"2")
    r = client.get("/b1")
    assert r.status_code == 200
    root = ET.fromstring(r.data)
    keys = {e.find("Key").text for e in root.findall("Contents")}
    assert keys == {"a", "b"}


def test_delete_object(client):
    client.put("/b1", headers={"x-goog-project-id": "p1"})
    client.put("/b1/k", data=b"x")
    r = client.delete("/b1/k")
    assert r.status_code == 204


def test_delete_bucket(client):
    client.put("/b1", headers={"x-goog-project-id": "p1"})
    r = client.delete("/b1")
    assert r.status_code == 204


def test_get_missing_object_returns_xml_error(client):
    client.put("/b1", headers={"x-goog-project-id": "p1"})
    r = client.get("/b1/missing")
    assert r.status_code == 404
    root = ET.fromstring(r.data)
    assert root.tag == "Error"
    assert root.find("Code").text == "NoSuchKey"
