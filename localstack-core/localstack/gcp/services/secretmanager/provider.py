from __future__ import annotations

import datetime

from localstack.gcp.exceptions import GcpAlreadyExists, GcpInvalidRequest, GcpNotFound
from localstack.gcp.resource_manager import ResourceManagerProvider
from localstack.gcp.services.secretmanager.models import (
    Secret,
    SecretManagerDataStore,
    SecretVersion,
)
from localstack.gcp.stores import GcpStores


def _now() -> str:
    return datetime.datetime.now(datetime.UTC).isoformat()


class SecretManagerProvider:
    def __init__(
        self,
        *,
        resource_manager: ResourceManagerProvider | None = None,
        stores: GcpStores | None = None,
    ) -> None:
        self.stores = stores or GcpStores()
        self.resource_manager = resource_manager or ResourceManagerProvider(stores=self.stores)
        self.data = SecretManagerDataStore()

    def create_secret(
        self,
        project: str,
        secret_id: str,
        *,
        labels: dict[str, str] | None = None,
        replication: dict | None = None,
    ) -> Secret:
        full = f"projects/{project}/secrets/{secret_id}"
        if full in self.data.secrets:
            raise GcpAlreadyExists(f"secret '{full}' already exists")
        self.resource_manager.ensure_project(project)
        secret = Secret(
            name=full,
            create_time=_now(),
            labels=dict(labels or {}),
            replication=replication or {"automatic": {}},
        )
        self.data.secrets[full] = secret
        return secret

    def get_secret(self, project: str, secret_id: str) -> Secret:
        full = f"projects/{project}/secrets/{secret_id}"
        secret = self.data.secrets.get(full)
        if secret is None:
            raise GcpNotFound(f"secret '{full}' not found")
        return secret

    def list_secrets(self, project: str) -> list[Secret]:
        prefix = f"projects/{project}/secrets/"
        return [s for s in self.data.secrets.values() if s.name.startswith(prefix)]

    def delete_secret(self, project: str, secret_id: str) -> None:
        full = f"projects/{project}/secrets/{secret_id}"
        if full not in self.data.secrets:
            raise GcpNotFound(f"secret '{full}' not found")
        del self.data.secrets[full]

    def add_secret_version(
        self, project: str, secret_id: str, payload_data: bytes
    ) -> SecretVersion:
        secret = self.get_secret(project, secret_id)
        number = len(secret.versions) + 1
        version = SecretVersion(
            name=f"{secret.name}/versions/{number}",
            state="ENABLED",
            create_time=_now(),
            payload_data=payload_data,
        )
        secret.versions.append(version)
        return version

    def _resolve_version(self, secret: Secret, version: str) -> SecretVersion:
        if version == "latest":
            for v in reversed(secret.versions):
                if v.state != "DESTROYED":
                    return v
            raise GcpNotFound(f"no enabled version for '{secret.name}'")
        try:
            idx = int(version) - 1
        except ValueError as e:
            raise GcpInvalidRequest(f"invalid version '{version}'") from e
        if idx < 0 or idx >= len(secret.versions):
            raise GcpNotFound(f"version '{version}' not found for '{secret.name}'")
        return secret.versions[idx]

    def get_secret_version(
        self, project: str, secret_id: str, version: str
    ) -> SecretVersion:
        secret = self.get_secret(project, secret_id)
        return self._resolve_version(secret, version)

    def access_secret_version(
        self, project: str, secret_id: str, version: str
    ) -> SecretVersion:
        v = self.get_secret_version(project, secret_id, version)
        if v.state != "ENABLED":
            raise GcpInvalidRequest(f"version '{v.name}' is not enabled (state={v.state})")
        return v

    def list_versions(self, project: str, secret_id: str) -> list[SecretVersion]:
        secret = self.get_secret(project, secret_id)
        return list(secret.versions)

    def disable_secret_version(
        self, project: str, secret_id: str, version: str
    ) -> SecretVersion:
        v = self.get_secret_version(project, secret_id, version)
        if v.state == "DESTROYED":
            raise GcpInvalidRequest(f"version '{v.name}' is destroyed")
        v.state = "DISABLED"
        return v

    def enable_secret_version(
        self, project: str, secret_id: str, version: str
    ) -> SecretVersion:
        v = self.get_secret_version(project, secret_id, version)
        if v.state == "DESTROYED":
            raise GcpInvalidRequest(f"version '{v.name}' is destroyed")
        v.state = "ENABLED"
        return v

    def destroy_secret_version(
        self, project: str, secret_id: str, version: str
    ) -> SecretVersion:
        v = self.get_secret_version(project, secret_id, version)
        v.state = "DESTROYED"
        v.payload_data = b""
        return v
