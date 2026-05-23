from __future__ import annotations

from localstack.gcp.spec import GcpServiceSpec, GcpServiceSpecRegistry

_DEFAULT_LOCATIONS: tuple[str, ...] = (
    "us-central1",
    "us-east1",
    "us-west1",
    "europe-west1",
    "asia-east1",
)


def create_default_registry() -> GcpServiceSpecRegistry:
    registry = GcpServiceSpecRegistry()
    # Tier-1
    registry.register(GcpServiceSpec("cloudresourcemanager", "projects", ("v3",)))
    registry.register(
        GcpServiceSpec("storage", "buckets", ("v1",), locations=_DEFAULT_LOCATIONS)
    )
    registry.register(
        GcpServiceSpec("storage", "objects", ("v1",), locations=_DEFAULT_LOCATIONS)
    )
    registry.register(
        GcpServiceSpec("pubsub", "topics", ("v1",), locations=_DEFAULT_LOCATIONS)
    )
    registry.register(
        GcpServiceSpec("pubsub", "subscriptions", ("v1",), locations=_DEFAULT_LOCATIONS)
    )
    registry.register(
        GcpServiceSpec("firestore", "databases", ("v1",), locations=_DEFAULT_LOCATIONS)
    )
    registry.register(
        GcpServiceSpec("firestore", "documents", ("v1",), locations=_DEFAULT_LOCATIONS)
    )
    registry.register(
        GcpServiceSpec("cloudfunctions", "functions", ("v2",), locations=_DEFAULT_LOCATIONS)
    )
    registry.register(GcpServiceSpec("iam", "serviceAccounts", ("v1",)))
    # Tier-2
    registry.register(
        GcpServiceSpec("bigquery", "datasets", ("v2",), locations=_DEFAULT_LOCATIONS)
    )
    registry.register(
        GcpServiceSpec("bigquery", "tables", ("v2",), locations=_DEFAULT_LOCATIONS)
    )
    registry.register(GcpServiceSpec("bigquery", "jobs", ("v2",)))
    registry.register(
        GcpServiceSpec("secretmanager", "secrets", ("v1",), locations=_DEFAULT_LOCATIONS)
    )
    registry.register(
        GcpServiceSpec("cloudkms", "keyRings", ("v1",), locations=_DEFAULT_LOCATIONS)
    )
    registry.register(
        GcpServiceSpec("cloudkms", "cryptoKeys", ("v1",), locations=_DEFAULT_LOCATIONS)
    )
    registry.register(
        GcpServiceSpec("cloudtasks", "queues", ("v2",), locations=_DEFAULT_LOCATIONS)
    )
    registry.register(
        GcpServiceSpec("run", "services", ("v2",), locations=_DEFAULT_LOCATIONS)
    )
    registry.register(GcpServiceSpec("logging", "logs", ("v2",)))
    registry.register(GcpServiceSpec("logging", "sinks", ("v2",)))
    # Tier-3
    registry.register(
        GcpServiceSpec("sqladmin", "instances", ("v1beta4",), locations=_DEFAULT_LOCATIONS)
    )
    registry.register(
        GcpServiceSpec("sqladmin", "databases", ("v1beta4",), locations=_DEFAULT_LOCATIONS)
    )
    registry.register(GcpServiceSpec("sqladmin", "users", ("v1beta4",)))
    registry.register(
        GcpServiceSpec("cloudscheduler", "jobs", ("v1",), locations=_DEFAULT_LOCATIONS)
    )
    registry.register(GcpServiceSpec("dns", "managedZones", ("v1",)))
    registry.register(GcpServiceSpec("dns", "rrsets", ("v1",)))
    registry.register(GcpServiceSpec("spanner", "instances", ("v1",)))
    registry.register(GcpServiceSpec("spanner", "databases", ("v1",)))
    registry.register(
        GcpServiceSpec("redis", "instances", ("v1",), locations=_DEFAULT_LOCATIONS)
    )
    return registry
