from __future__ import annotations

from uuid import uuid4

from localstack.azure.defaults import create_default_registry
from localstack.azure.exceptions import AzureNotFound
from localstack.azure.ids import AzureResourceId
from localstack.azure.resource_manager import ResourceManagerProvider
from localstack.azure.scope import AzureScope
from localstack.azure.services.storage.models import (
    BlobContainerState,
    BlobObjectState,
    QueueMessageState,
    QueueState,
    StorageAccountDataPlaneState,
    StorageDataPlaneStore,
)
from localstack.azure.spec import AzureServiceSpec
from localstack.azure.stores import AzureGenericResource, AzureStores


class MicrosoftStorageProvider:
    def __init__(
        self,
        *,
        resource_manager: ResourceManagerProvider | None = None,
        stores: AzureStores | None = None,
        data_store: StorageDataPlaneStore | None = None,
    ) -> None:
        self.stores = stores or AzureStores()
        self.resource_manager = resource_manager or ResourceManagerProvider(
            stores=self.stores, registry=create_default_registry()
        )
        self.resource_manager.registry.register(
            AzureServiceSpec(
                namespace="Microsoft.Storage",
                resource_type="storageAccounts",
                api_versions=("2023-01-01",),
                locations=("eastus", "westeurope", "westus2", "brazilsouth"),
            )
        )
        self.data_store = data_store or StorageDataPlaneStore()

    def create_storage_account(
        self,
        scope: AzureScope,
        account_name: str,
        parameters: dict,
        *,
        api_version: str | None = "2023-01-01",
    ) -> AzureGenericResource:
        resource_group = self._scope_resource_group(scope)
        resource_id = self._storage_account_id(scope.subscription_id, resource_group, account_name)
        resource = self.resource_manager.create_or_update_resource(
            scope,
            resource_id,
            parameters,
            api_version=api_version,
        )
        self.data_store.ensure_account(account_name)
        return resource

    def get_storage_account(self, scope: AzureScope, account_name: str) -> AzureGenericResource:
        resource_group = self._scope_resource_group(scope)
        return self.resource_manager.get_resource(
            scope, self._storage_account_id(scope.subscription_id, resource_group, account_name)
        )

    def list_storage_accounts(self, scope: AzureScope) -> list[AzureGenericResource]:
        return [
            resource
            for resource in self.resource_manager.list_resources(
                AzureScope.for_subscription(scope.subscription_id), resource_group=scope.resource_group
            )
            if resource.type.lower() == "microsoft.storage/storageaccounts"
        ]

    def delete_storage_account(self, scope: AzureScope, account_name: str) -> None:
        resource_group = self._scope_resource_group(scope)
        self.resource_manager.delete_resource(
            scope, self._storage_account_id(scope.subscription_id, resource_group, account_name)
        )
        self.data_store.delete_account(account_name)

    def create_container(
        self, account_name: str, container_name: str, *, metadata: dict[str, str] | None = None
    ) -> BlobContainerState:
        account = self._get_data_account(account_name)
        container = BlobContainerState(name=container_name, metadata=dict(metadata or {}))
        account.containers[container_name] = container
        return container

    def get_container(self, account_name: str, container_name: str) -> BlobContainerState:
        account = self._get_data_account(account_name)
        container = account.containers.get(container_name)
        if container is None:
            raise AzureNotFound(f"Azure blob container not found: {container_name}")
        return container

    def list_containers(self, account_name: str) -> list[BlobContainerState]:
        account = self._get_data_account(account_name)
        return sorted(account.containers.values(), key=lambda container: container.name.lower())

    def delete_container(self, account_name: str, container_name: str) -> None:
        account = self._get_data_account(account_name)
        if account.containers.pop(container_name, None) is None:
            raise AzureNotFound(f"Azure blob container not found: {container_name}")

    def put_blob(
        self,
        account_name: str,
        container_name: str,
        blob_name: str,
        content: bytes,
        *,
        metadata: dict[str, str] | None = None,
        content_type: str | None = None,
    ) -> BlobObjectState:
        container = self.get_container(account_name, container_name)
        blob = BlobObjectState(
            name=blob_name,
            content=bytes(content),
            metadata=dict(metadata or {}),
            content_type=content_type,
            etag=str(uuid4()),
        )
        container.blobs[blob_name] = blob
        return blob

    def get_blob(self, account_name: str, container_name: str, blob_name: str) -> BlobObjectState:
        container = self.get_container(account_name, container_name)
        blob = container.blobs.get(blob_name)
        if blob is None:
            raise AzureNotFound(f"Azure blob not found: {blob_name}")
        return blob

    def list_blobs(
        self, account_name: str, container_name: str, *, prefix: str | None = None
    ) -> list[BlobObjectState]:
        container = self.get_container(account_name, container_name)
        blobs = list(container.blobs.values())
        if prefix is not None:
            blobs = [blob for blob in blobs if blob.name.startswith(prefix)]
        return sorted(blobs, key=lambda blob: blob.name.lower())

    def delete_blob(self, account_name: str, container_name: str, blob_name: str) -> None:
        container = self.get_container(account_name, container_name)
        if container.blobs.pop(blob_name, None) is None:
            raise AzureNotFound(f"Azure blob not found: {blob_name}")

    def create_queue(
        self, account_name: str, queue_name: str, *, metadata: dict[str, str] | None = None
    ) -> QueueState:
        account = self._get_data_account(account_name)
        queue = QueueState(name=queue_name, metadata=dict(metadata or {}))
        account.queues[queue_name] = queue
        return queue

    def get_queue(self, account_name: str, queue_name: str) -> QueueState:
        account = self._get_data_account(account_name)
        queue = account.queues.get(queue_name)
        if queue is None:
            raise AzureNotFound(f"Azure queue not found: {queue_name}")
        return queue

    def list_queues(self, account_name: str) -> list[QueueState]:
        account = self._get_data_account(account_name)
        return sorted(account.queues.values(), key=lambda queue: queue.name.lower())

    def delete_queue(self, account_name: str, queue_name: str) -> None:
        account = self._get_data_account(account_name)
        if account.queues.pop(queue_name, None) is None:
            raise AzureNotFound(f"Azure queue not found: {queue_name}")

    def send_message(self, account_name: str, queue_name: str, content: str) -> QueueMessageState:
        queue = self.get_queue(account_name, queue_name)
        message = QueueMessageState(message_id=str(uuid4()), content=content)
        queue.messages.append(message)
        return message

    def receive_messages(
        self, account_name: str, queue_name: str, *, num_messages: int = 1
    ) -> list[QueueMessageState]:
        queue = self.get_queue(account_name, queue_name)
        visible = [message for message in queue.messages if message.visible]
        received = visible[:num_messages]
        for message in received:
            message.visible = False
            message.dequeue_count += 1
            message.pop_receipt = str(uuid4())
        return received

    def delete_message(
        self, account_name: str, queue_name: str, message_id: str, pop_receipt: str
    ) -> None:
        queue = self.get_queue(account_name, queue_name)
        for index, message in enumerate(queue.messages):
            if message.message_id == message_id and message.pop_receipt == pop_receipt:
                del queue.messages[index]
                return
        raise AzureNotFound(f"Azure queue message not found: {message_id}")

    def _get_data_account(self, account_name: str) -> StorageAccountDataPlaneState:
        account = self.data_store.get_account(account_name)
        if account is None:
            raise AzureNotFound(f"Azure storage account not found: {account_name}")
        return account

    @staticmethod
    def _scope_resource_group(scope: AzureScope) -> str:
        if not scope.resource_group:
            raise AzureNotFound("Azure resource group is required for storage account operations")
        return scope.resource_group

    @staticmethod
    def _storage_account_id(
        subscription_id: str, resource_group: str, account_name: str
    ) -> AzureResourceId:
        return AzureResourceId.parse(
            f"/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/"
            f"Microsoft.Storage/storageAccounts/{account_name}"
        )
