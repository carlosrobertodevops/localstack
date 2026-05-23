import json

import pytest
from werkzeug.test import Client
from werkzeug.wrappers import Response

from localstack.gcp.gateway import GcpGateway


@pytest.fixture
def client():
    return Client(GcpGateway(), Response)


def test_storage_json_via_host(client):
    r = client.post(
        "/storage/v1/b?project=p1",
        data=json.dumps({"name": "b1"}),
        content_type="application/json",
        headers={"Host": "storage.googleapis.com"},
    )
    assert r.status_code == 200


def test_storage_xml_via_host(client):
    r = client.put(
        "/b-xml",
        headers={"Host": "storage.googleapis.com", "x-goog-project-id": "p1"},
    )
    assert r.status_code == 200


def test_pubsub_via_host(client):
    r = client.put(
        "/v1/projects/p1/topics/t1",
        headers={"Host": "pubsub.googleapis.com"},
    )
    assert r.status_code == 200


def test_firestore_via_host(client):
    r = client.post(
        "/v1/projects/p1/databases?databaseId=(default)",
        data=b"{}",
        content_type="application/json",
        headers={"Host": "firestore.googleapis.com"},
    )
    assert r.status_code == 200


def test_iam_token_via_host(client):
    r = client.post(
        "/token",
        data={"grant_type": "client_credentials"},
        headers={"Host": "oauth2.googleapis.com"},
    )
    assert r.status_code == 200


def test_functions_control_via_host(client):
    r = client.post(
        "/v2/projects/p1/locations/us-central1/functions?functionId=fn",
        data=b"{}",
        content_type="application/json",
        headers={"Host": "cloudfunctions.googleapis.com"},
    )
    assert r.status_code == 200


def test_functions_http_invoke_via_host(client):
    client.post(
        "/v2/projects/p1/locations/us-central1/functions?functionId=fn",
        data=b"{}",
        content_type="application/json",
        headers={"Host": "cloudfunctions.googleapis.com"},
    )
    gw = client.application
    gw.functions_provider.attach_handler(
        "projects/p1/locations/us-central1/functions/fn",
        lambda env, body: (200, {}, b"ok"),
    )
    r = client.get("/fn", headers={"Host": "us-central1-p1.cloudfunctions.net"})
    assert r.status_code == 200
    assert r.data == b"ok"


def test_unknown_host_returns_404(client):
    r = client.get("/whatever", headers={"Host": "unknown.example.com"})
    assert r.status_code == 404


def test_path_fallback_no_host(client):
    r = client.post(
        "/storage/v1/b?project=p1",
        data=json.dumps({"name": "b-path"}),
        content_type="application/json",
    )
    assert r.status_code == 200
