from __future__ import annotations

from localstack.azure.defaults import create_default_registry
from localstack.azure.exceptions import AzureInvalidRequest, AzureNotFound
from localstack.azure.ids import AzureResourceId
from localstack.azure.resource_manager import ResourceManagerProvider
from localstack.azure.scope import AzureScope
from localstack.azure.services.cosmos.models import (
    CosmosAccountDataPlaneState,
    CosmosDataPlaneStore,
    CosmosSqlContainerState,
    CosmosSqlDatabaseState,
)
from localstack.azure.spec import AzureServiceSpec
from localstack.azure.stores import AzureGenericResource, AzureStores


class MicrosoftDocumentDBProvider:
    def __init__(
        self,
        *,
        resource_manager: ResourceManagerProvider | None = None,
        stores: AzureStores | None = None,
        data_store: CosmosDataPlaneStore | None = None,
    ) -> None:
        self.stores = stores or AzureStores()
        self.resource_manager = resource_manager or ResourceManagerProvider(
            stores=self.stores, registry=create_default_registry()
        )
        self.resource_manager.registry.register(
            AzureServiceSpec(
                namespace="Microsoft.DocumentDB",
                resource_type="databaseAccounts",
                api_versions=("2023-11-15",),
                locations=("eastus", "westeurope", "westus2", "brazilsouth"),
            )
        )
        self.data_store = data_store or CosmosDataPlaneStore()

    def create_database_account(
        self,
        scope: AzureScope,
        name: str,
        parameters: dict,
        *,
        api_version: str | None = "2023-11-15",
    ) -> AzureGenericResource:
        resource = self.resource_manager.create_or_update_resource(
            scope, self._account_id(scope, name), parameters, api_version=api_version
        )
        self.data_store.ensure_account(name)
        return resource

    def get_database_account(self, scope: AzureScope, name: str) -> AzureGenericResource:
        return self.resource_manager.get_resource(scope, self._account_id(scope, name))

    def list_database_accounts(self, scope: AzureScope) -> list[AzureGenericResource]:
        return [
            resource
            for resource in self.resource_manager.list_resources(
                AzureScope.for_subscription(scope.subscription_id), resource_group=scope.resource_group
            )
            if resource.type.lower() == "microsoft.documentdb/databaseaccounts"
        ]

    def delete_database_account(self, scope: AzureScope, name: str) -> None:
        self.resource_manager.delete_resource(scope, self._account_id(scope, name))
        self.data_store.delete_account(name)

    def create_sql_database(self, account_name: str, database_name: str) -> CosmosSqlDatabaseState:
        account = self._get_data_account(account_name)
        database = CosmosSqlDatabaseState(name=database_name)
        account.sql_databases[database_name] = database
        return database

    def get_sql_database(self, account_name: str, database_name: str) -> CosmosSqlDatabaseState:
        account = self._get_data_account(account_name)
        database = account.sql_databases.get(database_name)
        if database is None:
            raise AzureNotFound(f"Azure Cosmos SQL database not found: {database_name}")
        return database

    def list_sql_databases(self, account_name: str) -> list[CosmosSqlDatabaseState]:
        account = self._get_data_account(account_name)
        return sorted(account.sql_databases.values(), key=lambda database: database.name.lower())

    def delete_sql_database(self, account_name: str, database_name: str) -> None:
        account = self._get_data_account(account_name)
        if account.sql_databases.pop(database_name, None) is None:
            raise AzureNotFound(f"Azure Cosmos SQL database not found: {database_name}")

    def create_sql_container(
        self,
        account_name: str,
        database_name: str,
        container_name: str,
        *,
        partition_key: str | None = None,
    ) -> CosmosSqlContainerState:
        database = self.get_sql_database(account_name, database_name)
        container = CosmosSqlContainerState(name=container_name, partition_key=partition_key)
        database.containers[container_name] = container
        return container

    def get_sql_container(
        self, account_name: str, database_name: str, container_name: str
    ) -> CosmosSqlContainerState:
        database = self.get_sql_database(account_name, database_name)
        container = database.containers.get(container_name)
        if container is None:
            raise AzureNotFound(f"Azure Cosmos SQL container not found: {container_name}")
        return container

    def list_sql_containers(
        self, account_name: str, database_name: str
    ) -> list[CosmosSqlContainerState]:
        database = self.get_sql_database(account_name, database_name)
        return sorted(database.containers.values(), key=lambda container: container.name.lower())

    def delete_sql_container(
        self, account_name: str, database_name: str, container_name: str
    ) -> None:
        database = self.get_sql_database(account_name, database_name)
        if database.containers.pop(container_name, None) is None:
            raise AzureNotFound(f"Azure Cosmos SQL container not found: {container_name}")

    # -- item CRUD --

    def upsert_item(
        self,
        account_name: str,
        database_name: str,
        container_name: str,
        item: dict,
        *,
        item_id_field: str = "id",
    ) -> dict:
        container = self.get_sql_container(account_name, database_name, container_name)
        item_id = item.get(item_id_field)
        if not item_id:
            raise AzureInvalidRequest(f"item missing required '{item_id_field}' field")
        stored = dict(item)
        container.items[item_id] = stored
        return stored

    def get_item(
        self, account_name: str, database_name: str, container_name: str, item_id: str
    ) -> dict:
        container = self.get_sql_container(account_name, database_name, container_name)
        item = container.items.get(item_id)
        if item is None:
            raise AzureNotFound(f"Azure Cosmos item not found: {item_id}")
        return item

    def list_items(
        self, account_name: str, database_name: str, container_name: str
    ) -> list[dict]:
        container = self.get_sql_container(account_name, database_name, container_name)
        return sorted(container.items.values(), key=lambda doc: str(doc.get("id", "")).lower())

    def delete_item(
        self, account_name: str, database_name: str, container_name: str, item_id: str
    ) -> None:
        container = self.get_sql_container(account_name, database_name, container_name)
        if container.items.pop(item_id, None) is None:
            raise AzureNotFound(f"Azure Cosmos item not found: {item_id}")

    def _get_data_account(self, account_name: str) -> CosmosAccountDataPlaneState:
        account = self.data_store.get_account(account_name)
        if account is None:
            raise AzureNotFound(f"Azure Cosmos account not found: {account_name}")
        return account

    @staticmethod
    def _account_id(scope: AzureScope, name: str) -> AzureResourceId:
        return AzureResourceId.parse(
            f"/subscriptions/{scope.subscription_id}/resourceGroups/{scope.resource_group}/providers/"
            f"Microsoft.DocumentDB/databaseAccounts/{name}"
        )
