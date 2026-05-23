from __future__ import annotations

import datetime
from typing import Any

from localstack.gcp.exceptions import GcpAlreadyExists, GcpInvalidRequest, GcpNotFound
from localstack.gcp.stores import GcpProject, GcpStores


class ResourceManagerProvider:
    """Minimal CloudResourceManager.projects.* CRUD."""

    def __init__(self, stores: GcpStores | None = None) -> None:
        self.stores = stores or GcpStores()
        self._number_seq = 0

    def create_project(self, project_id: str, *, name: str = "", labels: dict[str, str] | None = None) -> GcpProject:
        if not project_id:
            raise GcpInvalidRequest("projectId is required")
        if self.stores.has_project(project_id):
            raise GcpAlreadyExists(f"Project '{project_id}' already exists")
        self._number_seq += 1
        project = GcpProject(
            project_id=project_id,
            name=name or project_id,
            project_number=str(100_000_000_000 + self._number_seq),
            labels=dict(labels or {}),
            create_time=datetime.datetime.now(datetime.UTC).isoformat(),
        )
        store = self.stores.get_project(project_id)
        store.project = project
        return project

    def get_project(self, project_id: str) -> GcpProject:
        if not self.stores.has_project(project_id):
            raise GcpNotFound(f"Project '{project_id}' not found")
        store = self.stores.get_project(project_id)
        if store.project is None:
            raise GcpNotFound(f"Project '{project_id}' not found")
        return store.project

    def list_projects(self) -> list[GcpProject]:
        out: list[GcpProject] = []
        for pid in list(self.stores._projects.keys()):  # type: ignore[attr-defined]
            store = self.stores.get_project(str(pid))
            if store.project is not None:
                out.append(store.project)
        return out

    def delete_project(self, project_id: str) -> None:
        if not self.stores.has_project(project_id):
            raise GcpNotFound(f"Project '{project_id}' not found")
        store = self.stores.get_project(project_id)
        if store.project is None:
            raise GcpNotFound(f"Project '{project_id}' not found")
        store.project.state = "DELETE_REQUESTED"

    def ensure_project(self, project_id: str) -> GcpProject:
        try:
            return self.get_project(project_id)
        except GcpNotFound:
            return self.create_project(project_id)

    def to_dict(self, project: GcpProject) -> dict[str, Any]:
        return {
            "name": f"projects/{project.project_id}",
            "projectId": project.project_id,
            "projectNumber": project.project_number,
            "displayName": project.name,
            "state": project.state,
            "labels": project.labels,
            "createTime": project.create_time,
        }
