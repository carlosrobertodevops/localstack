"""Built-in cloud registrations. Imported lazily on first registry access."""

from __future__ import annotations

from localstack.cloud.base import CloudProvider
from localstack.cloud.registry import CloudRegistry, registry as _default_registry


def _azure_gateway_factory():
    from localstack.azure.gateway import AzureGateway

    return AzureGateway()


def _azure_state_store_factory():
    from localstack.azure.state import AzureStateStore

    return AzureStateStore()


def _azure_plugin_registry_factory():
    from localstack.azure.plugins import AzureProviderRegistry

    registry = AzureProviderRegistry()
    registry.load_builtins()
    return registry


def _aws_gateway_factory():
    # The AWS module ships a richer gateway; expose its factory if available.
    from localstack.aws.gateway import Gateway  # type: ignore

    return Gateway()


def _gcp_gateway_factory():
    from localstack.gcp.gateway import GcpGateway

    return GcpGateway()


def _gcp_state_store_factory():
    from localstack.gcp.state import GcpStateStore

    return GcpStateStore()


def _gcp_plugin_registry_factory():
    from localstack.gcp.plugins import GcpProviderRegistry

    registry = GcpProviderRegistry()
    registry.load_builtins()
    return registry


def register_builtins(target: CloudRegistry | None = None) -> CloudRegistry:
    """Register the cloud providers shipped in this repo.

    Idempotent: safe to call multiple times — re-registers with ``replace=True``.
    """
    target = target if target is not None else _default_registry
    target.register(
        CloudProvider(
            name="azure",
            display_name="Microsoft Azure",
            package="localstack.azure",
            gateway_factory=_azure_gateway_factory,
            state_store_factory=_azure_state_store_factory,
            plugin_registry_factory=_azure_plugin_registry_factory,
            edge_hosts=(
                "*.blob.core.windows.net",
                "*.queue.core.windows.net",
                "*.documents.azure.com",
                "*.azurewebsites.net",
                "*.vault.azure.net",
                "login.microsoftonline.com",
            ),
            metadata={
                "scope_terms": {"tenant": "tenant", "account": "subscription", "region": "location"},
                "id_format": "/subscriptions/{sub}/resourceGroups/{rg}/providers/{ns}/{type}/{name}",
                "auth": "oauth2-bearer",
            },
        ),
        replace=True,
    )
    target.register(
        CloudProvider(
            name="aws",
            display_name="Amazon Web Services",
            package="localstack.aws",
            gateway_factory=_aws_gateway_factory,
            state_store_factory=None,
            plugin_registry_factory=None,
            edge_hosts=(
                "*.amazonaws.com",
                "*.s3.amazonaws.com",
                "*.execute-api.amazonaws.com",
                "*.lambda-url.amazonaws.com",
            ),
            metadata={
                "scope_terms": {"tenant": "account", "account": "account", "region": "region"},
                "id_format": "arn:aws:{svc}:{region}:{account}:{type}/{name}",
                "auth": "sigv4",
            },
        ),
        replace=True,
    )
    target.register(
        CloudProvider(
            name="gcp",
            display_name="Google Cloud Platform",
            package="localstack.gcp",
            gateway_factory=_gcp_gateway_factory,
            state_store_factory=_gcp_state_store_factory,
            plugin_registry_factory=_gcp_plugin_registry_factory,
            edge_hosts=(
                "storage.googleapis.com",
                "pubsub.googleapis.com",
                "firestore.googleapis.com",
                "cloudfunctions.googleapis.com",
                "iam.googleapis.com",
                "oauth2.googleapis.com",
                "cloudresourcemanager.googleapis.com",
                "*.cloudfunctions.net",
                "bigquery.googleapis.com",
                "secretmanager.googleapis.com",
                "cloudkms.googleapis.com",
                "cloudtasks.googleapis.com",
                "run.googleapis.com",
                "logging.googleapis.com",
                "sqladmin.googleapis.com",
                "cloudscheduler.googleapis.com",
                "dns.googleapis.com",
                "spanner.googleapis.com",
                "redis.googleapis.com",
            ),
            metadata={
                "scope_terms": {"tenant": "organization", "account": "project", "region": "location"},
                "id_format": "projects/{project}/locations/{loc}/{type}/{name}",
                "auth": "oauth2-bearer",
            },
        ),
        replace=True,
    )
    return target
