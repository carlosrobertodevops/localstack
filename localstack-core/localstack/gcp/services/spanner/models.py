from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from localstack.gcp.stores import CaseInsensitiveDict


@dataclass
class SpannerSession:
    name: str  # projects/{p}/instances/{i}/databases/{d}/sessions/{s}
    create_time: str = ""
    approximate_last_use_time: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "createTime": self.create_time,
            "approximateLastUseTime": self.approximate_last_use_time,
        }


@dataclass
class SpannerDatabase:
    name: str  # projects/{p}/instances/{i}/databases/{d}
    state: str = "READY"
    create_time: str = ""
    sessions: CaseInsensitiveDict = field(default_factory=CaseInsensitiveDict)
    ddl: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "state": self.state,
            "createTime": self.create_time,
        }


@dataclass
class SpannerInstance:
    name: str  # projects/{p}/instances/{id}
    config: str = "projects/_/instanceConfigs/regional-us-central1"
    display_name: str = ""
    node_count: int = 1
    state: str = "READY"
    create_time: str = ""
    databases: CaseInsensitiveDict = field(default_factory=CaseInsensitiveDict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "config": self.config,
            "displayName": self.display_name or self.name.rsplit("/", 1)[-1],
            "nodeCount": self.node_count,
            "state": self.state,
            "createTime": self.create_time,
        }


class SpannerDataStore:
    def __init__(self) -> None:
        self.instances: CaseInsensitiveDict = CaseInsensitiveDict()
