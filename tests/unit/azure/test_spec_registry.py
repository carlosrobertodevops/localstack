import pytest

from localstack.azure.exceptions import AzureUnsupportedOperation
from localstack.azure.spec import AzureServiceSpec, AzureServiceSpecRegistry


def test_registers_and_resolves_service_spec_by_namespace_and_resource_type():
    registry = AzureServiceSpecRegistry()
    spec = AzureServiceSpec(
        namespace="Microsoft.Storage",
        resource_type="storageAccounts",
        api_versions=("2023-01-01",),
        locations=("eastus", "westeurope"),
    )

    registry.register(spec)

    assert registry.get("Microsoft.Storage", "storageAccounts") == spec
    assert registry.namespaces() == ("Microsoft.Storage",)
    assert registry.resource_types("Microsoft.Storage") == ("storageAccounts",)


def test_unknown_service_spec_raises_unsupported_operation():
    registry = AzureServiceSpecRegistry()

    with pytest.raises(AzureUnsupportedOperation) as exc:
        registry.get("Microsoft.Web", "sites")

    assert exc.value.status_code == 501
    assert exc.value.code == "UnsupportedAzureResourceType"
    assert "Microsoft.Web/sites" in str(exc.value)


def test_register_rejects_empty_api_versions():
    registry = AzureServiceSpecRegistry()

    with pytest.raises(ValueError) as exc:
        registry.register(
            AzureServiceSpec(
                namespace="Microsoft.Storage",
                resource_type="storageAccounts",
                api_versions=(),
                locations=("eastus",),
            )
        )

    assert "api_versions" in str(exc.value)
