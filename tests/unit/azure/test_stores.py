from localstack.azure.ids import AzureResourceId
from localstack.azure.stores import AzureGenericResource, AzureResourceGroup, AzureStores


def test_creates_isolated_subscription_stores():
    stores = AzureStores()
    sub_123 = stores.get_subscription("sub-123")
    sub_456 = stores.get_subscription("sub-456")

    sub_123.resource_groups["rg-dev"] = AzureResourceGroup(
        id="/subscriptions/sub-123/resourceGroups/rg-dev",
        name="rg-dev",
        location="eastus",
    )

    assert sub_123 is stores.get_subscription("sub-123")
    assert sub_456.resource_groups == {}


def test_clear_removes_subscription_state():
    stores = AzureStores()
    stores.get_subscription("sub-123").resource_groups["rg-dev"] = AzureResourceGroup(
        id="/subscriptions/sub-123/resourceGroups/rg-dev",
        name="rg-dev",
        location="eastus",
    )

    stores.clear()

    assert stores.get_subscription("sub-123").resource_groups == {}


def test_stores_generic_resources_by_normalized_resource_id():
    stores = AzureStores()
    store = stores.get_subscription("sub-123")
    resource_id = AzureResourceId.parse(
        "/subscriptions/sub-123/resourceGroups/rg-dev/providers/Microsoft.Storage/storageAccounts/store1"
    )
    resource = AzureGenericResource(
        id=resource_id.resource_id,
        name="store1",
        type="Microsoft.Storage/storageAccounts",
        location="eastus",
    )

    store.resources[resource_id.resource_id.upper()] = resource

    assert store.resources[resource_id.resource_id.lower()] == resource
