from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from localstack.gcp.stores import CaseInsensitiveDict


@dataclass
class CloudTask:
    name: str  # projects/{p}/locations/{l}/queues/{q}/tasks/{id}
    http_request: dict[str, Any] = field(default_factory=dict)
    schedule_time: str = ""
    dispatch_count: int = 0
    state: str = "SCHEDULED"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "httpRequest": self.http_request,
            "scheduleTime": self.schedule_time,
            "dispatchCount": self.dispatch_count,
            "state": self.state,
        }


@dataclass
class Queue:
    name: str  # projects/{p}/locations/{l}/queues/{id}
    state: str = "RUNNING"
    rate_limits: dict[str, Any] = field(
        default_factory=lambda: {"maxDispatchesPerSecond": 500.0}
    )
    retry_config: dict[str, Any] = field(default_factory=lambda: {"maxAttempts": 100})
    tasks: CaseInsensitiveDict = field(default_factory=CaseInsensitiveDict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "state": self.state,
            "rateLimits": self.rate_limits,
            "retryConfig": self.retry_config,
        }


class CloudTasksDataStore:
    def __init__(self) -> None:
        self.queues: CaseInsensitiveDict = CaseInsensitiveDict()
