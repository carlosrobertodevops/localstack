"""GCP provider plugin registry — analog of ``localstack.azure.plugins``."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable


@dataclass(frozen=True)
class GcpProviderPlugin:
    service: str
    resource_type: str
    provider_factory: Callable[..., object]

    @property
    def name(self) -> str:
        return f"{self.service}/{self.resource_type}"


class GcpProviderRegistry:
    def __init__(self) -> None:
        self._plugins: dict[tuple[str, str], GcpProviderPlugin] = {}

    def register(self, plugin: GcpProviderPlugin) -> None:
        self._plugins[(plugin.service.lower(), plugin.resource_type.lower())] = plugin

    def get(self, service: str, resource_type: str) -> GcpProviderPlugin | None:
        return self._plugins.get((service.lower(), resource_type.lower()))

    def services(self) -> tuple[str, ...]:
        return tuple(sorted({p.service for p in self._plugins.values()}))

    def resource_types(self, service: str) -> tuple[str, ...]:
        svc = service.lower()
        return tuple(
            sorted({p.resource_type for p in self._plugins.values() if p.service.lower() == svc})
        )

    def load_builtins(self) -> None:
        for plugin in iter_builtin_plugins():
            self.register(plugin)


def iter_builtin_plugins() -> Iterable[GcpProviderPlugin]:
    from localstack.gcp.resource_manager import ResourceManagerProvider
    from localstack.gcp.services.bigquery.provider import BigQueryProvider
    from localstack.gcp.services.cloudrun.provider import CloudRunProvider
    from localstack.gcp.services.cloudsql.provider import CloudSqlProvider
    from localstack.gcp.services.cloudtasks.provider import CloudTasksProvider
    from localstack.gcp.services.dns.provider import DnsProvider
    from localstack.gcp.services.firestore.provider import FirestoreProvider
    from localstack.gcp.services.functions.provider import CloudFunctionsProvider
    from localstack.gcp.services.iam.provider import IamProvider
    from localstack.gcp.services.kms.provider import KmsProvider
    from localstack.gcp.services.logging.provider import LoggingProvider
    from localstack.gcp.services.memorystore.provider import MemorystoreProvider
    from localstack.gcp.services.pubsub.provider import PubSubProvider
    from localstack.gcp.services.scheduler.provider import SchedulerProvider
    from localstack.gcp.services.secretmanager.provider import SecretManagerProvider
    from localstack.gcp.services.spanner.provider import SpannerProvider
    from localstack.gcp.services.storage.provider import CloudStorageProvider

    # Tier-1
    yield GcpProviderPlugin("cloudresourcemanager", "projects", ResourceManagerProvider)
    yield GcpProviderPlugin("storage", "buckets", CloudStorageProvider)
    yield GcpProviderPlugin("pubsub", "topics", PubSubProvider)
    yield GcpProviderPlugin("firestore", "databases", FirestoreProvider)
    yield GcpProviderPlugin("cloudfunctions", "functions", CloudFunctionsProvider)
    yield GcpProviderPlugin("iam", "serviceAccounts", IamProvider)
    # Tier-2
    yield GcpProviderPlugin("bigquery", "datasets", BigQueryProvider)
    yield GcpProviderPlugin("secretmanager", "secrets", SecretManagerProvider)
    yield GcpProviderPlugin("cloudkms", "keyRings", KmsProvider)
    yield GcpProviderPlugin("cloudtasks", "queues", CloudTasksProvider)
    yield GcpProviderPlugin("run", "services", CloudRunProvider)
    yield GcpProviderPlugin("logging", "logs", LoggingProvider)
    # Tier-3
    yield GcpProviderPlugin("sqladmin", "instances", CloudSqlProvider)
    yield GcpProviderPlugin("cloudscheduler", "jobs", SchedulerProvider)
    yield GcpProviderPlugin("dns", "managedZones", DnsProvider)
    yield GcpProviderPlugin("spanner", "instances", SpannerProvider)
    yield GcpProviderPlugin("redis", "instances", MemorystoreProvider)
