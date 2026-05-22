"""GCP resource name parsing.

GCP uses path-based resource names: ``projects/{project}/locations/{loc}/{type}/{id}`` plus
optional child segments. Some services omit the location segment (e.g. global resources like
GCS buckets accessed via ``projects/{project}/buckets/{bucket}``).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from localstack.gcp.exceptions import GcpInvalidResourceName


@dataclass(frozen=True)
class GcpResourceName:
    project: str
    location: str | None
    resource_type: str
    name: str
    child_resources: tuple[tuple[str, str], ...] = field(default_factory=tuple)

    @classmethod
    def parse(cls, value: str) -> "GcpResourceName":
        parts = [p for p in value.strip("/").split("/") if p]
        if len(parts) < 4 or parts[0] != "projects":
            raise GcpInvalidResourceName(
                f"GCP resource name must start with 'projects/{{id}}/...': {value}"
            )
        project = parts[1]
        idx = 2
        location: str | None = None
        if len(parts) >= 4 and parts[idx] == "locations":
            location = parts[idx + 1]
            idx += 2
        if len(parts) - idx < 2:
            raise GcpInvalidResourceName(
                f"GCP resource name must include type and id: {value}"
            )
        resource_type = parts[idx]
        name = parts[idx + 1]
        remaining = parts[idx + 2 :]
        if len(remaining) % 2:
            raise GcpInvalidResourceName(
                f"GCP child segments must be type/id pairs: {value}"
            )
        children = tuple(zip(remaining[::2], remaining[1::2], strict=True))
        return cls(
            project=project,
            location=location,
            resource_type=resource_type,
            name=name,
            child_resources=children,
        )

    @property
    def full_name(self) -> str:
        parts = ["projects", self.project]
        if self.location is not None:
            parts.extend(["locations", self.location])
        parts.extend([self.resource_type, self.name])
        for ct, cn in self.child_resources:
            parts.extend([ct, cn])
        return "/".join(parts)
