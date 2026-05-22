from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

from localstack.gcp.stores import CaseInsensitiveDict


@dataclass
class CryptoKeyVersion:
    name: str  # .../cryptoKeyVersions/{n}
    state: str = "ENABLED"
    algorithm: str = "GOOGLE_SYMMETRIC_ENCRYPTION"
    create_time: str = ""
    key_material: bytes = field(default_factory=lambda: os.urandom(32))

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "state": self.state,
            "algorithm": self.algorithm,
            "createTime": self.create_time,
        }


@dataclass
class CryptoKey:
    name: str  # projects/{p}/locations/{l}/keyRings/{kr}/cryptoKeys/{id}
    purpose: str = "ENCRYPT_DECRYPT"
    primary_version_id: int = 1
    versions: list[CryptoKeyVersion] = field(default_factory=list)
    create_time: str = ""

    def primary(self) -> CryptoKeyVersion:
        return self.versions[self.primary_version_id - 1]

    def to_dict(self) -> dict[str, Any]:
        primary = self.primary()
        return {
            "name": self.name,
            "purpose": self.purpose,
            "createTime": self.create_time,
            "primary": primary.to_dict(),
        }


@dataclass
class KeyRing:
    name: str  # projects/{p}/locations/{l}/keyRings/{id}
    create_time: str = ""
    crypto_keys: CaseInsensitiveDict = field(default_factory=CaseInsensitiveDict)

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "createTime": self.create_time}


class KmsDataStore:
    def __init__(self) -> None:
        self.keyrings: CaseInsensitiveDict = CaseInsensitiveDict()
