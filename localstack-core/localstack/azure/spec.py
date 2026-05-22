from __future__ import annotations

from dataclasses import dataclass

from localstack.azure.exceptions import AzureUnsupportedOperation


@dataclass(frozen=True)
class AzureServiceSpec:
    namespace: str
    resource_type: str
    api_versions: tuple[str, ...]
    locations: tuple[str, ...] = ()


class AzureServiceSpecRegistry:
    def __init__(self) -> None:
        self._specs: dict[tuple[str, str], AzureServiceSpec] = {}

    def register(self, spec: AzureServiceSpec) -> AzureServiceSpec:
        if not spec.namespace:
            raise ValueError("namespace must not be empty")
        if not spec.resource_type:
            raise ValueError("resource_type must not be empty")
        if not spec.api_versions:
            raise ValueError("api_versions must not be empty")

        self._specs[self._key(spec.namespace, spec.resource_type)] = spec
        return spec

    def get(self, namespace: str, resource_type: str) -> AzureServiceSpec:
        try:
            return self._specs[self._key(namespace, resource_type)]
        except KeyError as e:
            raise AzureUnsupportedOperation(
                f"Unsupported Azure resource type: {namespace}/{resource_type}",
                code="UnsupportedAzureResourceType",
            ) from e

    def namespaces(self) -> tuple[str, ...]:
        return tuple(sorted({spec.namespace for spec in self._specs.values()}))

    def resource_types(self, namespace: str) -> tuple[str, ...]:
        namespace_key = namespace.lower()
        return tuple(
            sorted(
                spec.resource_type
                for (registered_namespace, _), spec in self._specs.items()
                if registered_namespace == namespace_key
            )
        )

    @staticmethod
    def _key(namespace: str, resource_type: str) -> tuple[str, str]:
        return namespace.lower(), resource_type.lower()
