import json

import pytest
from werkzeug.test import Client
from werkzeug.wrappers import Response

from localstack.azure.arm_router import ArmRouter
from localstack.azure.defaults import create_default_registry
from localstack.azure.resource_manager import ResourceManagerProvider


@pytest.fixture
def client():
    registry = create_default_registry()
    provider = ResourceManagerProvider(registry=registry)
    router = ArmRouter(provider=provider)
    return Client(router, Response)


def test_put_resource_group_returns_arm_body(client):
    resp = client.put(
        "/subscriptions/sub-1/resourceGroups/rg-dev",
        data=json.dumps({"location": "eastus", "tags": {"env": "dev"}}),
        content_type="application/json",
    )
    assert resp.status_code == 200
    body = json.loads(resp.data)
    assert body["id"] == "/subscriptions/sub-1/resourceGroups/rg-dev"
    assert body["name"] == "rg-dev"
    assert body["type"] == "Microsoft.Resources/resourceGroups"
    assert body["location"] == "eastus"
    assert body["tags"] == {"env": "dev"}
    assert body["properties"]["provisioningState"] == "Succeeded"


def test_get_resource_group_after_put(client):
    client.put(
        "/subscriptions/s1/resourceGroups/rg1",
        data=json.dumps({"location": "eastus"}),
        content_type="application/json",
    )
    resp = client.get("/subscriptions/s1/resourceGroups/rg1")
    assert resp.status_code == 200
    body = json.loads(resp.data)
    assert body["name"] == "rg1"


def test_get_missing_resource_group_returns_404(client):
    resp = client.get("/subscriptions/s1/resourceGroups/missing")
    assert resp.status_code == 404
    body = json.loads(resp.data)
    assert body["error"]["code"] == "ResourceGroupNotFound"


def test_list_resource_groups(client):
    for name in ("a", "b"):
        client.put(
            f"/subscriptions/s1/resourceGroups/{name}",
            data=json.dumps({"location": "eastus"}),
            content_type="application/json",
        )
    resp = client.get("/subscriptions/s1/resourceGroups")
    assert resp.status_code == 200
    body = json.loads(resp.data)
    names = sorted(rg["name"] for rg in body["value"])
    assert names == ["a", "b"]


def test_delete_resource_group(client):
    client.put(
        "/subscriptions/s1/resourceGroups/rg1",
        data=json.dumps({"location": "eastus"}),
        content_type="application/json",
    )
    resp = client.delete("/subscriptions/s1/resourceGroups/rg1")
    assert resp.status_code == 204
    assert client.get("/subscriptions/s1/resourceGroups/rg1").status_code == 404


def test_put_generic_resource_requires_existing_rg(client):
    resp = client.put(
        "/subscriptions/s1/resourceGroups/no-rg/providers/Microsoft.Storage/storageAccounts/sa1",
        data=json.dumps({"location": "eastus"}),
        content_type="application/json",
    )
    assert resp.status_code == 404
    body = json.loads(resp.data)
    assert body["error"]["code"] == "ResourceGroupNotFound"


def test_put_get_delete_generic_resource(client):
    client.put(
        "/subscriptions/s1/resourceGroups/rg1",
        data=json.dumps({"location": "eastus"}),
        content_type="application/json",
    )
    res_path = (
        "/subscriptions/s1/resourceGroups/rg1/providers/Microsoft.Storage/storageAccounts/sa1"
    )
    put_resp = client.put(
        res_path,
        data=json.dumps({"location": "eastus", "properties": {"sku": "Standard_LRS"}}),
        content_type="application/json",
    )
    assert put_resp.status_code == 200
    body = json.loads(put_resp.data)
    assert body["type"] == "Microsoft.Storage/storageAccounts"
    assert body["properties"]["sku"] == "Standard_LRS"

    get_resp = client.get(res_path)
    assert get_resp.status_code == 200

    del_resp = client.delete(res_path)
    assert del_resp.status_code == 204
    assert client.get(res_path).status_code == 404


def test_list_resources_by_type(client):
    client.put(
        "/subscriptions/s1/resourceGroups/rg1",
        data=json.dumps({"location": "eastus"}),
        content_type="application/json",
    )
    for n in ("sa1", "sa2"):
        client.put(
            f"/subscriptions/s1/resourceGroups/rg1/providers/Microsoft.Storage/storageAccounts/{n}",
            data=json.dumps({"location": "eastus"}),
            content_type="application/json",
        )
    resp = client.get(
        "/subscriptions/s1/resourceGroups/rg1/providers/Microsoft.Storage/storageAccounts"
    )
    assert resp.status_code == 200
    body = json.loads(resp.data)
    assert sorted(r["name"] for r in body["value"]) == ["sa1", "sa2"]


def test_invalid_body_returns_400(client):
    resp = client.put(
        "/subscriptions/s1/resourceGroups/rg1",
        data="not json",
        content_type="application/json",
    )
    assert resp.status_code == 400


def test_unknown_route_returns_404(client):
    resp = client.get("/unknown/path")
    assert resp.status_code == 404
