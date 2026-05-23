from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from localstack.gcp.stores import CaseInsensitiveDict


@dataclass
class SqlDatabase:
    name: str  # database name
    instance: str = ""
    project: str = ""
    charset: str = "utf8"
    collation: str = "utf8_general_ci"

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": "sql#database",
            "name": self.name,
            "instance": self.instance,
            "project": self.project,
            "charset": self.charset,
            "collation": self.collation,
            "selfLink": f"https://sqladmin.googleapis.com/sql/v1beta4/projects/{self.project}/instances/{self.instance}/databases/{self.name}",
        }


@dataclass
class SqlUser:
    name: str
    instance: str = ""
    project: str = ""
    host: str = "%"
    password: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": "sql#user",
            "name": self.name,
            "instance": self.instance,
            "project": self.project,
            "host": self.host,
        }


@dataclass
class SqlInstance:
    name: str  # instance id
    project: str = ""
    region: str = "us-central1"
    database_version: str = "MYSQL_8_0"
    tier: str = "db-n1-standard-1"
    state: str = "RUNNABLE"
    ip_addresses: list[dict[str, str]] = field(
        default_factory=lambda: [{"type": "PRIMARY", "ipAddress": "127.0.0.1"}]
    )
    create_time: str = ""
    databases: CaseInsensitiveDict = field(default_factory=CaseInsensitiveDict)
    users: CaseInsensitiveDict = field(default_factory=CaseInsensitiveDict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": "sql#instance",
            "name": self.name,
            "project": self.project,
            "region": self.region,
            "databaseVersion": self.database_version,
            "state": self.state,
            "settings": {"tier": self.tier},
            "ipAddresses": self.ip_addresses,
            "createTime": self.create_time,
            "selfLink": f"https://sqladmin.googleapis.com/sql/v1beta4/projects/{self.project}/instances/{self.name}",
        }


class CloudSqlDataStore:
    def __init__(self) -> None:
        self.instances: CaseInsensitiveDict = CaseInsensitiveDict()
