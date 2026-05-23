from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4

from localstack.azure.stores import CaseInsensitiveDict


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class ServiceBusMessage:
    body: str
    message_id: str = field(default_factory=lambda: uuid4().hex)
    enqueued_time: datetime = field(default_factory=_now)
    delivery_count: int = 0
    properties: dict[str, str] = field(default_factory=dict)


@dataclass
class ServiceBusQueue:
    name: str
    messages: list[ServiceBusMessage] = field(default_factory=list)


@dataclass
class ServiceBusSubscription:
    name: str
    messages: list[ServiceBusMessage] = field(default_factory=list)


@dataclass
class ServiceBusTopic:
    name: str
    subscriptions: CaseInsensitiveDict = field(default_factory=CaseInsensitiveDict)


@dataclass
class ServiceBusNamespaceState:
    namespace: str
    queues: CaseInsensitiveDict = field(default_factory=CaseInsensitiveDict)
    topics: CaseInsensitiveDict = field(default_factory=CaseInsensitiveDict)


class ServiceBusDataPlaneStore:
    def __init__(self) -> None:
        self.namespaces: CaseInsensitiveDict = CaseInsensitiveDict()

    def ensure(self, namespace: str) -> ServiceBusNamespaceState:
        ns = self.namespaces.get(namespace)
        if ns is None:
            ns = ServiceBusNamespaceState(namespace=namespace)
            self.namespaces[namespace] = ns
        return ns

    def get(self, namespace: str) -> ServiceBusNamespaceState | None:
        return self.namespaces.get(namespace)
