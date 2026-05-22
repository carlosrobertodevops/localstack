from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import Any, Callable

from localstack.gcp.stores import CaseInsensitiveDict


@dataclass
class CloudFunction:
    name: str  # projects/{p}/locations/{l}/functions/{f}
    runtime: str = "python313"
    entry_point: str = "main"
    trigger_type: str = "HTTP"
    environment: dict[str, str] = field(default_factory=dict)
    labels: dict[str, str] = field(default_factory=dict)
    update_time: str = ""
    state: str = "ACTIVE"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "runtime": self.runtime,
            "entryPoint": self.entry_point,
            "buildConfig": {"entryPoint": self.entry_point, "runtime": self.runtime},
            "serviceConfig": {"environmentVariables": self.environment},
            "labels": self.labels,
            "updateTime": self.update_time,
            "state": self.state,
        }


@dataclass
class RegisteredHandler:
    region: str
    project: str
    function: str
    handler: Callable[[dict, dict], tuple[int, dict, bytes]]


class FunctionsDataStore:
    def __init__(self) -> None:
        self.functions: CaseInsensitiveDict = CaseInsensitiveDict()

    def now_iso(self) -> str:
        return datetime.datetime.now(datetime.UTC).isoformat()
