from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from localstack.azure.stores import CaseInsensitiveDict


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class BlobObjectState:
    name: str
    content: bytes
    metadata: dict[str, str] = field(default_factory=dict)
    content_type: str | None = None
    etag: str | None = None
    last_modified: datetime = field(default_factory=utc_now)

    @property
    def size(self) -> int:
        return len(self.content)


@dataclass
class BlobContainerState:
    name: str
    metadata: dict[str, str] = field(default_factory=dict)
    blobs: CaseInsensitiveDict = field(default_factory=CaseInsensitiveDict)


@dataclass
class QueueMessageState:
    message_id: str
    content: str
    pop_receipt: str | None = None
    insertion_time: datetime = field(default_factory=utc_now)
    dequeue_count: int = 0
    visible: bool = True


@dataclass
class QueueState:
    name: str
    metadata: dict[str, str] = field(default_factory=dict)
    messages: list[QueueMessageState] = field(default_factory=list)


@dataclass
class StorageAccountDataPlaneState:
    account_name: str
    containers: CaseInsensitiveDict = field(default_factory=CaseInsensitiveDict)
    queues: CaseInsensitiveDict = field(default_factory=CaseInsensitiveDict)


class StorageDataPlaneStore:
    def __init__(self) -> None:
        self.accounts: CaseInsensitiveDict = CaseInsensitiveDict()

    def get_account(self, account_name: str) -> StorageAccountDataPlaneState | None:
        return self.accounts.get(account_name)

    def ensure_account(self, account_name: str) -> StorageAccountDataPlaneState:
        account = self.accounts.get(account_name)
        if account is None:
            account = StorageAccountDataPlaneState(account_name=account_name)
            self.accounts[account_name] = account
        return account

    def delete_account(self, account_name: str) -> None:
        self.accounts.pop(account_name, None)


RawResource = dict[str, Any]
