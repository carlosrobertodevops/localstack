from __future__ import annotations

from dataclasses import dataclass

from localstack.azure.exceptions import AzureInvalidResourceId


@dataclass(frozen=True)
class AzureResourceId:
    subscription_id: str
    resource_group: str
    namespace: str
    resource_type: str
    name: str
    child_resources: tuple[tuple[str, str], ...] = ()

    @classmethod
    def parse(cls, value: str) -> "AzureResourceId":
        parts = [part for part in value.strip("/").split("/") if part]
        cls._require(parts, 0, "subscriptions", value)
        cls._require(parts, 2, "resourceGroups", value)
        cls._require(parts, 4, "providers", value)

        if len(parts) < 8:
            raise AzureInvalidResourceId(
                f"Azure Resource ID must include provider namespace, resource type, and name: {value}"
            )

        remaining = parts[8:]
        if len(remaining) % 2:
            raise AzureInvalidResourceId(
                f"Azure Resource ID child resources must be type/name pairs: {value}"
            )

        return cls(
            subscription_id=parts[1],
            resource_group=parts[3],
            namespace=parts[5],
            resource_type=parts[6],
            name=parts[7],
            child_resources=tuple(zip(remaining[::2], remaining[1::2], strict=True)),
        )

    @property
    def resource_id(self) -> str:
        parts = [
            "subscriptions",
            self.subscription_id,
            "resourceGroups",
            self.resource_group,
            "providers",
            self.namespace,
            self.resource_type,
            self.name,
        ]
        for resource_type, name in self.child_resources:
            parts.extend([resource_type, name])
        return "/" + "/".join(parts)

    @staticmethod
    def _require(parts: list[str], index: int, expected: str, value: str) -> None:
        if len(parts) <= index or parts[index].lower() != expected.lower():
            raise AzureInvalidResourceId(
                f"Azure Resource ID must include '{expected}' at segment {index}: {value}"
            )
