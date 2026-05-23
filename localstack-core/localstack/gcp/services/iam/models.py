from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from localstack.gcp.stores import CaseInsensitiveDict


@dataclass
class ServiceAccount:
    name: str  # projects/{p}/serviceAccounts/{sa-email}
    email: str
    unique_id: str
    display_name: str = ""
    disabled: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "email": self.email,
            "uniqueId": self.unique_id,
            "displayName": self.display_name,
            "disabled": self.disabled,
        }


class IamDataStore:
    def __init__(self) -> None:
        self.service_accounts: CaseInsensitiveDict = CaseInsensitiveDict()
        self._sa_seq = 0

    def next_unique_id(self) -> str:
        self._sa_seq += 1
        return str(100_000_000_000 + self._sa_seq)
