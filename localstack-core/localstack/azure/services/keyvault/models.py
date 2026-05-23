from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4

from localstack.azure.stores import CaseInsensitiveDict


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class KeyVaultSecretVersion:
    value: str
    id: str = field(default_factory=lambda: uuid4().hex)
    enabled: bool = True
    created: datetime = field(default_factory=_now)
    updated: datetime = field(default_factory=_now)
    content_type: str | None = None
    tags: dict[str, str] = field(default_factory=dict)


@dataclass
class KeyVaultSecret:
    name: str
    versions: list[KeyVaultSecretVersion] = field(default_factory=list)

    @property
    def latest(self) -> KeyVaultSecretVersion:
        return self.versions[-1]


@dataclass
class KeyVaultDataPlaneState:
    vault_name: str
    secrets: CaseInsensitiveDict = field(default_factory=CaseInsensitiveDict)


class KeyVaultDataPlaneStore:
    def __init__(self) -> None:
        self.vaults: CaseInsensitiveDict = CaseInsensitiveDict()

    def ensure_vault(self, vault_name: str) -> KeyVaultDataPlaneState:
        vault = self.vaults.get(vault_name)
        if vault is None:
            vault = KeyVaultDataPlaneState(vault_name=vault_name)
            self.vaults[vault_name] = vault
        return vault

    def get_vault(self, vault_name: str) -> KeyVaultDataPlaneState | None:
        return self.vaults.get(vault_name)

    def delete_vault(self, vault_name: str) -> None:
        self.vaults.pop(vault_name, None)
