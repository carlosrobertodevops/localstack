from __future__ import annotations

import datetime
import uuid
from typing import Any

from localstack.gcp.exceptions import GcpAlreadyExists, GcpInvalidRequest, GcpNotFound
from localstack.gcp.resource_manager import ResourceManagerProvider
from localstack.gcp.services.spanner.models import (
    SpannerDatabase,
    SpannerDataStore,
    SpannerInstance,
    SpannerSession,
)
from localstack.gcp.stores import GcpStores


def _now() -> str:
    return datetime.datetime.now(datetime.UTC).isoformat()


class SpannerProvider:
    def __init__(
        self,
        *,
        resource_manager: ResourceManagerProvider | None = None,
        stores: GcpStores | None = None,
    ) -> None:
        self.stores = stores or GcpStores()
        self.resource_manager = resource_manager or ResourceManagerProvider(stores=self.stores)
        self.data = SpannerDataStore()

    def create_instance(
        self,
        project: str,
        instance_id: str,
        *,
        config: str = "projects/_/instanceConfigs/regional-us-central1",
        display_name: str = "",
        node_count: int = 1,
    ) -> SpannerInstance:
        full = f"projects/{project}/instances/{instance_id}"
        if full in self.data.instances:
            raise GcpAlreadyExists(f"instance '{full}' already exists")
        self.resource_manager.ensure_project(project)
        inst = SpannerInstance(
            name=full,
            config=config,
            display_name=display_name,
            node_count=node_count,
            create_time=_now(),
        )
        self.data.instances[full] = inst
        return inst

    def get_instance(self, project: str, instance_id: str) -> SpannerInstance:
        full = f"projects/{project}/instances/{instance_id}"
        inst = self.data.instances.get(full)
        if inst is None:
            raise GcpNotFound(f"instance '{full}' not found")
        return inst

    def list_instances(self, project: str) -> list[SpannerInstance]:
        prefix = f"projects/{project}/instances/"
        return [i for i in self.data.instances.values() if i.name.startswith(prefix)]

    def delete_instance(self, project: str, instance_id: str) -> None:
        full = f"projects/{project}/instances/{instance_id}"
        if full not in self.data.instances:
            raise GcpNotFound(f"instance '{full}' not found")
        del self.data.instances[full]

    def create_database(
        self,
        project: str,
        instance_id: str,
        database_id: str,
        *,
        extra_statements: list[str] | None = None,
    ) -> SpannerDatabase:
        inst = self.get_instance(project, instance_id)
        full = f"{inst.name}/databases/{database_id}"
        if full in inst.databases:
            raise GcpAlreadyExists(f"database '{full}' already exists")
        db = SpannerDatabase(name=full, create_time=_now())
        db.ddl.extend(extra_statements or [])
        inst.databases[full] = db
        return db

    def get_database(
        self, project: str, instance_id: str, database_id: str
    ) -> SpannerDatabase:
        inst = self.get_instance(project, instance_id)
        full = f"{inst.name}/databases/{database_id}"
        db = inst.databases.get(full)
        if db is None:
            raise GcpNotFound(f"database '{full}' not found")
        return db

    def list_databases(
        self, project: str, instance_id: str
    ) -> list[SpannerDatabase]:
        inst = self.get_instance(project, instance_id)
        return list(inst.databases.values())

    def delete_database(
        self, project: str, instance_id: str, database_id: str
    ) -> None:
        inst = self.get_instance(project, instance_id)
        full = f"{inst.name}/databases/{database_id}"
        if full not in inst.databases:
            raise GcpNotFound(f"database '{full}' not found")
        del inst.databases[full]

    def update_ddl(
        self,
        project: str,
        instance_id: str,
        database_id: str,
        statements: list[str],
    ) -> SpannerDatabase:
        db = self.get_database(project, instance_id, database_id)
        if not statements:
            raise GcpInvalidRequest("statements required")
        db.ddl.extend(statements)
        return db

    def create_session(
        self, project: str, instance_id: str, database_id: str
    ) -> SpannerSession:
        db = self.get_database(project, instance_id, database_id)
        sid = uuid.uuid4().hex[:12]
        full = f"{db.name}/sessions/{sid}"
        sess = SpannerSession(name=full, create_time=_now(), approximate_last_use_time=_now())
        db.sessions[full] = sess
        return sess

    def list_sessions(
        self, project: str, instance_id: str, database_id: str
    ) -> list[SpannerSession]:
        db = self.get_database(project, instance_id, database_id)
        return list(db.sessions.values())

    def delete_session(self, name: str) -> None:
        # name = projects/{p}/instances/{i}/databases/{d}/sessions/{s}
        parts = name.split("/")
        if len(parts) != 8 or parts[6] != "sessions":
            raise GcpInvalidRequest(f"invalid session name: {name}")
        db = self.get_database(parts[1], parts[3], parts[5])
        if name not in db.sessions:
            raise GcpNotFound(f"session '{name}' not found")
        del db.sessions[name]

    def execute_sql(self, session_name: str, sql: str) -> dict[str, Any]:
        if not sql:
            raise GcpInvalidRequest("sql required")
        # locate session to validate
        parts = session_name.split("/")
        if len(parts) != 8 or parts[6] != "sessions":
            raise GcpInvalidRequest(f"invalid session name: {session_name}")
        db = self.get_database(parts[1], parts[3], parts[5])
        if session_name not in db.sessions:
            raise GcpNotFound(f"session '{session_name}' not found")
        return {
            "metadata": {
                "rowType": {"fields": []},
            },
            "rows": [],
            "stats": {"rowCountExact": "0"},
        }
