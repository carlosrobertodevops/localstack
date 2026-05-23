from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from localstack.azure.stores import CaseInsensitiveDict


@dataclass(frozen=True)
class TableEntityKey:
    partition_key: str
    row_key: str


@dataclass
class TableState:
    name: str
    # composite key {(pk, rk): entity dict}
    entities: dict = field(default_factory=dict)


@dataclass
class TableAccountState:
    account_name: str
    tables: CaseInsensitiveDict = field(default_factory=CaseInsensitiveDict)


class TableStorageDataStore:
    def __init__(self) -> None:
        self.accounts: CaseInsensitiveDict = CaseInsensitiveDict()

    def ensure_account(self, name: str) -> TableAccountState:
        acc = self.accounts.get(name)
        if acc is None:
            acc = TableAccountState(account_name=name)
            self.accounts[name] = acc
        return acc

    def get_account(self, name: str) -> TableAccountState | None:
        return self.accounts.get(name)
