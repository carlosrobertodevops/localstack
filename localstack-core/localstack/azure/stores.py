from __future__ import annotations

from collections import UserDict
from dataclasses import dataclass, field
from typing import Any


class CaseInsensitiveDict(UserDict):
    def __contains__(self, key: object) -> bool:
        return super().__contains__(self._normalize(key))

    def __getitem__(self, key: str) -> Any:
        return super().__getitem__(self._normalize(key))

    def __setitem__(self, key: str, value: Any) -> None:
        super().__setitem__(self._normalize(key), value)

    def __delitem__(self, key: str) -> None:
        super().__delitem__(self._normalize(key))

    def get(self, key: str, default: Any = None) -> Any:
        return super().get(self._normalize(key), default)

    def pop(self, key: str, default: Any = None) -> Any:
        return super().pop(self._normalize(key), default)

    @staticmethod
    def _normalize(key: object) -> object:
        return key.lower() if isinstance(key, str) else key


@dataclass
class AzureResourceGroup:
    id: str
    name: str
    location: str
    tags: dict[str, str] = field(default_factory=dict)
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass
class AzureGenericResource:
    id: str
    name: str
    type: str
    location: str | None = None
    api_version: str | None = None
    tags: dict[str, str] = field(default_factory=dict)
    properties: dict[str, Any] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class AzureSubscriptionStore:
    resource_groups: CaseInsensitiveDict = field(default_factory=CaseInsensitiveDict)
    resources: CaseInsensitiveDict = field(default_factory=CaseInsensitiveDict)


class AzureStores:
    def __init__(self) -> None:
        self._subscriptions: CaseInsensitiveDict = CaseInsensitiveDict()

    def get_subscription(self, subscription_id: str) -> AzureSubscriptionStore:
        store = self._subscriptions.get(subscription_id)
        if store is None:
            store = AzureSubscriptionStore()
            self._subscriptions[subscription_id] = store
        return store

    def clear(self) -> None:
        self._subscriptions.clear()
