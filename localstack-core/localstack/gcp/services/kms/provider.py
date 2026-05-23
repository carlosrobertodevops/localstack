from __future__ import annotations

import datetime
import os

from localstack.gcp.exceptions import GcpAlreadyExists, GcpInvalidRequest, GcpNotFound
from localstack.gcp.resource_manager import ResourceManagerProvider
from localstack.gcp.services.kms.models import (
    CryptoKey,
    CryptoKeyVersion,
    KeyRing,
    KmsDataStore,
)
from localstack.gcp.stores import GcpStores


def _now() -> str:
    return datetime.datetime.now(datetime.UTC).isoformat()


def _xor(data: bytes, key: bytes) -> bytes:
    if not key:
        raise GcpInvalidRequest("key_material is empty")
    repeated = (key * ((len(data) // len(key)) + 1))[: len(data)]
    return bytes(a ^ b for a, b in zip(data, repeated))


class KmsProvider:
    def __init__(
        self,
        *,
        resource_manager: ResourceManagerProvider | None = None,
        stores: GcpStores | None = None,
    ) -> None:
        self.stores = stores or GcpStores()
        self.resource_manager = resource_manager or ResourceManagerProvider(stores=self.stores)
        self.data = KmsDataStore()

    def create_keyring(self, project: str, location: str, keyring_id: str) -> KeyRing:
        full = f"projects/{project}/locations/{location}/keyRings/{keyring_id}"
        if full in self.data.keyrings:
            raise GcpAlreadyExists(f"keyring '{full}' already exists")
        self.resource_manager.ensure_project(project)
        kr = KeyRing(name=full, create_time=_now())
        self.data.keyrings[full] = kr
        return kr

    def get_keyring(self, project: str, location: str, keyring_id: str) -> KeyRing:
        full = f"projects/{project}/locations/{location}/keyRings/{keyring_id}"
        kr = self.data.keyrings.get(full)
        if kr is None:
            raise GcpNotFound(f"keyring '{full}' not found")
        return kr

    def list_keyrings(self, project: str, location: str) -> list[KeyRing]:
        prefix = f"projects/{project}/locations/{location}/keyRings/"
        return [kr for kr in self.data.keyrings.values() if kr.name.startswith(prefix)]

    def create_cryptokey(
        self,
        project: str,
        location: str,
        keyring_id: str,
        cryptokey_id: str,
        *,
        purpose: str = "ENCRYPT_DECRYPT",
    ) -> CryptoKey:
        kr = self.get_keyring(project, location, keyring_id)
        if cryptokey_id in kr.crypto_keys:
            raise GcpAlreadyExists(f"cryptokey '{cryptokey_id}' already exists in '{kr.name}'")
        ck_full = f"{kr.name}/cryptoKeys/{cryptokey_id}"
        ck = CryptoKey(name=ck_full, purpose=purpose, create_time=_now())
        v1 = CryptoKeyVersion(name=f"{ck_full}/cryptoKeyVersions/1", create_time=_now())
        ck.versions.append(v1)
        kr.crypto_keys[cryptokey_id] = ck
        return ck

    def get_cryptokey(
        self, project: str, location: str, keyring_id: str, cryptokey_id: str
    ) -> CryptoKey:
        kr = self.get_keyring(project, location, keyring_id)
        ck = kr.crypto_keys.get(cryptokey_id)
        if ck is None:
            raise GcpNotFound(f"cryptokey '{cryptokey_id}' not found in '{kr.name}'")
        return ck

    def list_cryptokeys(
        self, project: str, location: str, keyring_id: str
    ) -> list[CryptoKey]:
        kr = self.get_keyring(project, location, keyring_id)
        return list(kr.crypto_keys.values())

    def create_cryptokey_version(
        self, project: str, location: str, keyring_id: str, cryptokey_id: str
    ) -> CryptoKeyVersion:
        ck = self.get_cryptokey(project, location, keyring_id, cryptokey_id)
        number = len(ck.versions) + 1
        v = CryptoKeyVersion(
            name=f"{ck.name}/cryptoKeyVersions/{number}", create_time=_now()
        )
        ck.versions.append(v)
        ck.primary_version_id = number
        return v

    def destroy_version(
        self, project: str, location: str, keyring_id: str, cryptokey_id: str, version: int
    ) -> CryptoKeyVersion:
        ck = self.get_cryptokey(project, location, keyring_id, cryptokey_id)
        if version < 1 or version > len(ck.versions):
            raise GcpNotFound(f"version {version} not found")
        v = ck.versions[version - 1]
        v.state = "DESTROYED"
        return v

    def encrypt(self, cryptokey_name: str, plaintext: bytes) -> bytes:
        ck = self._lookup_cryptokey_by_name(cryptokey_name)
        nonce = os.urandom(12)
        primary = ck.primary()
        body = _xor(plaintext, primary.key_material)
        return nonce + body

    def decrypt(self, cryptokey_name: str, ciphertext: bytes) -> bytes:
        ck = self._lookup_cryptokey_by_name(cryptokey_name)
        if len(ciphertext) < 12:
            raise GcpInvalidRequest("ciphertext too short")
        body = ciphertext[12:]
        primary = ck.primary()
        return _xor(body, primary.key_material)

    def _lookup_cryptokey_by_name(self, name: str) -> CryptoKey:
        # name = projects/{p}/locations/{l}/keyRings/{kr}/cryptoKeys/{ck}
        parts = name.split("/")
        if len(parts) != 8 or parts[0] != "projects" or parts[2] != "locations":
            raise GcpInvalidRequest(f"invalid cryptokey name: {name}")
        return self.get_cryptokey(parts[1], parts[3], parts[5], parts[7])
