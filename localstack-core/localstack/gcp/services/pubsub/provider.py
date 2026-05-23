from __future__ import annotations

import base64
import datetime
from typing import Any

from localstack.gcp.exceptions import GcpAlreadyExists, GcpInvalidRequest, GcpNotFound
from localstack.gcp.resource_manager import ResourceManagerProvider
from localstack.gcp.services.pubsub.models import (
    PubSubDataStore,
    PubsubMessage,
    Subscription,
    Topic,
)
from localstack.gcp.stores import GcpStores


def _now_iso() -> str:
    return datetime.datetime.now(datetime.UTC).isoformat()


class PubSubProvider:
    def __init__(
        self,
        *,
        resource_manager: ResourceManagerProvider | None = None,
        stores: GcpStores | None = None,
    ) -> None:
        self.stores = stores or GcpStores()
        self.resource_manager = resource_manager or ResourceManagerProvider(stores=self.stores)
        self.data = PubSubDataStore()

    # topics
    def create_topic(self, full_name: str, *, labels: dict[str, str] | None = None) -> Topic:
        if not full_name.startswith("projects/") or "/topics/" not in full_name:
            raise GcpInvalidRequest(f"invalid topic name: {full_name}")
        if full_name in self.data.topics:
            raise GcpAlreadyExists(f"topic '{full_name}' already exists")
        project_id = full_name.split("/")[1]
        self.resource_manager.ensure_project(project_id)
        topic = Topic(name=full_name, labels=dict(labels or {}))
        self.data.topics[full_name] = topic
        return topic

    def get_topic(self, full_name: str) -> Topic:
        t = self.data.topics.get(full_name)
        if t is None:
            raise GcpNotFound(f"topic '{full_name}' not found")
        return t

    def list_topics(self, project_id: str) -> list[Topic]:
        prefix = f"projects/{project_id}/topics/"
        return [t for t in self.data.topics.values() if t.name.startswith(prefix)]

    def delete_topic(self, full_name: str) -> None:
        if full_name not in self.data.topics:
            raise GcpNotFound(f"topic '{full_name}' not found")
        topic = self.data.topics[full_name]
        for sub_name in topic.subscriptions:
            self.data.subscriptions.pop(sub_name, None)
        del self.data.topics[full_name]

    # subscriptions
    def create_subscription(self, full_name: str, topic_name: str, *, ack_deadline: int = 10, labels: dict[str, str] | None = None) -> Subscription:
        if not full_name.startswith("projects/") or "/subscriptions/" not in full_name:
            raise GcpInvalidRequest(f"invalid subscription name: {full_name}")
        if full_name in self.data.subscriptions:
            raise GcpAlreadyExists(f"subscription '{full_name}' already exists")
        topic = self.get_topic(topic_name)
        sub = Subscription(name=full_name, topic=topic_name, ack_deadline_seconds=ack_deadline, labels=dict(labels or {}))
        self.data.subscriptions[full_name] = sub
        topic.subscriptions.append(full_name)
        return sub

    def get_subscription(self, full_name: str) -> Subscription:
        sub = self.data.subscriptions.get(full_name)
        if sub is None:
            raise GcpNotFound(f"subscription '{full_name}' not found")
        return sub

    def list_subscriptions(self, project_id: str) -> list[Subscription]:
        prefix = f"projects/{project_id}/subscriptions/"
        return [s for s in self.data.subscriptions.values() if s.name.startswith(prefix)]

    def delete_subscription(self, full_name: str) -> None:
        if full_name not in self.data.subscriptions:
            raise GcpNotFound(f"subscription '{full_name}' not found")
        sub = self.data.subscriptions[full_name]
        if sub.topic in self.data.topics:
            topic = self.data.topics[sub.topic]
            if full_name in topic.subscriptions:
                topic.subscriptions.remove(full_name)
        del self.data.subscriptions[full_name]

    # publish / pull / ack
    def publish(self, topic_name: str, messages: list[dict[str, Any]]) -> list[str]:
        topic = self.get_topic(topic_name)
        ids: list[str] = []
        for m in messages:
            raw = m.get("data", "")
            data = base64.b64decode(raw) if raw else b""
            msg_id = self.data.next_message_id()
            msg = PubsubMessage(
                message_id=msg_id,
                data=data,
                attributes=dict(m.get("attributes") or {}),
                publish_time=_now_iso(),
            )
            for sub_name in topic.subscriptions:
                self.data.subscriptions[sub_name].messages.append(msg)
            ids.append(msg_id)
        return ids

    def pull(self, subscription_name: str, max_messages: int = 10) -> list[dict[str, Any]]:
        sub = self.get_subscription(subscription_name)
        out: list[dict[str, Any]] = []
        while sub.messages and len(out) < max_messages:
            msg = sub.messages.popleft()
            sub.ack_seq += 1
            ack_id = f"ack-{sub.ack_seq}"
            out.append({"ackId": ack_id, "message": msg.to_dict()})
        return out

    def acknowledge(self, subscription_name: str, ack_ids: list[str]) -> None:
        # in-memory model already pops on pull; ack is a no-op besides validation
        self.get_subscription(subscription_name)
