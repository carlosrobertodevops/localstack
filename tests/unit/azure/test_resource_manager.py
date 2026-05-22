import pytest

from localstack.azure.exceptions import AzureInvalidRequest, AzureNotFound, AzureUnsupportedOperation
from localstack.azure.ids import AzureResourceId
from localstack.azure.resource_manager import ResourceManagerProvider
from localstack.azure.scope import AzureScope
from localstack.azure.spec import AzureServiceSpec, AzureServiceSpecRegistry
from localstack.azure.stores import AzureStores


def test_creates_updates_lists_and_deletes_resource_groups():
    manager = ResourceManagerProvider(stores=AzureStores())
    scope = AzureScope.for_subscription("sub-123")

    group = manager.create_or_update_resource_group(
        scope,
        "rg-dev",
        {"location": "eastus", "tags": {"env": "dev"}},
    )
    updated = manager.create_or_update_resource_group(
        scope,
        "rg-dev",
        {"location": "eastus", "tags": {"env": "personal"}},
    )

    assert group.id == "/subscriptions/sub-123/resourceGroups/rg-dev"
    assert updated.tags == {"env": "personal"}
    assert [item.name for item in manager.list_resource_groups(scope)] == ["rg-dev"]

    manager.delete_resource_group(scope, "rg-dev")

    assert manager.list_resource_groups(scope) == []
    with pytest.raises(AzureNotFound):
        manager.get_resource_group(scope, "rg-dev")


def test_deleting_resource_group_deletes_child_resources():
    manager = ResourceManagerProvider(stores=AzureStores(), registry=_registry())
    scope = AzureScope.for_subscription("sub-123")
    resource_id = _storage_account_id("store1")

    manager.create_or_update_resource_group(scope, "rg-dev", {"location": "eastus"})
    manager.create_or_update_resource(scope, resource_id, {"location": "eastus"})
    manager.delete_resource_group(scope, "rg-dev")

    with pytest.raises(AzureNotFound):
        manager.get_resource(scope, resource_id)


def test_put_get_list_and_delete_generic_resource():
    manager = ResourceManagerProvider(stores=AzureStores(), registry=_registry())
    scope = AzureScope.for_subscription("sub-123")
    resource_id = _storage_account_id("store1")

    manager.create_or_update_resource_group(scope, "rg-dev", {"location": "eastus"})
    resource = manager.create_or_update_resource(
        scope,
        resource_id,
        {"location": "eastus", "tags": {"owner": "me"}, "properties": {"kind": "dev"}},
        api_version="2023-01-01",
    )

    assert resource.id == resource_id.resource_id
    assert resource.name == "store1"
    assert resource.type == "Microsoft.Storage/storageAccounts"
    assert resource.api_version == "2023-01-01"
    assert manager.get_resource(scope, resource_id) == resource
    assert manager.list_resources(scope, resource_group="rg-dev") == [resource]

    manager.delete_resource(scope, resource_id)

    with pytest.raises(AzureNotFound):
        manager.get_resource(scope, resource_id)


def test_put_resource_requires_registered_resource_type():
    manager = ResourceManagerProvider(stores=AzureStores(), registry=AzureServiceSpecRegistry())
    scope = AzureScope.for_subscription("sub-123")
    manager.create_or_update_resource_group(scope, "rg-dev", {"location": "eastus"})

    with pytest.raises(AzureUnsupportedOperation) as exc:
        manager.create_or_update_resource(
            scope,
            _storage_account_id("store1"),
            {"location": "eastus"},
        )

    assert "Microsoft.Storage/storageAccounts" in str(exc.value)


def test_put_resource_rejects_unsupported_location():
    manager = ResourceManagerProvider(stores=AzureStores(), registry=_registry(locations=("eastus",)))
    scope = AzureScope.for_subscription("sub-123")
    manager.create_or_update_resource_group(scope, "rg-dev", {"location": "eastus"})

    with pytest.raises(AzureInvalidRequest) as exc:
        manager.create_or_update_resource(
            scope,
            _storage_account_id("store1"),
            {"location": "westeurope"},
        )

    assert "location" in str(exc.value)
    assert "eastus" in str(exc.value)


def test_put_resource_rejects_subscription_mismatch():
    manager = ResourceManagerProvider(stores=AzureStores(), registry=_registry())

    with pytest.raises(AzureInvalidRequest) as exc:
        manager.create_or_update_resource(
            AzureScope.for_subscription("sub-456"),
            _storage_account_id("store1"),
            {"location": "eastus"},
        )

    assert "subscription" in str(exc.value)


def test_put_resource_requires_existing_resource_group():
    manager = ResourceManagerProvider(stores=AzureStores(), registry=_registry())

    with pytest.raises(AzureNotFound) as exc:
        manager.create_or_update_resource(
            AzureScope.for_subscription("sub-123"),
            _storage_account_id("store1"),
            {"location": "eastus"},
        )

    assert "resource group" in str(exc.value)


def _registry(locations=("eastus", "westeurope")):
    registry = AzureServiceSpecRegistry()
    registry.register(
        AzureServiceSpec(
            namespace="Microsoft.Storage",
            resource_type="storageAccounts",
            api_versions=("2023-01-01",),
            locations=locations,
        )
    )
    return registry


def _storage_account_id(name: str):
    return AzureResourceId.parse(
        f"/subscriptions/sub-123/resourceGroups/rg-dev/providers/"
        f"Microsoft.Storage/storageAccounts/{name}"
    )
