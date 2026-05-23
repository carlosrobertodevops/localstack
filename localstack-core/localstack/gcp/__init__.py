"""Experimental Google Cloud Platform emulation primitives."""

from localstack.gcp.defaults import create_default_registry
from localstack.gcp.exceptions import (
    GcpAlreadyExists,
    GcpError,
    GcpInvalidRequest,
    GcpInvalidResourceName,
    GcpNotFound,
    GcpUnsupportedOperation,
)
from localstack.gcp.gateway import GcpGateway
from localstack.gcp.handlers import (
    AuthHandler,
    ErrorSerializerHandler,
    GcpRequestContext,
    HandlerChain,
    RequestContextHandler,
)
from localstack.gcp.plugins import (
    GcpProviderPlugin,
    GcpProviderRegistry,
    iter_builtin_plugins,
)
from localstack.gcp.resource_manager import ResourceManagerProvider
from localstack.gcp.resource_names import GcpResourceName
from localstack.gcp.scope import GcpScope
from localstack.gcp.serializers import (
    make_operation_name,
    parse_json_body,
    serialize_error,
    serialize_operation,
)
from localstack.gcp.services.bigquery import BigQueryProvider, BigQueryRouter
from localstack.gcp.services.cloudrun import CloudRunProvider, CloudRunRouter
from localstack.gcp.services.cloudsql import CloudSqlProvider, CloudSqlRouter
from localstack.gcp.services.cloudtasks import CloudTasksProvider, CloudTasksRouter
from localstack.gcp.services.dns import DnsProvider, DnsRouter
from localstack.gcp.services.firestore import FirestoreProvider, FirestoreRouter
from localstack.gcp.services.functions import (
    CloudFunctionsProvider,
    FunctionsControlRouter,
    FunctionsHttpRouter,
    FunctionsRegistry,
)
from localstack.gcp.services.iam import IamProvider, IamTokenRouter
from localstack.gcp.services.kms import KmsProvider, KmsRouter
from localstack.gcp.services.logging import LoggingProvider, LoggingRouter
from localstack.gcp.services.memorystore import MemorystoreProvider, MemorystoreRouter
from localstack.gcp.services.pubsub import PubSubProvider, PubSubRouter
from localstack.gcp.services.scheduler import SchedulerProvider, SchedulerRouter
from localstack.gcp.services.secretmanager import (
    SecretManagerProvider,
    SecretManagerRouter,
)
from localstack.gcp.services.spanner import SpannerProvider, SpannerRouter
from localstack.gcp.services.storage import (
    CloudStorageProvider,
    StorageJsonRouter,
    StorageXmlRouter,
)
from localstack.gcp.spec import GcpServiceSpec, GcpServiceSpecRegistry
from localstack.gcp.state import GcpStateStore
from localstack.gcp.stores import (
    GcpGenericResource,
    GcpProject,
    GcpProjectStore,
    GcpStores,
)

__all__ = [
    "AuthHandler",
    "BigQueryProvider",
    "BigQueryRouter",
    "CloudFunctionsProvider",
    "CloudRunProvider",
    "CloudRunRouter",
    "CloudSqlProvider",
    "CloudSqlRouter",
    "CloudStorageProvider",
    "CloudTasksProvider",
    "CloudTasksRouter",
    "DnsProvider",
    "DnsRouter",
    "ErrorSerializerHandler",
    "FirestoreProvider",
    "FirestoreRouter",
    "FunctionsControlRouter",
    "FunctionsHttpRouter",
    "FunctionsRegistry",
    "GcpAlreadyExists",
    "GcpError",
    "GcpGateway",
    "GcpGenericResource",
    "GcpInvalidRequest",
    "GcpInvalidResourceName",
    "GcpNotFound",
    "GcpProject",
    "GcpProjectStore",
    "GcpProviderPlugin",
    "GcpProviderRegistry",
    "GcpRequestContext",
    "GcpResourceName",
    "GcpScope",
    "GcpServiceSpec",
    "GcpServiceSpecRegistry",
    "GcpStateStore",
    "GcpStores",
    "GcpUnsupportedOperation",
    "HandlerChain",
    "IamProvider",
    "IamTokenRouter",
    "KmsProvider",
    "KmsRouter",
    "LoggingProvider",
    "LoggingRouter",
    "MemorystoreProvider",
    "MemorystoreRouter",
    "PubSubProvider",
    "PubSubRouter",
    "RequestContextHandler",
    "ResourceManagerProvider",
    "SchedulerProvider",
    "SchedulerRouter",
    "SecretManagerProvider",
    "SecretManagerRouter",
    "SpannerProvider",
    "SpannerRouter",
    "StorageJsonRouter",
    "StorageXmlRouter",
    "create_default_registry",
    "iter_builtin_plugins",
    "make_operation_name",
    "parse_json_body",
    "serialize_error",
    "serialize_operation",
]
