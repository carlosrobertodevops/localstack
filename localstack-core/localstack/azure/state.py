"""Pickle-based snapshot/restore for the in-memory Azure state.

Snapshots all gateway-held stores into one file: ARM stores, Storage data plane,
Cosmos data plane, Functions registry. Restore overwrites the gateway's stores
in-place so existing router instances keep working.
"""

from __future__ import annotations

import pickle
from pathlib import Path
from typing import Any

_PICKLE_PROTOCOL = pickle.HIGHEST_PROTOCOL


class AzureStateStore:
    """Persist and rehydrate `AzureGateway` state from a single pickle file."""

    def snapshot(self, gateway: Any, path: str | Path) -> None:
        payload = {
            "stores": gateway.stores,
            "storage_data_store": gateway.storage_provider.data_store,
            "cosmos_data_store": gateway.cosmos_provider.data_store,
            "functions_registry": gateway.functions_registry,
        }
        path = Path(path)
        path.write_bytes(pickle.dumps(payload, protocol=_PICKLE_PROTOCOL))

    def restore(self, gateway: Any, path: str | Path) -> None:
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"snapshot not found: {path}")
        payload = pickle.loads(path.read_bytes())
        # rebind gateway-level + provider-level stores so all routers see the new state
        gateway.stores = payload["stores"]
        gateway.storage_provider.data_store = payload["storage_data_store"]
        gateway.cosmos_provider.data_store = payload["cosmos_data_store"]
        gateway.functions_registry._apps = payload["functions_registry"]._apps
        # rewire resource manager to point to the restored stores
        gateway.resource_manager.stores = gateway.stores
        gateway.storage_provider.stores = gateway.stores
        gateway.functions_provider.stores = gateway.stores
        gateway.cosmos_provider.stores = gateway.stores
