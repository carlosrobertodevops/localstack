from localstack.azure.ids import AzureResourceId
from localstack.azure.scope import AzureScope


def test_creates_subscription_scope():
    scope = AzureScope.for_subscription("sub-123")

    assert scope.subscription_id == "sub-123"
    assert scope.resource_group is None
    assert scope.location is None


def test_creates_resource_group_scope():
    scope = AzureScope.for_resource_group("sub-123", "rg-dev", location="eastus")

    assert scope.subscription_id == "sub-123"
    assert scope.resource_group == "rg-dev"
    assert scope.location == "eastus"


def test_creates_scope_from_resource_id():
    resource_id = AzureResourceId.parse(
        "/subscriptions/sub-123/resourceGroups/rg-dev/providers/Microsoft.Storage/storageAccounts/store1"
    )

    scope = AzureScope.from_resource_id(resource_id, location="eastus")

    assert scope.subscription_id == "sub-123"
    assert scope.resource_group == "rg-dev"
    assert scope.location == "eastus"
