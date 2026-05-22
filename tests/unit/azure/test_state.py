import json

import pytest

from localstack.azure.gateway import AzureGateway
from localstack.azure.scope import AzureScope
from localstack.azure.state import AzureStateStore


@pytest.fixture
def gateway():
    return AzureGateway()


def _seed(gateway):
    scope = AzureScope.for_resource_group("sub-1", "rg-dev", location="eastus")
    gateway.resource_manager.create_or_update_resource_group(
        scope, "rg-dev", {"location": "eastus"}
    )
    gateway.storage_provider.create_storage_account(
        scope, "acct1", {"location": "eastus"}
    )
    gateway.storage_provider.create_container("acct1", "c1")
    gateway.storage_provider.put_blob("acct1", "c1", "hello.txt", b"hi")
    gateway.cosmos_provider.data_store.ensure_account("cosmos1")
    gateway.cosmos_provider.create_sql_database("cosmos1", "db1")
    gateway.cosmos_provider.create_sql_container("cosmos1", "db1", "col1")
    gateway.cosmos_provider.upsert_item("cosmos1", "db1", "col1", {"id": "1", "v": 42})


def test_snapshot_then_restore_into_fresh_gateway(gateway, tmp_path):
    _seed(gateway)
    state = AzureStateStore()
    path = tmp_path / "azure.snapshot"
    state.snapshot(gateway, path)
    assert path.exists() and path.stat().st_size > 0

    fresh = AzureGateway()
    state.restore(fresh, path)

    # RG + storage account + blob + cosmos item all came back
    scope = AzureScope.for_resource_group("sub-1", "rg-dev")
    assert fresh.resource_manager.get_resource_group(scope, "rg-dev").location == "eastus"
    blob = fresh.storage_provider.get_blob("acct1", "c1", "hello.txt")
    assert blob.content == b"hi"
    item = fresh.cosmos_provider.get_item("cosmos1", "db1", "col1", "1")
    assert item == {"id": "1", "v": 42}


def test_snapshot_is_pickle_format(gateway, tmp_path):
    _seed(gateway)
    state = AzureStateStore()
    path = tmp_path / "azure.snapshot"
    state.snapshot(gateway, path)
    head = path.read_bytes()[:2]
    # pickle protocol-2+ files start with \x80\x0X
    assert head[0:1] == b"\x80"


def test_restore_missing_file_raises(gateway, tmp_path):
    state = AzureStateStore()
    with pytest.raises(FileNotFoundError):
        state.restore(gateway, tmp_path / "missing.snapshot")


def test_snapshot_overwrites_existing(gateway, tmp_path):
    state = AzureStateStore()
    path = tmp_path / "azure.snapshot"
    path.write_bytes(b"OLD")
    _seed(gateway)
    state.snapshot(gateway, path)
    assert path.read_bytes()[:3] != b"OLD"
