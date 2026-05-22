from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from localstack.gcp.stores import CaseInsensitiveDict


@dataclass
class SecretVersion:
    name: str  # projects/{p}/secrets/{s}/versions/{n}
    state: str = "ENABLED"
    create_time: str = ""
    payload_data: bytes = b""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "state": self.state,
            "createTime": self.create_time,
        }


@dataclass
class Secret:
    name: str  # projects/{p}/secrets/{id}
    create_time: str = ""
    labels: dict[str, str] = field(default_factory=dict)
    replication: dict[str, Any] = field(default_factory=lambda: {"automatic": {}})
    versions: list[SecretVersion] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "createTime": self.create_time,
            "labels": self.labels,
            "replication": self.replication,
        }


class SecretManagerDataStore:
    def __init__(self) -> None:
        self.secrets: CaseInsensitiveDict = CaseInsensitiveDict()
