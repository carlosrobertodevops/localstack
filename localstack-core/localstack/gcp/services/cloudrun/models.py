from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from localstack.gcp.stores import CaseInsensitiveDict


@dataclass
class Revision:
    name: str  # projects/{p}/locations/{l}/services/{s}/revisions/{rev}
    image: str = ""
    env: dict[str, str] = field(default_factory=dict)
    state: str = "ACTIVE"
    create_time: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "image": self.image,
            "env": [{"name": k, "value": v} for k, v in self.env.items()],
            "state": self.state,
            "createTime": self.create_time,
        }


@dataclass
class CloudRunService:
    name: str  # projects/{p}/locations/{l}/services/{id}
    image: str = ""
    env: dict[str, str] = field(default_factory=dict)
    generation: int = 1
    latest_revision_name: str = ""
    traffic: list[dict[str, Any]] = field(default_factory=list)
    uri: str = ""
    create_time: str = ""
    revisions: CaseInsensitiveDict = field(default_factory=CaseInsensitiveDict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "generation": self.generation,
            "latestReadyRevision": self.latest_revision_name,
            "traffic": self.traffic,
            "uri": self.uri,
            "createTime": self.create_time,
            "template": {
                "containers": [
                    {
                        "image": self.image,
                        "env": [{"name": k, "value": v} for k, v in self.env.items()],
                    }
                ]
            },
        }


class CloudRunDataStore:
    def __init__(self) -> None:
        self.services: CaseInsensitiveDict = CaseInsensitiveDict()
