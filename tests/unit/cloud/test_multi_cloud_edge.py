import json

import pytest
from werkzeug.test import Client
from werkzeug.wrappers import Response

from localstack.cloud import CloudProvider, CloudRegistry, register_builtins
from localstack.cloud.edge import MultiCloudEdge


@pytest.fixture
def registry():
    r = CloudRegistry()
    register_builtins(r)
    return r


@pytest.fixture
def edge(registry):
    return MultiCloudEdge(registry=registry)


@pytest.fixture
def client(edge):
    return Client(edge, Response)


def test_azure_blob_host_routes_to_azure_gateway(client):
    # PUT container on Azure (account in path after host rewrite)
    resp = client.put(
        "/c1?restype=container",
        headers={"Host": "acct1.blob.core.windows.net"},
    )
    assert resp.status_code == 201


def test_azure_entra_host_routes_to_azure_gateway(client):
    resp = client.post(
        "/tenant-1/oauth2/v2.0/token",
        data={"grant_type": "client_credentials", "client_id": "x", "client_secret": "y"},
        headers={"Host": "login.microsoftonline.com"},
    )
    assert resp.status_code == 200
    assert "access_token" in json.loads(resp.data)


def test_unknown_host_returns_404(client):
    resp = client.get("/anything", headers={"Host": "unknown.example.com"})
    assert resp.status_code == 404
    body = json.loads(resp.data)
    assert body["error"]["code"] == "NoCloudMatched"


def test_default_cloud_fallback(registry):
    edge = MultiCloudEdge(registry=registry, default_cloud="azure")
    client = Client(edge, Response)
    # weird host with no match → fallback Azure → ARM router path
    resp = client.put(
        "/subscriptions/s1/resourceGroups/rg1",
        data=json.dumps({"location": "eastus"}),
        content_type="application/json",
        headers={"Host": "weird-host.example"},
    )
    assert resp.status_code == 200


def test_edge_caches_gateways(registry):
    calls = {"count": 0}

    class FakeGateway:
        def __init__(self):
            calls["count"] += 1

        def __call__(self, environ, start_response):
            resp = Response("ok", status=200)
            return resp(environ, start_response)

    reg = CloudRegistry()
    reg.register(
        CloudProvider(
            name="fake",
            display_name="Fake",
            package="fake",
            gateway_factory=FakeGateway,
            edge_hosts=("*.fake.local",),
        )
    )
    edge = MultiCloudEdge(registry=reg)
    client = Client(edge, Response)
    client.get("/x", headers={"Host": "a.fake.local"})
    client.get("/x", headers={"Host": "b.fake.local"})
    client.get("/x", headers={"Host": "c.fake.local"})
    assert calls["count"] == 1  # gateway built once, reused
