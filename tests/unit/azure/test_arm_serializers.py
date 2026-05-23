from localstack.azure.arm_serializers import (
    deserialize_resource_body,
    deserialize_resource_group_body,
    serialize_resource,
    serialize_resource_group,
    serialize_resource_group_list,
    serialize_resource_list,
)
from localstack.azure.stores import AzureGenericResource, AzureResourceGroup


def test_serialize_resource_group_arm_shape():
    rg = AzureResourceGroup(
        id="/subscriptions/sub-1/resourceGroups/rg-dev",
        name="rg-dev",
        location="eastus",
        tags={"env": "dev"},
        properties={"customField": 1},
    )

    out = serialize_resource_group(rg)

    assert out == {
        "id": "/subscriptions/sub-1/resourceGroups/rg-dev",
        "name": "rg-dev",
        "type": "Microsoft.Resources/resourceGroups",
        "location": "eastus",
        "tags": {"env": "dev"},
        "properties": {"provisioningState": "Succeeded", "customField": 1},
    }


def test_serialize_resource_group_list_wraps_in_value():
    rg = AzureResourceGroup(
        id="/subscriptions/sub-1/resourceGroups/rg-dev",
        name="rg-dev",
        location="eastus",
    )

    out = serialize_resource_group_list([rg])

    assert out == {"value": [serialize_resource_group(rg)]}


def test_serialize_generic_resource_arm_shape():
    res = AzureGenericResource(
        id="/subscriptions/s/resourceGroups/rg/providers/Microsoft.Storage/storageAccounts/sa1",
        name="sa1",
        type="Microsoft.Storage/storageAccounts",
        location="eastus",
        api_version="2023-01-01",
        tags={"team": "platform"},
        properties={"sku": "Standard_LRS"},
    )

    out = serialize_resource(res)

    assert out["id"].endswith("/storageAccounts/sa1")
    assert out["name"] == "sa1"
    assert out["type"] == "Microsoft.Storage/storageAccounts"
    assert out["location"] == "eastus"
    assert out["tags"] == {"team": "platform"}
    assert out["properties"] == {"provisioningState": "Succeeded", "sku": "Standard_LRS"}
    # apiVersion stays out of the body per Azure REST convention
    assert "apiVersion" not in out
    assert "raw" not in out


def test_serialize_resource_list_wraps_in_value():
    res = AzureGenericResource(
        id="/subscriptions/s/resourceGroups/rg/providers/Microsoft.Storage/storageAccounts/sa1",
        name="sa1",
        type="Microsoft.Storage/storageAccounts",
        location="eastus",
    )

    assert serialize_resource_list([res]) == {"value": [serialize_resource(res)]}


def test_deserialize_resource_group_body_extracts_fields():
    body = {
        "location": "westeurope",
        "tags": {"env": "prod"},
        "properties": {"foo": "bar"},
        "extra-ignored-field": True,
    }

    out = deserialize_resource_group_body(body)

    assert out == {
        "location": "westeurope",
        "tags": {"env": "prod"},
        "properties": {"foo": "bar"},
    }


def test_deserialize_resource_group_body_requires_location():
    import pytest

    from localstack.azure.exceptions import AzureInvalidRequest

    with pytest.raises(AzureInvalidRequest):
        deserialize_resource_group_body({})


def test_deserialize_resource_body_extracts_fields():
    body = {
        "location": "eastus",
        "tags": {"a": "b"},
        "properties": {"sku": "Standard_LRS"},
    }

    out = deserialize_resource_body(body)

    assert out == {
        "location": "eastus",
        "tags": {"a": "b"},
        "properties": {"sku": "Standard_LRS"},
    }


def test_deserialize_resource_body_defaults_missing_collections():
    out = deserialize_resource_body({"location": "eastus"})
    assert out == {"location": "eastus", "tags": {}, "properties": {}}
