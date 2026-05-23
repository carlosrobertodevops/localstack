from localstack.cloud import CloudRegistry, register_builtins


def test_register_builtins_adds_azure_and_aws():
    reg = CloudRegistry()
    register_builtins(reg)
    assert "azure" in reg
    assert "aws" in reg


def test_azure_provider_metadata_shape():
    reg = CloudRegistry()
    register_builtins(reg)
    azure = reg.require("azure")
    assert azure.package == "localstack.azure"
    assert "*.blob.core.windows.net" in azure.edge_hosts
    assert azure.metadata["scope_terms"]["account"] == "subscription"


def test_azure_factory_builds_gateway():
    reg = CloudRegistry()
    register_builtins(reg)
    gw = reg.require("azure").build_gateway()
    # AzureGateway is a WSGI callable
    assert callable(gw)
    assert gw.__class__.__name__ == "AzureGateway"


def test_azure_state_store_factory_builds_store():
    reg = CloudRegistry()
    register_builtins(reg)
    store = reg.require("azure").build_state_store()
    assert store.__class__.__name__ == "AzureStateStore"


def test_azure_plugin_registry_loads_builtins():
    reg = CloudRegistry()
    register_builtins(reg)
    plugins = reg.require("azure").build_plugin_registry()
    assert plugins.get("Microsoft.Storage", "storageAccounts") is not None
    assert plugins.get("Microsoft.KeyVault", "vaults") is not None


def test_register_builtins_is_idempotent():
    reg = CloudRegistry()
    register_builtins(reg)
    register_builtins(reg)  # no exception
    assert len(reg) == 3  # aws + azure + gcp


def test_aws_provider_registered_with_sigv4_marker():
    reg = CloudRegistry()
    register_builtins(reg)
    aws = reg.require("aws")
    assert aws.metadata["auth"] == "sigv4"
    assert "*.amazonaws.com" in aws.edge_hosts
