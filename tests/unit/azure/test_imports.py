def test_localstack_azure_imports_without_optional_azure_dependencies():
    from localstack import azure
    from localstack.azure.exceptions import AzureUnsupportedOperation
    from localstack.azure.ids import AzureResourceId
    from localstack.azure.resource_manager import ResourceManagerProvider
    from localstack.azure.scope import AzureScope
    from localstack.azure.spec import AzureServiceSpec, AzureServiceSpecRegistry
    from localstack.azure.stores import AzureStores

    assert azure.__all__
    assert AzureUnsupportedOperation
    assert AzureResourceId
    assert AzureScope
    assert AzureServiceSpec
    assert AzureServiceSpecRegistry
    assert AzureStores
    assert ResourceManagerProvider


def test_localstack_azure_exports_core_primitives():
    from localstack.azure import (
        AzureScope,
        AzureStores,
        MicrosoftDocumentDBProvider,
        MicrosoftStorageProvider,
        MicrosoftWebProvider,
        ResourceManagerProvider,
        create_default_registry,
    )

    assert AzureScope.for_subscription("sub-123").subscription_id == "sub-123"
    assert AzureStores
    assert ResourceManagerProvider
    assert create_default_registry
    assert MicrosoftStorageProvider
    assert MicrosoftWebProvider
    assert MicrosoftDocumentDBProvider
