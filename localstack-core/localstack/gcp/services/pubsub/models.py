from __future__ import annotations

import base64
from collections import deque
from dataclasses import dataclass, field
from typing import Any

from localstack.gcp.stores import CaseInsensitiveDict


@dataclass
class PubsubMessage:
    message_id: str
    data: bytes = b""
    attributes: dict[str, str] = field(default_factory=dict)
    publish_time: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "messageId": self.message_id,
            "data": base64.b64encode(self.data).decode("ascii"),
            "attributes": self.attributes,
            "publishTime": self.publish_time,
        }


@dataclass
class Topic:
    name: str  # full: projects/{p}/topics/{t}
    labels: dict[str, str] = field(default_factory=dict)
    subscriptions: list[str] = field(default_factory=list)  # full subscription names

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "labels": self.labels}


@dataclass
class Subscription:
    name: str  # full: projects/{p}/subscriptions/{s}
    topic: str  # full topic name
    ack_deadline_seconds: int = 10
    labels: dict[str, str] = field(default_factory=dict)
    messages: deque = field(default_factory=deque)
    ack_seq: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "topic": self.topic,
            "ackDeadlineSeconds": self.ack_deadline_seconds,
            "labels": self.labels,
        }


class PubSubDataStore:
    def __init__(self) -> None:
        self.topics: CaseInsensitiveDict = CaseInsensitiveDict()
        self.subscriptions: CaseInsensitiveDict = CaseInsensitiveDict()
        self._msg_seq = 0

    def next_message_id(self) -> str:
        self._msg_seq += 1
        return str(self._msg_seq)
