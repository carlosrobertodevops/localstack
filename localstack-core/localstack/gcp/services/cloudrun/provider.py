from __future__ import annotations

import datetime
import uuid

from localstack.gcp.exceptions import GcpAlreadyExists, GcpInvalidRequest, GcpNotFound
from localstack.gcp.resource_manager import ResourceManagerProvider
from localstack.gcp.services.cloudrun.models import (
    CloudRunDataStore,
    CloudRunService,
    Revision,
)
from localstack.gcp.stores import GcpStores


def _now() -> str:
    return datetime.datetime.now(datetime.UTC).isoformat()


class CloudRunProvider:
    def __init__(
        self,
        *,
        resource_manager: ResourceManagerProvider | None = None,
        stores: GcpStores | None = None,
    ) -> None:
        self.stores = stores or GcpStores()
        self.resource_manager = resource_manager or ResourceManagerProvider(stores=self.stores)
        self.data = CloudRunDataStore()

    def _full(self, project: str, location: str, service_id: str) -> str:
        return f"projects/{project}/locations/{location}/services/{service_id}"

    def create_service(
        self,
        project: str,
        location: str,
        service_id: str,
        *,
        image: str = "",
        env: dict[str, str] | None = None,
    ) -> CloudRunService:
        full = self._full(project, location, service_id)
        if full in self.data.services:
            raise GcpAlreadyExists(f"service '{full}' already exists")
        self.resource_manager.ensure_project(project)
        env = dict(env or {})
        suffix = uuid.uuid4().hex[:8]
        svc = CloudRunService(
            name=full,
            image=image,
            env=env,
            generation=1,
            uri=f"https://{service_id}-{suffix}.{location}.run.app",
            create_time=_now(),
        )
        rev_name = f"{full}/revisions/{service_id}-00001"
        rev = Revision(name=rev_name, image=image, env=dict(env), create_time=_now())
        svc.revisions[rev_name] = rev
        svc.latest_revision_name = rev_name
        svc.traffic = [{"percent": 100, "revision": rev_name}]
        self.data.services[full] = svc
        return svc

    def get_service(
        self, project: str, location: str, service_id: str
    ) -> CloudRunService:
        full = self._full(project, location, service_id)
        svc = self.data.services.get(full)
        if svc is None:
            raise GcpNotFound(f"service '{full}' not found")
        return svc

    def list_services(self, project: str, location: str) -> list[CloudRunService]:
        prefix = f"projects/{project}/locations/{location}/services/"
        return [s for s in self.data.services.values() if s.name.startswith(prefix)]

    def delete_service(self, project: str, location: str, service_id: str) -> None:
        full = self._full(project, location, service_id)
        if full not in self.data.services:
            raise GcpNotFound(f"service '{full}' not found")
        del self.data.services[full]

    def update_service(
        self,
        project: str,
        location: str,
        service_id: str,
        *,
        image: str | None = None,
        env: dict[str, str] | None = None,
        preserve_traffic: bool = False,
    ) -> CloudRunService:
        svc = self.get_service(project, location, service_id)
        if image is not None:
            svc.image = image
        if env is not None:
            svc.env = dict(env)
        svc.generation += 1
        rev_name = f"{svc.name}/revisions/{service_id}-{svc.generation:05d}"
        rev = Revision(
            name=rev_name, image=svc.image, env=dict(svc.env), create_time=_now()
        )
        svc.revisions[rev_name] = rev
        svc.latest_revision_name = rev_name
        if not preserve_traffic:
            svc.traffic = [{"percent": 100, "revision": rev_name}]
        return svc

    def list_revisions(
        self, project: str, location: str, service_id: str
    ) -> list[Revision]:
        svc = self.get_service(project, location, service_id)
        return list(svc.revisions.values())

    def get_revision(self, name: str) -> Revision:
        parts = name.split("/")
        if len(parts) != 8 or parts[6] != "revisions":
            raise GcpInvalidRequest(f"invalid revision name: {name}")
        svc = self.get_service(parts[1], parts[3], parts[5])
        rev = svc.revisions.get(name)
        if rev is None:
            raise GcpNotFound(f"revision '{name}' not found")
        return rev

    def delete_revision(self, name: str) -> None:
        rev = self.get_revision(name)
        parts = name.split("/")
        svc = self.get_service(parts[1], parts[3], parts[5])
        if svc.latest_revision_name == name:
            raise GcpInvalidRequest(f"cannot delete latest revision '{name}'")
        del svc.revisions[rev.name]

    def update_traffic(
        self,
        project: str,
        location: str,
        service_id: str,
        traffic: list[dict],
    ) -> CloudRunService:
        svc = self.get_service(project, location, service_id)
        total = sum(t.get("percent", 0) for t in traffic)
        if total != 100:
            raise GcpInvalidRequest(f"traffic percentages must sum to 100, got {total}")
        for entry in traffic:
            rev = entry.get("revision")
            if rev and rev not in svc.revisions:
                raise GcpInvalidRequest(f"unknown revision '{rev}'")
        svc.traffic = list(traffic)
        return svc
