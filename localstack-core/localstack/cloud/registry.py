"""Singleton registry of `CloudProvider` instances."""

from __future__ import annotations

from typing import Iterator

from localstack.cloud.base import CloudProvider


class CloudRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, CloudProvider] = {}

    def register(self, provider: CloudProvider, *, replace: bool = False) -> None:
        key = provider.name.lower()
        if not replace and key in self._providers:
            raise ValueError(f"cloud '{provider.name}' already registered")
        self._providers[key] = provider

    def unregister(self, name: str) -> None:
        self._providers.pop(name.lower(), None)

    def get(self, name: str) -> CloudProvider | None:
        return self._providers.get(name.lower())

    def require(self, name: str) -> CloudProvider:
        provider = self.get(name)
        if provider is None:
            raise LookupError(f"cloud '{name}' not registered (known: {self.list()})")
        return provider

    def list(self) -> tuple[str, ...]:
        return tuple(sorted(self._providers))

    def __iter__(self) -> Iterator[CloudProvider]:
        return iter(self._providers[k] for k in sorted(self._providers))

    def __len__(self) -> int:
        return len(self._providers)

    def __contains__(self, name: object) -> bool:
        return isinstance(name, str) and name.lower() in self._providers

    def clear(self) -> None:
        self._providers.clear()


# global singleton — tests can build their own instance instead
registry = CloudRegistry()
