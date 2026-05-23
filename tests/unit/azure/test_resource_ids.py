import pytest

from localstack.azure.exceptions import AzureInvalidResourceId
from localstack.azure.ids import AzureResourceId


def test_parses_resource_id_with_subscription_resource_group_provider_and_name():
    resource_id = AzureResourceId.parse(
        "/subscriptions/sub-123/resourceGroups/rg-dev/providers/Microsoft.Storage/storageAccounts/store1"
    )

    assert resource_id.subscription_id == "sub-123"
    assert resource_id.resource_group == "rg-dev"
    assert resource_id.namespace == "Microsoft.Storage"
    assert resource_id.resource_type == "storageAccounts"
    assert resource_id.name == "store1"
    assert resource_id.resource_id == (
        "/subscriptions/sub-123/resourceGroups/rg-dev/providers/Microsoft.Storage/"
        "storageAccounts/store1"
    )


def test_parses_nested_resource_id_children():
    resource_id = AzureResourceId.parse(
        "/subscriptions/sub-123/resourceGroups/rg-dev/providers/"
        "Microsoft.Web/sites/site1/slots/staging"
    )

    assert resource_id.namespace == "Microsoft.Web"
    assert resource_id.resource_type == "sites"
    assert resource_id.name == "site1"
    assert resource_id.child_resources == (("slots", "staging"),)
    assert resource_id.resource_id.endswith("/sites/site1/slots/staging")


def test_rejects_invalid_resource_id():
    with pytest.raises(AzureInvalidResourceId) as exc:
        AzureResourceId.parse("/subscriptions/sub-123/providers/Microsoft.Storage")

    assert "resourceGroups" in str(exc.value)
