from __future__ import annotations

import datetime
import re
import uuid
from typing import Any

from localstack.gcp.exceptions import GcpAlreadyExists, GcpInvalidRequest, GcpNotFound
from localstack.gcp.resource_manager import ResourceManagerProvider
from localstack.gcp.services.logging.models import (
    SEVERITY_RANK,
    LogEntry,
    LoggingDataStore,
    LogSink,
)
from localstack.gcp.stores import GcpStores


def _now() -> str:
    return datetime.datetime.now(datetime.UTC).isoformat()


def _project_from_log_name(log_name: str) -> str | None:
    m = re.match(r"^projects/([^/]+)/logs/", log_name)
    return m.group(1) if m else None


_SEV_RE = re.compile(r"^severity\s*(>=|<=|>|<|=|!=)\s*([A-Z]+)$")
_LOG_RE = re.compile(r'^logName\s*=\s*"?([^"]+)"?$')


def _match_filter(entry: LogEntry, expr: str) -> bool:
    if not expr:
        return True
    # split AND clauses
    clauses = [c.strip() for c in re.split(r"\bAND\b", expr) if c.strip()]
    for clause in clauses:
        if _SEV_RE.match(clause):
            op, level = _SEV_RE.match(clause).groups()
            target = SEVERITY_RANK.get(level, 0)
            actual = SEVERITY_RANK.get(entry.severity, 0)
            ok = {
                ">=": actual >= target,
                "<=": actual <= target,
                ">": actual > target,
                "<": actual < target,
                "=": actual == target,
                "!=": actual != target,
            }[op]
            if not ok:
                return False
            continue
        if _LOG_RE.match(clause):
            target = _LOG_RE.match(clause).group(1)
            if entry.log_name != target:
                return False
            continue
        # unknown clause → strict: no match
        return False
    return True


class LoggingProvider:
    def __init__(
        self,
        *,
        resource_manager: ResourceManagerProvider | None = None,
        stores: GcpStores | None = None,
    ) -> None:
        self.stores = stores or GcpStores()
        self.resource_manager = resource_manager or ResourceManagerProvider(stores=self.stores)
        self.data = LoggingDataStore()

    def write_log_entries(self, entries: list[dict[str, Any]]) -> int:
        count = 0
        for raw in entries:
            log_name = raw.get("logName") or ""
            project = _project_from_log_name(log_name)
            if not project:
                raise GcpInvalidRequest(f"invalid logName: {log_name}")
            self.resource_manager.ensure_project(project)
            entry = LogEntry(
                log_name=log_name,
                severity=raw.get("severity", "DEFAULT"),
                timestamp=raw.get("timestamp") or _now(),
                text_payload=raw.get("textPayload", ""),
                json_payload=raw.get("jsonPayload"),
                labels=dict(raw.get("labels") or {}),
                insert_id=raw.get("insertId") or uuid.uuid4().hex,
            )
            self.data.append(project, entry)
            count += 1
        return count

    def list_log_entries(
        self,
        project: str,
        *,
        filter_expr: str = "",
        page_size: int = 50,
    ) -> list[LogEntry]:
        entries = self.data.entries.get(project, [])
        out = [e for e in entries if _match_filter(e, filter_expr)]
        return out[-page_size:] if page_size > 0 else out

    def delete_log(self, project: str, log_name: str) -> int:
        entries = self.data.entries.get(project, [])
        before = len(entries)
        self.data.entries[project] = [e for e in entries if e.log_name != log_name]
        return before - len(self.data.entries[project])

    def create_sink(
        self,
        project: str,
        sink_id: str,
        *,
        destination: str,
        filter_expr: str = "",
    ) -> LogSink:
        full = f"projects/{project}/sinks/{sink_id}"
        if full in self.data.sinks:
            raise GcpAlreadyExists(f"sink '{full}' already exists")
        self.resource_manager.ensure_project(project)
        sink = LogSink(
            name=full,
            destination=destination,
            filter_expr=filter_expr,
            create_time=_now(),
        )
        self.data.sinks[full] = sink
        return sink

    def get_sink(self, project: str, sink_id: str) -> LogSink:
        full = f"projects/{project}/sinks/{sink_id}"
        sink = self.data.sinks.get(full)
        if sink is None:
            raise GcpNotFound(f"sink '{full}' not found")
        return sink

    def list_sinks(self, project: str) -> list[LogSink]:
        prefix = f"projects/{project}/sinks/"
        return [s for s in self.data.sinks.values() if s.name.startswith(prefix)]

    def delete_sink(self, project: str, sink_id: str) -> None:
        full = f"projects/{project}/sinks/{sink_id}"
        if full not in self.data.sinks:
            raise GcpNotFound(f"sink '{full}' not found")
        del self.data.sinks[full]

    def update_sink(
        self,
        project: str,
        sink_id: str,
        *,
        destination: str | None = None,
        filter_expr: str | None = None,
    ) -> LogSink:
        sink = self.get_sink(project, sink_id)
        if destination is not None:
            sink.destination = destination
        if filter_expr is not None:
            sink.filter_expr = filter_expr
        return sink
