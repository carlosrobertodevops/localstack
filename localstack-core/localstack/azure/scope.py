from __future__ import annotations

from dataclasses import dataclass

from localstack.azure.ids import AzureResourceId


@dataclass(frozen=True)
class AzureScope:
    subscription_id: str
    resource_group: str | None = None
    location: str | None = None

    @classmethod
    def for_subscription(cls, subscription_id: str) -> "AzureScope":
        return cls(subscription_id=subscription_id)

    @classmethod
    def for_resource_group(
        cls, subscription_id: str, resource_group: str, *, location: str | None = None
    ) -> "AzureScope":
        return cls(subscription_id=subscription_id, resource_group=resource_group, location=location)

    @classmethod
    def from_resource_id(
        cls, resource_id: str | AzureResourceId, *, location: str | None = None
    ) -> "AzureScope":
        parsed = AzureResourceId.parse(resource_id) if isinstance(resource_id, str) else resource_id
        return cls(
            subscription_id=parsed.subscription_id,
            resource_group=parsed.resource_group,
            location=location,
        )
