from localstack.azure.spec import AzureServiceSpec, AzureServiceSpecRegistry


def create_default_registry() -> AzureServiceSpecRegistry:
    registry = AzureServiceSpecRegistry()
    registry.register(
        AzureServiceSpec(
            namespace="Microsoft.Resources",
            resource_type="resourceGroups",
            api_versions=("2021-04-01",),
            locations=(),
        )
    )
    registry.register(
        AzureServiceSpec(
            namespace="Microsoft.Storage",
            resource_type="storageAccounts",
            api_versions=("2023-01-01",),
            locations=("eastus", "westeurope", "westus2", "brazilsouth"),
        )
    )
    registry.register(
        AzureServiceSpec(
            namespace="Microsoft.Web",
            resource_type="sites",
            api_versions=("2023-12-01",),
            locations=("eastus", "westeurope", "westus2", "brazilsouth"),
        )
    )
    registry.register(
        AzureServiceSpec(
            namespace="Microsoft.DocumentDB",
            resource_type="databaseAccounts",
            api_versions=("2023-11-15",),
            locations=("eastus", "westeurope", "westus2", "brazilsouth"),
        )
    )
    return registry
