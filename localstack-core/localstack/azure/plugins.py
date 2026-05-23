"""Azure provider plugin registry — analog of `localstack.aws.services.plugins`."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable


@dataclass(frozen=True)
class AzureProviderPlugin:
    """Describes how to instantiate a provider for a `(namespace, resource_type)` pair."""

    namespace: str
    resource_type: str
    provider_factory: Callable[..., object]

    @property
    def name(self) -> str:
        return f"{self.namespace}/{self.resource_type}"


class AzureProviderRegistry:
    """In-memory registry. Plux-compatible: `load_builtins()` mirrors entry-point discovery."""

    def __init__(self) -> None:
        self._plugins: dict[tuple[str, str], AzureProviderPlugin] = {}

    def register(self, plugin: AzureProviderPlugin) -> None:
        self._plugins[(plugin.namespace.lower(), plugin.resource_type.lower())] = plugin

    def get(self, namespace: str, resource_type: str) -> AzureProviderPlugin | None:
        return self._plugins.get((namespace.lower(), resource_type.lower()))

    def namespaces(self) -> tuple[str, ...]:
        return tuple(sorted({p.namespace for p in self._plugins.values()}))

    def resource_types(self, namespace: str) -> tuple[str, ...]:
        ns_l = namespace.lower()
        return tuple(
            sorted({p.resource_type for p in self._plugins.values() if p.namespace.lower() == ns_l})
        )

    def load_builtins(self) -> None:
        for plugin in iter_builtin_plugins():
            self.register(plugin)


def iter_builtin_plugins() -> Iterable[AzureProviderPlugin]:
    """Static list of providers shipped in this repo. Replaces Plux entry-points for now."""
    from localstack.azure.resource_manager import ResourceManagerProvider
    from localstack.azure.services.cosmos.provider import MicrosoftDocumentDBProvider
    from localstack.azure.services.functions.provider import MicrosoftWebProvider
    from localstack.azure.services.keyvault.provider import MicrosoftKeyVaultProvider
    from localstack.azure.services.storage.provider import MicrosoftStorageProvider

    yield AzureProviderPlugin("Microsoft.Resources", "resourceGroups", ResourceManagerProvider)
    yield AzureProviderPlugin("Microsoft.Storage", "storageAccounts", MicrosoftStorageProvider)
    yield AzureProviderPlugin("Microsoft.Web", "sites", MicrosoftWebProvider)
    yield AzureProviderPlugin(
        "Microsoft.DocumentDB", "databaseAccounts", MicrosoftDocumentDBProvider
    )
    yield AzureProviderPlugin("Microsoft.KeyVault", "vaults", MicrosoftKeyVaultProvider)
