from __future__ import annotations

from localstack.azure.defaults import create_default_registry
from localstack.azure.ids import AzureResourceId
from localstack.azure.resource_manager import ResourceManagerProvider
from localstack.azure.scope import AzureScope
from localstack.azure.spec import AzureServiceSpec
from localstack.azure.stores import AzureGenericResource, AzureStores


class MicrosoftWebProvider:
    def __init__(
        self,
        *,
        resource_manager: ResourceManagerProvider | None = None,
        stores: AzureStores | None = None,
    ) -> None:
        self.stores = stores or AzureStores()
        self.resource_manager = resource_manager or ResourceManagerProvider(
            stores=self.stores, registry=create_default_registry()
        )
        self.resource_manager.registry.register(
            AzureServiceSpec(
                namespace="Microsoft.Web",
                resource_type="sites",
                api_versions=("2023-12-01",),
                locations=("eastus", "westeurope", "westus2", "brazilsouth"),
            )
        )

    def create_function_app(
        self,
        scope: AzureScope,
        name: str,
        parameters: dict,
        *,
        api_version: str | None = "2023-12-01",
    ) -> AzureGenericResource:
        body = {**parameters, "kind": parameters.get("kind", "functionapp")}
        return self.resource_manager.create_or_update_resource(
            scope, self._site_id(scope, name), body, api_version=api_version
        )

    def get_function_app(self, scope: AzureScope, name: str) -> AzureGenericResource:
        return self.resource_manager.get_resource(scope, self._site_id(scope, name))

    def list_function_apps(self, scope: AzureScope) -> list[AzureGenericResource]:
        return [
            resource
            for resource in self.resource_manager.list_resources(
                AzureScope.for_subscription(scope.subscription_id), resource_group=scope.resource_group
            )
            if resource.type.lower() == "microsoft.web/sites"
            and resource.raw.get("kind") == "functionapp"
        ]

    def delete_function_app(self, scope: AzureScope, name: str) -> None:
        self.resource_manager.delete_resource(scope, self._site_id(scope, name))

    def find_app(self, name: str) -> AzureGenericResource | None:
        """Scan every subscription for a function app named `name` (host-based lookup)."""
        target = f"microsoft.web/sites/{name}".lower()
        for sub_store in self.stores._subscriptions.values():
            for resource in sub_store.resources.values():
                if resource.type.lower() == "microsoft.web/sites" and resource.id.lower().endswith(target):
                    return resource
        return None

    @staticmethod
    def _site_id(scope: AzureScope, name: str) -> AzureResourceId:
        return AzureResourceId.parse(
            f"/subscriptions/{scope.subscription_id}/resourceGroups/{scope.resource_group}/providers/"
            f"Microsoft.Web/sites/{name}"
        )
