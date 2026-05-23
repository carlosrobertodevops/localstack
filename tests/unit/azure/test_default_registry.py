import pytest

from localstack.azure.defaults import create_default_registry
from localstack.azure.exceptions import AzureUnsupportedOperation


def test_default_registry_registers_resource_group_and_storage_account_specs():
    registry = create_default_registry()

    resource_groups = registry.get("Microsoft.Resources", "resourceGroups")
    storage_accounts = registry.get("Microsoft.Storage", "storageAccounts")

    assert resource_groups.api_versions
    assert storage_accounts.api_versions
    assert resource_groups.namespace == "Microsoft.Resources"
    assert storage_accounts.resource_type == "storageAccounts"


def test_default_registry_resolves_specs_case_insensitively():
    registry = create_default_registry()

    assert registry.get("microsoft.storage", "storageaccounts") == registry.get(
        "Microsoft.Storage", "storageAccounts"
    )


def test_default_registry_rejects_unknown_resource_type():
    registry = create_default_registry()

    with pytest.raises(AzureUnsupportedOperation) as exc:
        registry.get("Microsoft.Storage", "unknownType")

    assert "Microsoft.Storage/unknownType" in str(exc.value)
