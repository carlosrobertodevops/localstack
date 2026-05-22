from __future__ import annotations

from dataclasses import dataclass

from localstack.gcp.exceptions import GcpUnsupportedOperation


@dataclass(frozen=True)
class GcpServiceSpec:
    service: str  # e.g. "storage", "pubsub"
    resource_type: str  # e.g. "buckets", "topics"
    api_versions: tuple[str, ...]
    locations: tuple[str, ...] = ()


class GcpServiceSpecRegistry:
    def __init__(self) -> None:
        self._specs: dict[tuple[str, str], GcpServiceSpec] = {}

    def register(self, spec: GcpServiceSpec) -> GcpServiceSpec:
        if not spec.service:
            raise ValueError("service must not be empty")
        if not spec.resource_type:
            raise ValueError("resource_type must not be empty")
        if not spec.api_versions:
            raise ValueError("api_versions must not be empty")
        self._specs[self._key(spec.service, spec.resource_type)] = spec
        return spec

    def get(self, service: str, resource_type: str) -> GcpServiceSpec:
        try:
            return self._specs[self._key(service, resource_type)]
        except KeyError as e:
            raise GcpUnsupportedOperation(
                f"Unsupported GCP resource type: {service}/{resource_type}",
                code="UnsupportedGcpResourceType",
            ) from e

    def services(self) -> tuple[str, ...]:
        return tuple(sorted({spec.service for spec in self._specs.values()}))

    def resource_types(self, service: str) -> tuple[str, ...]:
        key = service.lower()
        return tuple(
            sorted(
                spec.resource_type
                for (svc, _), spec in self._specs.items()
                if svc == key
            )
        )

    @staticmethod
    def _key(service: str, resource_type: str) -> tuple[str, str]:
        return service.lower(), resource_type.lower()
