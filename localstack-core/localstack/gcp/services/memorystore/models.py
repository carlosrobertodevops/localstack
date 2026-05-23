from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from localstack.gcp.stores import CaseInsensitiveDict


@dataclass
class RedisInstance:
    name: str  # projects/{p}/locations/{l}/instances/{id}
    tier: str = "BASIC"  # BASIC | STANDARD_HA
    memory_size_gb: int = 1
    redis_version: str = "REDIS_7_0"
    state: str = "READY"
    host: str = "10.0.0.10"
    port: int = 6379
    authorized_network: str = ""
    auth_enabled: bool = False
    labels: dict[str, str] = field(default_factory=dict)
    create_time: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "tier": self.tier,
            "memorySizeGb": self.memory_size_gb,
            "redisVersion": self.redis_version,
            "state": self.state,
            "host": self.host,
            "port": self.port,
            "authorizedNetwork": self.authorized_network,
            "authEnabled": self.auth_enabled,
            "labels": self.labels,
            "createTime": self.create_time,
        }


class MemorystoreDataStore:
    def __init__(self) -> None:
        self.instances: CaseInsensitiveDict = CaseInsensitiveDict()
