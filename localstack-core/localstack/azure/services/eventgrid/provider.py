"""Microsoft.EventGrid provider — topics + event subscriptions + publish."""

from __future__ import annotations

from typing import Any

from localstack.azure.exceptions import AzureInvalidRequest, AzureNotFound
from localstack.azure.services.eventgrid.models import (
    EventGridEvent,
    EventGridSubscription,
    EventGridTopic,
)
from localstack.azure.stores import CaseInsensitiveDict

NAMESPACE = "Microsoft.EventGrid"


class MicrosoftEventGridProvider:
    def __init__(self) -> None:
        self._topics: CaseInsensitiveDict = CaseInsensitiveDict()

    def create_topic(self, name: str) -> EventGridTopic:
        if name in self._topics:
            return self._topics[name]
        topic = EventGridTopic(name=name)
        self._topics[name] = topic
        return topic

    def get_topic(self, name: str) -> EventGridTopic:
        topic = self._topics.get(name)
        if topic is None:
            raise AzureNotFound(f"Event Grid topic not found: {name}")
        return topic

    def list_topics(self) -> list[EventGridTopic]:
        return sorted(self._topics.values(), key=lambda t: t.name.lower())

    def delete_topic(self, name: str) -> None:
        if self._topics.pop(name, None) is None:
            raise AzureNotFound(f"Event Grid topic not found: {name}")

    def create_subscription(
        self, topic_name: str, subscription_name: str, *, endpoint: str
    ) -> EventGridSubscription:
        if not endpoint:
            raise AzureInvalidRequest("subscription endpoint is required")
        topic = self.get_topic(topic_name)
        if subscription_name in topic.subscriptions:
            sub = topic.subscriptions[subscription_name]
            sub.endpoint = endpoint
            return sub
        sub = EventGridSubscription(name=subscription_name, endpoint=endpoint)
        topic.subscriptions[subscription_name] = sub
        return sub

    def list_subscriptions(self, topic_name: str) -> list[EventGridSubscription]:
        topic = self.get_topic(topic_name)
        return sorted(topic.subscriptions.values(), key=lambda s: s.name.lower())

    def delete_subscription(self, topic_name: str, subscription_name: str) -> None:
        topic = self.get_topic(topic_name)
        if topic.subscriptions.pop(subscription_name, None) is None:
            raise AzureNotFound(f"Event Grid subscription not found: {subscription_name}")

    def publish_events(self, topic_name: str, events: list[dict[str, Any]]) -> list[EventGridEvent]:
        topic = self.get_topic(topic_name)
        materialized: list[EventGridEvent] = []
        for raw in events:
            for required in ("subject", "eventType", "data"):
                if required not in raw:
                    raise AzureInvalidRequest(f"event missing '{required}'")
            event = EventGridEvent(
                subject=raw["subject"],
                event_type=raw["eventType"],
                data=dict(raw["data"]),
                data_version=str(raw.get("dataVersion", "1.0")),
            )
            materialized.append(event)
        for sub in topic.subscriptions.values():
            sub.delivered.extend(materialized)
        return materialized

    def delivered_for(self, topic_name: str, subscription_name: str) -> list[EventGridEvent]:
        topic = self.get_topic(topic_name)
        sub = topic.subscriptions.get(subscription_name)
        if sub is None:
            raise AzureNotFound(f"Event Grid subscription not found: {subscription_name}")
        return list(sub.delivered)
