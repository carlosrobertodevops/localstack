import pytest

from localstack.azure.exceptions import AzureNotFound
from localstack.azure.resource_manager import ResourceManagerProvider
from localstack.azure.scope import AzureScope
from localstack.azure.services.cosmos.provider import MicrosoftDocumentDBProvider
from localstack.azure.services.functions.provider import MicrosoftWebProvider
from localstack.azure.stores import AzureStores


def test_create_get_list_and_delete_function_app():
    provider, scope = _web_provider_with_resource_group()

    app = provider.create_function_app(scope, "fn1", {"location": "eastus"})

    assert app.name == "fn1"
    assert app.type == "Microsoft.Web/sites"
    assert app.raw["kind"] == "functionapp"
    assert provider.get_function_app(scope, "fn1") == app
    assert [item.name for item in provider.list_function_apps(scope)] == ["fn1"]

    provider.delete_function_app(scope, "fn1")
    assert provider.list_function_apps(scope) == []
    with pytest.raises(AzureNotFound):
        provider.get_function_app(scope, "fn1")


def test_create_get_list_and_delete_cosmos_account():
    provider, scope = _cosmos_provider_with_resource_group()

    account = provider.create_database_account(scope, "cosmos1", {"location": "eastus"})

    assert account.name == "cosmos1"
    assert account.type == "Microsoft.DocumentDB/databaseAccounts"
    assert provider.get_database_account(scope, "cosmos1") == account
    assert [item.name for item in provider.list_database_accounts(scope)] == ["cosmos1"]

    provider.delete_database_account(scope, "cosmos1")
    assert provider.list_database_accounts(scope) == []
    with pytest.raises(AzureNotFound):
        provider.get_database_account(scope, "cosmos1")


def test_create_get_list_and_delete_cosmos_sql_database_and_container():
    provider, scope = _cosmos_provider_with_resource_group()
    provider.create_database_account(scope, "cosmos1", {"location": "eastus"})

    database = provider.create_sql_database("cosmos1", "db1")
    container = provider.create_sql_container("cosmos1", "db1", "c1", partition_key="/pk")

    assert database.name == "db1"
    assert container.name == "c1"
    assert container.partition_key == "/pk"
    assert provider.get_sql_container("cosmos1", "db1", "c1") == container
    assert [item.name for item in provider.list_sql_containers("cosmos1", "db1")] == ["c1"]

    provider.delete_sql_container("cosmos1", "db1", "c1")
    assert provider.list_sql_containers("cosmos1", "db1") == []
    provider.delete_sql_database("cosmos1", "db1")
    assert provider.list_sql_databases("cosmos1") == []


def _web_provider_with_resource_group():
    stores = AzureStores()
    manager = ResourceManagerProvider(stores=stores)
    provider = MicrosoftWebProvider(resource_manager=manager, stores=stores)
    scope = AzureScope.for_resource_group("sub-123", "rg-dev", location="eastus")
    manager.create_or_update_resource_group(scope, "rg-dev", {"location": "eastus"})
    return provider, scope


def _cosmos_provider_with_resource_group():
    stores = AzureStores()
    manager = ResourceManagerProvider(stores=stores)
    provider = MicrosoftDocumentDBProvider(resource_manager=manager, stores=stores)
    scope = AzureScope.for_resource_group("sub-123", "rg-dev", location="eastus")
    manager.create_or_update_resource_group(scope, "rg-dev", {"location": "eastus"})
    return provider, scope
