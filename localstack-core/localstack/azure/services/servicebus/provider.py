"""Microsoft.ServiceBus provider — ARM metadata + queue/topic/subscription data plane."""

from __future__ import annotations

from localstack.azure.defaults import create_default_registry
from localstack.azure.exceptions import AzureInvalidRequest, AzureNotFound
from localstack.azure.ids import AzureResourceId
from localstack.azure.resource_manager import ResourceManagerProvider
from localstack.azure.scope import AzureScope
from localstack.azure.services.servicebus.models import (
    ServiceBusDataPlaneStore,
    ServiceBusMessage,
    ServiceBusQueue,
    ServiceBusSubscription,
    ServiceBusTopic,
)
from localstack.azure.spec import AzureServiceSpec
from localstack.azure.stores import AzureGenericResource, AzureStores

NAMESPACE = "Microsoft.ServiceBus"
RESOURCE_TYPE = "namespaces"


class MicrosoftServiceBusProvider:
    def __init__(
        self,
        *,
        resource_manager: ResourceManagerProvider | None = None,
        stores: AzureStores | None = None,
        data_store: ServiceBusDataPlaneStore | None = None,
    ) -> None:
        self.stores = stores or AzureStores()
        self.resource_manager = resource_manager or ResourceManagerProvider(
            stores=self.stores, registry=create_default_registry()
        )
        self.resource_manager.registry.register(
            AzureServiceSpec(
                namespace=NAMESPACE,
                resource_type=RESOURCE_TYPE,
                api_versions=("2022-10-01-preview",),
                locations=("eastus", "westeurope", "westus2", "brazilsouth"),
            )
        )
        self.data_store = data_store or ServiceBusDataPlaneStore()

    # -- ARM metadata --

    def create_namespace(
        self, scope: AzureScope, name: str, parameters: dict
    ) -> AzureGenericResource:
        resource = self.resource_manager.create_or_update_resource(
            scope, self._namespace_id(scope, name), parameters
        )
        self.data_store.ensure(name)
        return resource

    # -- queues --

    def create_queue(self, namespace: str, queue: str) -> ServiceBusQueue:
        ns = self.data_store.ensure(namespace)
        if queue in ns.queues:
            return ns.queues[queue]
        q = ServiceBusQueue(name=queue)
        ns.queues[queue] = q
        return q

    def list_queues(self, namespace: str) -> list[ServiceBusQueue]:
        ns = self._require_namespace(namespace)
        return sorted(ns.queues.values(), key=lambda q: q.name.lower())

    def delete_queue(self, namespace: str, queue: str) -> None:
        ns = self._require_namespace(namespace)
        if ns.queues.pop(queue, None) is None:
            raise AzureNotFound(f"queue not found: {queue}")

    def send_queue_message(
        self, namespace: str, queue: str, body: str, *, properties: dict | None = None
    ) -> ServiceBusMessage:
        if body is None:
            raise AzureInvalidRequest("body required")
        ns = self._require_namespace(namespace)
        q = ns.queues.get(queue)
        if q is None:
            raise AzureNotFound(f"queue not found: {queue}")
        msg = ServiceBusMessage(body=body, properties=dict(properties or {}))
        q.messages.append(msg)
        return msg

    def receive_queue_message(self, namespace: str, queue: str) -> ServiceBusMessage | None:
        ns = self._require_namespace(namespace)
        q = ns.queues.get(queue)
        if q is None:
            raise AzureNotFound(f"queue not found: {queue}")
        if not q.messages:
            return None
        msg = q.messages.pop(0)
        msg.delivery_count += 1
        return msg

    # -- topics + subscriptions --

    def create_topic(self, namespace: str, topic: str) -> ServiceBusTopic:
        ns = self.data_store.ensure(namespace)
        if topic in ns.topics:
            return ns.topics[topic]
        t = ServiceBusTopic(name=topic)
        ns.topics[topic] = t
        return t

    def create_subscription(
        self, namespace: str, topic: str, subscription: str
    ) -> ServiceBusSubscription:
        t = self._require_topic(namespace, topic)
        if subscription in t.subscriptions:
            return t.subscriptions[subscription]
        sub = ServiceBusSubscription(name=subscription)
        t.subscriptions[subscription] = sub
        return sub

    def publish_topic_message(
        self, namespace: str, topic: str, body: str, *, properties: dict | None = None
    ) -> ServiceBusMessage:
        if body is None:
            raise AzureInvalidRequest("body required")
        t = self._require_topic(namespace, topic)
        msg = ServiceBusMessage(body=body, properties=dict(properties or {}))
        for sub in t.subscriptions.values():
            sub.messages.append(ServiceBusMessage(body=msg.body, properties=dict(msg.properties)))
        return msg

    def receive_subscription_message(
        self, namespace: str, topic: str, subscription: str
    ) -> ServiceBusMessage | None:
        t = self._require_topic(namespace, topic)
        sub = t.subscriptions.get(subscription)
        if sub is None:
            raise AzureNotFound(f"subscription not found: {subscription}")
        if not sub.messages:
            return None
        msg = sub.messages.pop(0)
        msg.delivery_count += 1
        return msg

    # -- helpers --

    def _require_namespace(self, namespace: str):
        ns = self.data_store.get(namespace)
        if ns is None:
            raise AzureNotFound(f"namespace not found: {namespace}")
        return ns

    def _require_topic(self, namespace: str, topic: str) -> ServiceBusTopic:
        ns = self._require_namespace(namespace)
        t = ns.topics.get(topic)
        if t is None:
            raise AzureNotFound(f"topic not found: {topic}")
        return t

    @staticmethod
    def _namespace_id(scope: AzureScope, name: str) -> AzureResourceId:
        if not scope.resource_group:
            raise AzureInvalidRequest("namespace operations require a resource group in scope")
        return AzureResourceId.parse(
            f"/subscriptions/{scope.subscription_id}/resourceGroups/{scope.resource_group}/"
            f"providers/{NAMESPACE}/{RESOURCE_TYPE}/{name}"
        )
