from __future__ import annotations

from dataclasses import dataclass

from localstack.gcp.resource_names import GcpResourceName


@dataclass(frozen=True)
class GcpScope:
    project_id: str
    location: str | None = None

    @classmethod
    def for_project(cls, project_id: str) -> "GcpScope":
        return cls(project_id=project_id)

    @classmethod
    def for_location(cls, project_id: str, location: str) -> "GcpScope":
        return cls(project_id=project_id, location=location)

    @classmethod
    def from_resource_name(cls, name: str | GcpResourceName) -> "GcpScope":
        parsed = GcpResourceName.parse(name) if isinstance(name, str) else name
        return cls(project_id=parsed.project, location=parsed.location)
