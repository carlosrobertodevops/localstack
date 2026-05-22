import pytest

from localstack.azure.plugins import (
    AzureProviderPlugin,
    AzureProviderRegistry,
    iter_builtin_plugins,
)


class _StubProvider:
    pass


def test_plugin_carries_namespace_and_type():
    plugin = AzureProviderPlugin(
        namespace="Microsoft.Foo",
        resource_type="bars",
        provider_factory=_StubProvider,
    )
    assert plugin.name == "Microsoft.Foo/bars"


def test_registry_register_and_get():
    registry = AzureProviderRegistry()
    plugin = AzureProviderPlugin("Microsoft.Foo", "bars", _StubProvider)
    registry.register(plugin)
    assert registry.get("Microsoft.Foo", "bars") is plugin


def test_registry_get_missing_returns_none():
    registry = AzureProviderRegistry()
    assert registry.get("missing", "x") is None


def test_registry_namespaces_sorted():
    registry = AzureProviderRegistry()
    registry.register(AzureProviderPlugin("ns.B", "x", _StubProvider))
    registry.register(AzureProviderPlugin("ns.A", "y", _StubProvider))
    assert registry.namespaces() == ("ns.A", "ns.B")


def test_registry_resource_types_for_namespace():
    registry = AzureProviderRegistry()
    registry.register(AzureProviderPlugin("ns.A", "y", _StubProvider))
    registry.register(AzureProviderPlugin("ns.A", "x", _StubProvider))
    registry.register(AzureProviderPlugin("ns.B", "z", _StubProvider))
    assert registry.resource_types("ns.A") == ("x", "y")
    assert registry.resource_types("ns.B") == ("z",)


def test_iter_builtin_plugins_includes_core_services():
    names = {p.name for p in iter_builtin_plugins()}
    assert "Microsoft.Storage/storageAccounts" in names
    assert "Microsoft.Web/sites" in names
    assert "Microsoft.DocumentDB/databaseAccounts" in names
    assert "Microsoft.Resources/resourceGroups" in names


def test_registry_load_builtins():
    registry = AzureProviderRegistry()
    registry.load_builtins()
    assert registry.get("Microsoft.Storage", "storageAccounts") is not None
    assert registry.get("Microsoft.KeyVault", "vaults") is not None
