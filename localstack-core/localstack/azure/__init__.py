"""Experimental Azure emulation primitives."""

from localstack.azure.exceptions import (
    AzureError,
    AzureInvalidRequest,
    AzureInvalidResourceId,
    AzureNotFound,
    AzureUnsupportedOperation,
)
from localstack.azure.arm_router import ArmRouter
from localstack.azure.gateway import AzureGateway
from localstack.azure.services.entra import EntraTokenRouter
from localstack.azure.arm_serializers import (
    deserialize_resource_body,
    deserialize_resource_group_body,
    serialize_resource,
    serialize_resource_group,
    serialize_resource_group_list,
    serialize_resource_list,
)
from localstack.azure.defaults import create_default_registry
from localstack.azure.ids import AzureResourceId
from localstack.azure.resource_manager import ResourceManagerProvider
from localstack.azure.scope import AzureScope
from localstack.azure.services.cosmos import CosmosSqlRouter, MicrosoftDocumentDBProvider
from localstack.azure.services.functions import (
    FunctionsHttpRouter,
    FunctionsRegistry,
    MicrosoftWebProvider,
)
from localstack.azure.services.eventgrid import EventGridRouter, MicrosoftEventGridProvider
from localstack.azure.services.keyvault import KeyVaultSecretsRouter, MicrosoftKeyVaultProvider
from localstack.azure.services.servicebus import (
    MicrosoftServiceBusProvider,
    ServiceBusRouter,
)
from localstack.azure.services.storage import (
    BlobRouter,
    MicrosoftStorageProvider,
    QueueRouter,
)
from localstack.azure.services.tablestorage import TableStorageProvider, TableStorageRouter
from localstack.azure.spec import AzureServiceSpec, AzureServiceSpecRegistry
from localstack.azure.stores import AzureGenericResource, AzureResourceGroup, AzureStores

__all__ = [
    "ArmRouter",
    "AzureGateway",
    "BlobRouter",
    "CosmosSqlRouter",
    "EntraTokenRouter",
    "EventGridRouter",
    "FunctionsHttpRouter",
    "FunctionsRegistry",
    "KeyVaultSecretsRouter",
    "MicrosoftEventGridProvider",
    "MicrosoftKeyVaultProvider",
    "MicrosoftServiceBusProvider",
    "QueueRouter",
    "ServiceBusRouter",
    "TableStorageProvider",
    "TableStorageRouter",
    "AzureError",
    "AzureInvalidRequest",
    "AzureInvalidResourceId",
    "AzureNotFound",
    "AzureResourceId",
    "AzureScope",
    "AzureServiceSpec",
    "AzureServiceSpecRegistry",
    "AzureGenericResource",
    "AzureResourceGroup",
    "AzureStores",
    "AzureUnsupportedOperation",
    "MicrosoftDocumentDBProvider",
    "MicrosoftStorageProvider",
    "MicrosoftWebProvider",
    "ResourceManagerProvider",
    "create_default_registry",
    "deserialize_resource_body",
    "deserialize_resource_group_body",
    "serialize_resource",
    "serialize_resource_group",
    "serialize_resource_group_list",
    "serialize_resource_list",
]
