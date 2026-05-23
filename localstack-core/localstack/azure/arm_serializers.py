"""Serialize/deserialize Azure resources to/from ARM-style REST JSON."""

from __future__ import annotations

from typing import Any

from localstack.azure.exceptions import AzureInvalidRequest
from localstack.azure.stores import AzureGenericResource, AzureResourceGroup

RESOURCE_GROUP_TYPE = "Microsoft.Resources/resourceGroups"
_DEFAULT_PROVISIONING_STATE = {"provisioningState": "Succeeded"}


def serialize_resource_group(rg: AzureResourceGroup) -> dict[str, Any]:
    return {
        "id": rg.id,
        "name": rg.name,
        "type": RESOURCE_GROUP_TYPE,
        "location": rg.location,
        "tags": dict(rg.tags),
        "properties": {**_DEFAULT_PROVISIONING_STATE, **rg.properties},
    }


def serialize_resource_group_list(items: list[AzureResourceGroup]) -> dict[str, Any]:
    return {"value": [serialize_resource_group(i) for i in items]}


def serialize_resource(res: AzureGenericResource) -> dict[str, Any]:
    body: dict[str, Any] = {
        "id": res.id,
        "name": res.name,
        "type": res.type,
        "tags": dict(res.tags),
        "properties": {**_DEFAULT_PROVISIONING_STATE, **res.properties},
    }
    if res.location is not None:
        body["location"] = res.location
    return body


def serialize_resource_list(items: list[AzureGenericResource]) -> dict[str, Any]:
    return {"value": [serialize_resource(i) for i in items]}


def deserialize_resource_group_body(body: dict[str, Any]) -> dict[str, Any]:
    if not body or "location" not in body:
        raise AzureInvalidRequest("Resource group body requires 'location'")
    return {
        "location": body["location"],
        "tags": dict(body.get("tags") or {}),
        "properties": dict(body.get("properties") or {}),
    }


def deserialize_resource_body(body: dict[str, Any]) -> dict[str, Any]:
    if not body or "location" not in body:
        raise AzureInvalidRequest("Resource body requires 'location'")
    return {
        "location": body["location"],
        "tags": dict(body.get("tags") or {}),
        "properties": dict(body.get("properties") or {}),
    }
