import json
from xml.etree import ElementTree as ET

import pytest
from werkzeug.test import Client
from werkzeug.wrappers import Response

from localstack.azure.gateway import AzureGateway


@pytest.fixture
def gateway():
    return AzureGateway()


@pytest.fixture
def client(gateway):
    return Client(gateway, Response)


def test_arm_resource_group_through_gateway(client):
    resp = client.put(
        "/subscriptions/s1/resourceGroups/rg1",
        data=json.dumps({"location": "eastus"}),
        content_type="application/json",
    )
    assert resp.status_code == 200
    assert json.loads(resp.data)["name"] == "rg1"


def test_blob_via_host_routing(client):
    # real Azure URL = https://acct1.blob.core.windows.net/c1?restype=container
    client.put("/c1?restype=container", headers={"Host": "acct1.blob.core.windows.net"})
    put = client.put(
        "/c1/x",
        data=b"hi",
        headers={"Host": "acct1.blob.core.windows.net", "x-ms-blob-type": "BlockBlob"},
    )
    assert put.status_code == 201
    get = client.get("/c1/x", headers={"Host": "acct1.blob.core.windows.net"})
    assert get.status_code == 200
    assert get.data == b"hi"


def test_queue_via_host_routing(client):
    client.put("/q1", headers={"Host": "acct1.queue.core.windows.net"})
    enqueue_body = (
        b'<?xml version="1.0" encoding="utf-8"?>'
        b"<QueueMessage><MessageText>hi</MessageText></QueueMessage>"
    )
    resp = client.post(
        "/q1/messages",
        data=enqueue_body,
        content_type="application/xml",
        headers={"Host": "acct1.queue.core.windows.net"},
    )
    assert resp.status_code == 201


def test_function_invoke_via_host_routing(gateway, client):
    scope = gateway.functions_provider.resource_manager
    from localstack.azure.scope import AzureScope

    s = AzureScope.for_resource_group("sub-1", "rg-dev", location="eastus")
    scope.create_or_update_resource_group(s, "rg-dev", {"location": "eastus"})
    gateway.functions_provider.create_function_app(s, "app1", {"location": "eastus"})
    gateway.functions_registry.register("app1", "hello", lambda req: {"body": "world"})

    resp = client.get("/api/hello", headers={"Host": "app1.azurewebsites.net"})
    assert resp.status_code == 200
    assert resp.data == b"world"


def test_cosmos_via_host_routing(gateway, client):
    gateway.cosmos_provider.data_store.ensure_account("c1")
    gateway.cosmos_provider.create_sql_database("c1", "db1")
    gateway.cosmos_provider.create_sql_container("c1", "db1", "col1")

    resp = client.post(
        "/dbs/db1/colls/col1/docs",
        data=json.dumps({"id": "1"}),
        content_type="application/json",
        headers={"Host": "c1.documents.azure.com"},
    )
    assert resp.status_code == 201


def test_entra_token_via_host_routing(client):
    resp = client.post(
        "/tenant-x/oauth2/v2.0/token",
        data={
            "grant_type": "client_credentials",
            "client_id": "app",
            "client_secret": "s",
        },
        headers={"Host": "login.microsoftonline.com"},
    )
    assert resp.status_code == 200
    assert "access_token" in json.loads(resp.data)


def test_unknown_host_returns_404(client):
    resp = client.get("/anything", headers={"Host": "unknown.example.com"})
    assert resp.status_code == 404
