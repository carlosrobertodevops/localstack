from __future__ import annotations

import datetime

from localstack.gcp.exceptions import GcpAlreadyExists, GcpInvalidRequest, GcpNotFound
from localstack.gcp.resource_manager import ResourceManagerProvider
from localstack.gcp.services.memorystore.models import (
    MemorystoreDataStore,
    RedisInstance,
)
from localstack.gcp.stores import GcpStores


def _now() -> str:
    return datetime.datetime.now(datetime.UTC).isoformat()


class MemorystoreProvider:
    def __init__(
        self,
        *,
        resource_manager: ResourceManagerProvider | None = None,
        stores: GcpStores | None = None,
    ) -> None:
        self.stores = stores or GcpStores()
        self.resource_manager = resource_manager or ResourceManagerProvider(stores=self.stores)
        self.data = MemorystoreDataStore()

    def create_instance(
        self,
        project: str,
        location: str,
        instance_id: str,
        *,
        tier: str = "BASIC",
        memory_size_gb: int = 1,
        redis_version: str = "REDIS_7_0",
        authorized_network: str = "",
        auth_enabled: bool = False,
        labels: dict[str, str] | None = None,
    ) -> RedisInstance:
        if memory_size_gb < 1:
            raise GcpInvalidRequest("memorySizeGb must be >= 1")
        if tier not in ("BASIC", "STANDARD_HA"):
            raise GcpInvalidRequest(f"unknown tier: {tier}")
        full = f"projects/{project}/locations/{location}/instances/{instance_id}"
        if full in self.data.instances:
            raise GcpAlreadyExists(f"instance '{full}' already exists")
        self.resource_manager.ensure_project(project)
        inst = RedisInstance(
            name=full,
            tier=tier,
            memory_size_gb=memory_size_gb,
            redis_version=redis_version,
            authorized_network=authorized_network,
            auth_enabled=auth_enabled,
            labels=dict(labels or {}),
            create_time=_now(),
        )
        self.data.instances[full] = inst
        return inst

    def get_instance(
        self, project: str, location: str, instance_id: str
    ) -> RedisInstance:
        full = f"projects/{project}/locations/{location}/instances/{instance_id}"
        inst = self.data.instances.get(full)
        if inst is None:
            raise GcpNotFound(f"instance '{full}' not found")
        return inst

    def list_instances(
        self, project: str, location: str
    ) -> list[RedisInstance]:
        prefix = f"projects/{project}/locations/{location}/instances/"
        return [i for i in self.data.instances.values() if i.name.startswith(prefix)]

    def delete_instance(self, project: str, location: str, instance_id: str) -> None:
        full = f"projects/{project}/locations/{location}/instances/{instance_id}"
        if full not in self.data.instances:
            raise GcpNotFound(f"instance '{full}' not found")
        del self.data.instances[full]

    def patch_instance(
        self,
        project: str,
        location: str,
        instance_id: str,
        *,
        memory_size_gb: int | None = None,
        labels: dict[str, str] | None = None,
    ) -> RedisInstance:
        inst = self.get_instance(project, location, instance_id)
        if memory_size_gb is not None:
            if memory_size_gb < 1:
                raise GcpInvalidRequest("memorySizeGb must be >= 1")
            inst.memory_size_gb = memory_size_gb
        if labels is not None:
            inst.labels = dict(labels)
        return inst

    def failover(
        self, project: str, location: str, instance_id: str
    ) -> RedisInstance:
        inst = self.get_instance(project, location, instance_id)
        if inst.tier != "STANDARD_HA":
            raise GcpInvalidRequest("failover only supported on STANDARD_HA tier")
        inst.state = "READY"
        return inst
