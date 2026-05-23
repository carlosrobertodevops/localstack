import pytest

from localstack.azure.exceptions import AzureNotFound
from localstack.azure.resource_manager import ResourceManagerProvider
from localstack.azure.scope import AzureScope
from localstack.azure.services.storage.provider import MicrosoftStorageProvider
from localstack.azure.stores import AzureStores


def test_create_get_list_and_delete_storage_account():
    provider, scope = _provider_with_resource_group()

    account = provider.create_storage_account(scope, "store1", {"location": "eastus"})

    assert account.name == "store1"
    assert account.id.endswith("/providers/Microsoft.Storage/storageAccounts/store1")
    assert provider.get_storage_account(scope, "store1") == account
    assert [item.name for item in provider.list_storage_accounts(scope)] == ["store1"]

    provider.delete_storage_account(scope, "store1")

    assert provider.list_storage_accounts(scope) == []
    with pytest.raises(AzureNotFound):
        provider.get_storage_account(scope, "store1")


def test_storage_account_requires_existing_resource_group():
    provider = MicrosoftStorageProvider()
    scope = AzureScope.for_resource_group("sub-123", "rg-dev", location="eastus")

    with pytest.raises(AzureNotFound) as exc:
        provider.create_storage_account(scope, "store1", {"location": "eastus"})

    assert "resource group" in str(exc.value)


def test_create_get_list_and_delete_blob_container():
    provider, scope = _provider_with_storage_account()

    container = provider.create_container("store1", "c1", metadata={"purpose": "test"})

    assert container.name == "c1"
    assert container.metadata == {"purpose": "test"}
    assert provider.get_container("store1", "c1") == container
    assert [item.name for item in provider.list_containers("store1")] == ["c1"]

    provider.delete_container("store1", "c1")
    assert provider.list_containers("store1") == []
    with pytest.raises(AzureNotFound):
        provider.get_container("store1", "c1")


def test_blob_container_requires_existing_storage_account():
    provider = MicrosoftStorageProvider()

    with pytest.raises(AzureNotFound) as exc:
        provider.create_container("store1", "c1")

    assert "storage account" in str(exc.value)


def test_put_get_list_and_delete_blob():
    provider, scope = _provider_with_storage_account()
    provider.create_container("store1", "c1")

    blob = provider.put_blob("store1", "c1", "a.txt", b"hello", content_type="text/plain")

    assert blob.name == "a.txt"
    assert provider.get_blob("store1", "c1", "a.txt").content == b"hello"
    assert provider.get_blob("store1", "c1", "a.txt").size == 5
    assert provider.get_blob("store1", "c1", "a.txt").content_type == "text/plain"
    assert [item.name for item in provider.list_blobs("store1", "c1")] == ["a.txt"]

    provider.delete_blob("store1", "c1", "a.txt")
    assert provider.list_blobs("store1", "c1") == []
    with pytest.raises(AzureNotFound):
        provider.get_blob("store1", "c1", "a.txt")


def test_put_blob_overwrites_existing_blob():
    provider, scope = _provider_with_storage_account()
    provider.create_container("store1", "c1")

    provider.put_blob("store1", "c1", "a.txt", b"one")
    provider.put_blob("store1", "c1", "a.txt", b"two")

    assert provider.get_blob("store1", "c1", "a.txt").content == b"two"
    assert [item.name for item in provider.list_blobs("store1", "c1")] == ["a.txt"]


def test_blob_requires_existing_container():
    provider, scope = _provider_with_storage_account()

    with pytest.raises(AzureNotFound) as exc:
        provider.put_blob("store1", "missing", "a.txt", b"hello")

    assert "container" in str(exc.value)


def test_create_list_and_delete_queue():
    provider, scope = _provider_with_storage_account()

    queue = provider.create_queue("store1", "q1")

    assert queue.name == "q1"
    assert [item.name for item in provider.list_queues("store1")] == ["q1"]

    provider.delete_queue("store1", "q1")
    assert provider.list_queues("store1") == []
    with pytest.raises(AzureNotFound):
        provider.get_queue("store1", "q1")


def test_send_receive_and_delete_queue_message():
    provider, scope = _provider_with_storage_account()
    provider.create_queue("store1", "q1")

    sent = provider.send_message("store1", "q1", "hello")
    received = provider.receive_messages("store1", "q1")

    assert sent.message_id
    assert len(received) == 1
    assert received[0].content == "hello"
    assert received[0].message_id == sent.message_id
    assert received[0].pop_receipt

    provider.delete_message("store1", "q1", received[0].message_id, received[0].pop_receipt)

    assert provider.receive_messages("store1", "q1") == []


def test_send_message_requires_existing_queue():
    provider, scope = _provider_with_storage_account()

    with pytest.raises(AzureNotFound) as exc:
        provider.send_message("store1", "missing", "hello")

    assert "queue" in str(exc.value)


def test_delete_storage_account_clears_blob_and_queue_data_plane():
    provider, scope = _provider_with_storage_account()
    provider.create_container("store1", "c1")
    provider.put_blob("store1", "c1", "a.txt", b"hello")
    provider.create_queue("store1", "q1")
    provider.send_message("store1", "q1", "hello")

    provider.delete_storage_account(scope, "store1")

    with pytest.raises(AzureNotFound):
        provider.list_containers("store1")
    with pytest.raises(AzureNotFound):
        provider.list_queues("store1")


def _provider_with_resource_group():
    stores = AzureStores()
    manager = ResourceManagerProvider(stores=stores)
    provider = MicrosoftStorageProvider(resource_manager=manager, stores=stores)
    scope = AzureScope.for_resource_group("sub-123", "rg-dev", location="eastus")
    manager.create_or_update_resource_group(scope, "rg-dev", {"location": "eastus"})
    return provider, scope


def _provider_with_storage_account():
    provider, scope = _provider_with_resource_group()
    provider.create_storage_account(scope, "store1", {"location": "eastus"})
    return provider, scope
