"""Azure Table Storage provider — table + entity CRUD (subset)."""

from __future__ import annotations

from typing import Any

from localstack.azure.exceptions import AzureInvalidRequest, AzureNotFound
from localstack.azure.services.tablestorage.models import (
    TableEntityKey,
    TableState,
    TableStorageDataStore,
)


class TableStorageProvider:
    def __init__(self, *, data_store: TableStorageDataStore | None = None) -> None:
        self.data_store = data_store or TableStorageDataStore()

    # -- tables --

    def create_table(self, account: str, table: str) -> TableState:
        acc = self.data_store.ensure_account(account)
        if table in acc.tables:
            raise AzureInvalidRequest(f"table already exists: {table}")
        state = TableState(name=table)
        acc.tables[table] = state
        return state

    def list_tables(self, account: str) -> list[TableState]:
        acc = self.data_store.ensure_account(account)
        return sorted(acc.tables.values(), key=lambda t: t.name.lower())

    def delete_table(self, account: str, table: str) -> None:
        acc = self.data_store.ensure_account(account)
        if acc.tables.pop(table, None) is None:
            raise AzureNotFound(f"table not found: {table}")

    # -- entities --

    def upsert_entity(
        self, account: str, table: str, entity: dict[str, Any]
    ) -> dict[str, Any]:
        pk = entity.get("PartitionKey")
        rk = entity.get("RowKey")
        if not pk or not rk:
            raise AzureInvalidRequest("entity requires PartitionKey + RowKey")
        state = self._require_table(account, table)
        stored = dict(entity)
        state.entities[(pk, rk)] = stored
        return stored

    def get_entity(
        self, account: str, table: str, partition_key: str, row_key: str
    ) -> dict[str, Any]:
        state = self._require_table(account, table)
        entity = state.entities.get((partition_key, row_key))
        if entity is None:
            raise AzureNotFound(f"entity not found: ({partition_key},{row_key})")
        return entity

    def query_entities(
        self,
        account: str,
        table: str,
        *,
        partition_key: str | None = None,
    ) -> list[dict[str, Any]]:
        state = self._require_table(account, table)
        if partition_key is None:
            entities = list(state.entities.values())
        else:
            entities = [
                v for (pk, _), v in state.entities.items() if pk == partition_key
            ]
        return sorted(entities, key=lambda e: (e.get("PartitionKey", ""), e.get("RowKey", "")))

    def delete_entity(
        self, account: str, table: str, partition_key: str, row_key: str
    ) -> None:
        state = self._require_table(account, table)
        if state.entities.pop((partition_key, row_key), None) is None:
            raise AzureNotFound(f"entity not found: ({partition_key},{row_key})")

    # -- helpers --

    def _require_table(self, account: str, table: str) -> TableState:
        acc = self.data_store.ensure_account(account)
        state = acc.tables.get(table)
        if state is None:
            raise AzureNotFound(f"table not found: {table}")
        return state
