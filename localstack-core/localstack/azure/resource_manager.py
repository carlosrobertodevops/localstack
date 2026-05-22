from __future__ import annotations

from typing import Any

from localstack.azure.exceptions import AzureInvalidRequest, AzureNotFound
from localstack.azure.ids import AzureResourceId
from localstack.azure.scope import AzureScope
from localstack.azure.spec import AzureServiceSpecRegistry
from localstack.azure.stores import (
    AzureGenericResource,
    AzureResourceGroup,
    AzureStores,
    AzureSubscriptionStore,
)


class ResourceManagerProvider:
    def __init__(
        self,
        *,
        stores: AzureStores | None = None,
        registry: AzureServiceSpecRegistry | None = None,
    ) -> None:
        self.stores = stores or AzureStores()
        self.registry = registry or AzureServiceSpecRegistry()

    def create_or_update_resource_group(
        self, scope: AzureScope, name: str, parameters: dict[str, Any]
    ) -> AzureResourceGroup:
        location = parameters.get("location") or scope.location
        if not location:
            raise AzureInvalidRequest("resource group location is required")

        group = AzureResourceGroup(
            id=self._resource_group_id(scope.subscription_id, name),
            name=name,
            location=location,
            tags=dict(parameters.get("tags") or {}),
            properties=dict(parameters.get("properties") or {}),
        )
        self._store(scope).resource_groups[name] = group
        return group

    def get_resource_group(self, scope: AzureScope, name: str) -> AzureResourceGroup:
        group = self._store(scope).resource_groups.get(name)
        if group is None:
            raise AzureNotFound(f"Azure resource group not found: {name}")
        return group

    def list_resource_groups(self, scope: AzureScope) -> list[AzureResourceGroup]:
        return sorted(self._store(scope).resource_groups.values(), key=lambda group: group.name.lower())

    def delete_resource_group(self, scope: AzureScope, name: str) -> None:
        store = self._store(scope)
        if store.resource_groups.pop(name, None) is None:
            raise AzureNotFound(f"Azure resource group not found: {name}")
        prefix = self._resource_group_id(scope.subscription_id, name).lower() + "/"
        for resource_id in list(store.resources.keys()):
            if resource_id.lower().startswith(prefix):
                del store.resources[resource_id]

    def create_or_update_resource(
        self,
        scope: AzureScope,
        resource_id: str | AzureResourceId,
        parameters: dict[str, Any],
        *,
        api_version: str | None = None,
    ) -> AzureGenericResource:
        parsed = self._parse_and_validate_scope(scope, resource_id)
        spec = self.registry.get(parsed.namespace, parsed.resource_type)
        self.get_resource_group(scope, parsed.resource_group)
        location = parameters.get("location") or scope.location

        if spec.locations and location not in spec.locations:
            raise AzureInvalidRequest(
                f"location '{location}' is not supported for {parsed.namespace}/{parsed.resource_type}; "
                f"supported locations: {', '.join(spec.locations)}"
            )

        resource = AzureGenericResource(
            id=parsed.resource_id,
            name=parsed.name,
            type=f"{parsed.namespace}/{parsed.resource_type}",
            location=location,
            api_version=api_version,
            tags=dict(parameters.get("tags") or {}),
            properties=dict(parameters.get("properties") or {}),
            raw=dict(parameters),
        )
        self._store(scope).resources[parsed.resource_id] = resource
        return resource

    def get_resource(
        self, scope: AzureScope, resource_id: str | AzureResourceId
    ) -> AzureGenericResource:
        parsed = self._parse_and_validate_scope(scope, resource_id)
        resource = self._store(scope).resources.get(parsed.resource_id)
        if resource is None:
            raise AzureNotFound(f"Azure resource not found: {parsed.resource_id}")
        return resource

    def list_resources(
        self, scope: AzureScope, *, resource_group: str | None = None
    ) -> list[AzureGenericResource]:
        resources = list(self._store(scope).resources.values())
        if resource_group is not None:
            prefix = self._resource_group_id(scope.subscription_id, resource_group).lower() + "/"
            resources = [resource for resource in resources if resource.id.lower().startswith(prefix)]
        return sorted(resources, key=lambda resource: resource.id.lower())

    def delete_resource(self, scope: AzureScope, resource_id: str | AzureResourceId) -> None:
        parsed = self._parse_and_validate_scope(scope, resource_id)
        if self._store(scope).resources.pop(parsed.resource_id, None) is None:
            raise AzureNotFound(f"Azure resource not found: {parsed.resource_id}")

    def _parse_and_validate_scope(
        self, scope: AzureScope, resource_id: str | AzureResourceId
    ) -> AzureResourceId:
        parsed = AzureResourceId.parse(resource_id) if isinstance(resource_id, str) else resource_id
        if parsed.subscription_id.lower() != scope.subscription_id.lower():
            raise AzureInvalidRequest(
                f"resource subscription '{parsed.subscription_id}' does not match scope subscription "
                f"'{scope.subscription_id}'"
            )
        return parsed

    def _store(self, scope: AzureScope) -> AzureSubscriptionStore:
        return self.stores.get_subscription(scope.subscription_id)

    @staticmethod
    def _resource_group_id(subscription_id: str, name: str) -> str:
        return f"/subscriptions/{subscription_id}/resourceGroups/{name}"
