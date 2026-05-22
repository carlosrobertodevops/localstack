"""Pickle-based snapshot/restore for in-memory GCP state."""

from __future__ import annotations

import pickle
from pathlib import Path
from typing import Any

_PICKLE_PROTOCOL = pickle.HIGHEST_PROTOCOL


class GcpStateStore:
    def snapshot(self, gateway: Any, path: str | Path) -> None:
        payload = {
            "stores": gateway.stores,
            "storage_data": gateway.storage_provider.data,
            "pubsub_data": gateway.pubsub_provider.data,
            "firestore_data": gateway.firestore_provider.data,
            "functions_registry": gateway.functions_provider.registry,
            "iam_data": gateway.iam_provider.data,
        }
        Path(path).write_bytes(pickle.dumps(payload, protocol=_PICKLE_PROTOCOL))

    def restore(self, gateway: Any, path: str | Path) -> None:
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"snapshot not found: {path}")
        payload = pickle.loads(path.read_bytes())
        gateway.stores = payload["stores"]
        gateway.storage_provider.data = payload["storage_data"]
        gateway.pubsub_provider.data = payload["pubsub_data"]
        gateway.firestore_provider.data = payload["firestore_data"]
        gateway.functions_provider.registry = payload["functions_registry"]
        gateway.iam_provider.data = payload["iam_data"]
        gateway.resource_manager.stores = gateway.stores
        gateway.storage_provider.stores = gateway.stores
        gateway.pubsub_provider.stores = gateway.stores
        gateway.firestore_provider.stores = gateway.stores
        gateway.functions_provider.stores = gateway.stores
        gateway.iam_provider.stores = gateway.stores
