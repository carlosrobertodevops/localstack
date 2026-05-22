from __future__ import annotations

import datetime

from localstack.gcp.exceptions import GcpAlreadyExists, GcpInvalidRequest, GcpNotFound
from localstack.gcp.resource_manager import ResourceManagerProvider
from localstack.gcp.services.cloudsql.models import (
    CloudSqlDataStore,
    SqlDatabase,
    SqlInstance,
    SqlUser,
)
from localstack.gcp.stores import GcpStores


def _now() -> str:
    return datetime.datetime.now(datetime.UTC).isoformat()


class CloudSqlProvider:
    def __init__(
        self,
        *,
        resource_manager: ResourceManagerProvider | None = None,
        stores: GcpStores | None = None,
    ) -> None:
        self.stores = stores or GcpStores()
        self.resource_manager = resource_manager or ResourceManagerProvider(stores=self.stores)
        self.data = CloudSqlDataStore()

    def _key(self, project: str, instance: str) -> str:
        return f"{project}/{instance}"

    def create_instance(
        self,
        project: str,
        instance: str,
        *,
        region: str = "us-central1",
        database_version: str = "MYSQL_8_0",
        tier: str = "db-n1-standard-1",
    ) -> SqlInstance:
        k = self._key(project, instance)
        if k in self.data.instances:
            raise GcpAlreadyExists(f"instance '{instance}' already exists in project '{project}'")
        self.resource_manager.ensure_project(project)
        inst = SqlInstance(
            name=instance,
            project=project,
            region=region,
            database_version=database_version,
            tier=tier,
            create_time=_now(),
        )
        self.data.instances[k] = inst
        return inst

    def get_instance(self, project: str, instance: str) -> SqlInstance:
        k = self._key(project, instance)
        inst = self.data.instances.get(k)
        if inst is None:
            raise GcpNotFound(f"instance '{instance}' not found in '{project}'")
        return inst

    def list_instances(self, project: str) -> list[SqlInstance]:
        prefix = f"{project}/"
        return [
            i for k, i in self.data.instances.items() if k.startswith(prefix)
        ]

    def delete_instance(self, project: str, instance: str) -> None:
        k = self._key(project, instance)
        if k not in self.data.instances:
            raise GcpNotFound(f"instance '{instance}' not found")
        del self.data.instances[k]

    def patch_instance(
        self, project: str, instance: str, *, tier: str | None = None
    ) -> SqlInstance:
        inst = self.get_instance(project, instance)
        if tier is not None:
            inst.tier = tier
        return inst

    def create_database(
        self, project: str, instance: str, database: str, *, charset: str = "utf8"
    ) -> SqlDatabase:
        inst = self.get_instance(project, instance)
        if database in inst.databases:
            raise GcpAlreadyExists(f"database '{database}' already exists in '{instance}'")
        db = SqlDatabase(
            name=database, instance=instance, project=project, charset=charset
        )
        inst.databases[database] = db
        return db

    def get_database(
        self, project: str, instance: str, database: str
    ) -> SqlDatabase:
        inst = self.get_instance(project, instance)
        db = inst.databases.get(database)
        if db is None:
            raise GcpNotFound(f"database '{database}' not found in '{instance}'")
        return db

    def list_databases(self, project: str, instance: str) -> list[SqlDatabase]:
        inst = self.get_instance(project, instance)
        return list(inst.databases.values())

    def delete_database(self, project: str, instance: str, database: str) -> None:
        inst = self.get_instance(project, instance)
        if database not in inst.databases:
            raise GcpNotFound(f"database '{database}' not found")
        del inst.databases[database]

    def create_user(
        self,
        project: str,
        instance: str,
        user: str,
        *,
        host: str = "%",
        password: str = "",
    ) -> SqlUser:
        inst = self.get_instance(project, instance)
        key = f"{user}@{host}"
        if key in inst.users:
            raise GcpAlreadyExists(f"user '{key}' already exists in '{instance}'")
        u = SqlUser(name=user, instance=instance, project=project, host=host, password=password)
        inst.users[key] = u
        return u

    def list_users(self, project: str, instance: str) -> list[SqlUser]:
        inst = self.get_instance(project, instance)
        return list(inst.users.values())

    def delete_user(
        self, project: str, instance: str, user: str, host: str = "%"
    ) -> None:
        inst = self.get_instance(project, instance)
        key = f"{user}@{host}"
        if key not in inst.users:
            raise GcpNotFound(f"user '{key}' not found")
        del inst.users[key]
