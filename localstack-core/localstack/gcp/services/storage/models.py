from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import Any

from localstack.gcp.stores import CaseInsensitiveDict


@dataclass
class GcsObject:
    name: str
    bucket: str
    content: bytes = b""
    content_type: str = "application/octet-stream"
    metadata: dict[str, str] = field(default_factory=dict)
    generation: int = 1
    size: int = 0
    updated: str = ""
    etag: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": "storage#object",
            "name": self.name,
            "bucket": self.bucket,
            "id": f"{self.bucket}/{self.name}/{self.generation}",
            "generation": str(self.generation),
            "contentType": self.content_type,
            "size": str(self.size),
            "updated": self.updated,
            "etag": self.etag,
            "metadata": self.metadata,
            "selfLink": f"https://storage.googleapis.com/storage/v1/b/{self.bucket}/o/{self.name}",
        }


@dataclass
class GcsBucket:
    name: str
    project: str
    location: str = "US"
    storage_class: str = "STANDARD"
    created: str = ""
    labels: dict[str, str] = field(default_factory=dict)
    objects: CaseInsensitiveDict = field(default_factory=CaseInsensitiveDict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": "storage#bucket",
            "name": self.name,
            "id": self.name,
            "projectNumber": self.project,
            "location": self.location,
            "storageClass": self.storage_class,
            "timeCreated": self.created,
            "labels": self.labels,
            "selfLink": f"https://storage.googleapis.com/storage/v1/b/{self.name}",
        }


class GcsDataStore:
    def __init__(self) -> None:
        self.buckets: CaseInsensitiveDict = CaseInsensitiveDict()

    def now_iso(self) -> str:
        return datetime.datetime.now(datetime.UTC).isoformat()
