from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from localstack.gcp.stores import CaseInsensitiveDict

SEVERITY_RANK = {
    "DEFAULT": 0,
    "DEBUG": 100,
    "INFO": 200,
    "NOTICE": 300,
    "WARNING": 400,
    "ERROR": 500,
    "CRITICAL": 600,
    "ALERT": 700,
    "EMERGENCY": 800,
}

MAX_ENTRIES_PER_PROJECT = 10_000


@dataclass
class LogEntry:
    log_name: str  # projects/{p}/logs/{log}
    severity: str = "DEFAULT"
    timestamp: str = ""
    text_payload: str = ""
    json_payload: dict[str, Any] | None = None
    labels: dict[str, str] = field(default_factory=dict)
    insert_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "logName": self.log_name,
            "severity": self.severity,
            "timestamp": self.timestamp,
            "labels": self.labels,
            "insertId": self.insert_id,
        }
        if self.json_payload is not None:
            out["jsonPayload"] = self.json_payload
        else:
            out["textPayload"] = self.text_payload
        return out


@dataclass
class LogSink:
    name: str  # projects/{p}/sinks/{id}
    destination: str = ""
    filter_expr: str = ""
    create_time: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "destination": self.destination,
            "filter": self.filter_expr,
            "createTime": self.create_time,
        }


class LoggingDataStore:
    def __init__(self) -> None:
        self.entries: dict[str, list[LogEntry]] = {}
        self.sinks: CaseInsensitiveDict = CaseInsensitiveDict()

    def append(self, project: str, entry: LogEntry) -> None:
        lst = self.entries.setdefault(project, [])
        lst.append(entry)
        if len(lst) > MAX_ENTRIES_PER_PROJECT:
            del lst[: len(lst) - MAX_ENTRIES_PER_PROJECT]
