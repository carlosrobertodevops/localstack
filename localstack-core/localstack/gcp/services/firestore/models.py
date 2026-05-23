from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from localstack.gcp.stores import CaseInsensitiveDict


@dataclass
class FirestoreDocument:
    name: str  # projects/{p}/databases/{d}/documents/{coll}/{id}
    fields: dict[str, Any] = field(default_factory=dict)
    create_time: str = ""
    update_time: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "fields": self.fields,
            "createTime": self.create_time,
            "updateTime": self.update_time,
        }


@dataclass
class FirestoreDatabase:
    name: str  # projects/{p}/databases/{d}
    location_id: str = "nam5"
    type: str = "FIRESTORE_NATIVE"
    documents: CaseInsensitiveDict = field(default_factory=CaseInsensitiveDict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "locationId": self.location_id,
            "type": self.type,
        }


class FirestoreDataStore:
    def __init__(self) -> None:
        self.databases: CaseInsensitiveDict = CaseInsensitiveDict()
