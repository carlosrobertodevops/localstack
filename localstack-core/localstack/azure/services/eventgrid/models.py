from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from localstack.azure.stores import CaseInsensitiveDict


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class EventGridEvent:
    subject: str
    event_type: str
    data: dict[str, Any]
    id: str = field(default_factory=lambda: uuid4().hex)
    event_time: datetime = field(default_factory=_now)
    data_version: str = "1.0"


@dataclass
class EventGridSubscription:
    name: str
    endpoint: str  # webhook URL
    delivered: list[EventGridEvent] = field(default_factory=list)


@dataclass
class EventGridTopic:
    name: str
    subscriptions: CaseInsensitiveDict = field(default_factory=CaseInsensitiveDict)
