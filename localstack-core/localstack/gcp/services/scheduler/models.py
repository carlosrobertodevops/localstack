from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from localstack.gcp.stores import CaseInsensitiveDict


@dataclass
class SchedulerJob:
    name: str  # projects/{p}/locations/{l}/jobs/{id}
    schedule: str = ""
    time_zone: str = "Etc/UTC"
    state: str = "ENABLED"  # ENABLED | PAUSED | DISABLED
    target_type: str = "http"  # http | pubsub | appengine
    target: dict[str, Any] = field(default_factory=dict)
    description: str = ""
    attempt_count: int = 0
    last_attempt_time: str = ""
    create_time: str = ""

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "name": self.name,
            "description": self.description,
            "schedule": self.schedule,
            "timeZone": self.time_zone,
            "state": self.state,
            "attemptDeadline": "180s",
            "userUpdateTime": self.create_time,
            "lastAttemptTime": self.last_attempt_time,
        }
        if self.target_type == "http":
            out["httpTarget"] = self.target
        elif self.target_type == "pubsub":
            out["pubsubTarget"] = self.target
        elif self.target_type == "appengine":
            out["appEngineHttpTarget"] = self.target
        return out


class SchedulerDataStore:
    def __init__(self) -> None:
        self.jobs: CaseInsensitiveDict = CaseInsensitiveDict()
