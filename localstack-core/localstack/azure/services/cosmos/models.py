from __future__ import annotations

from dataclasses import dataclass, field

from localstack.azure.stores import CaseInsensitiveDict


@dataclass
class CosmosSqlContainerState:
    name: str
    partition_key: str | None = None
    items: CaseInsensitiveDict = field(default_factory=CaseInsensitiveDict)


@dataclass
class CosmosSqlDatabaseState:
    name: str
    containers: CaseInsensitiveDict = field(default_factory=CaseInsensitiveDict)


@dataclass
class CosmosAccountDataPlaneState:
    account_name: str
    sql_databases: CaseInsensitiveDict = field(default_factory=CaseInsensitiveDict)


class CosmosDataPlaneStore:
    def __init__(self) -> None:
        self.accounts: CaseInsensitiveDict = CaseInsensitiveDict()

    def get_account(self, account_name: str) -> CosmosAccountDataPlaneState | None:
        return self.accounts.get(account_name)

    def ensure_account(self, account_name: str) -> CosmosAccountDataPlaneState:
        account = self.accounts.get(account_name)
        if account is None:
            account = CosmosAccountDataPlaneState(account_name=account_name)
            self.accounts[account_name] = account
        return account

    def delete_account(self, account_name: str) -> None:
        self.accounts.pop(account_name, None)
