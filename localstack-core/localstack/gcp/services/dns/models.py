from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from localstack.gcp.stores import CaseInsensitiveDict


@dataclass
class ResourceRecordSet:
    name: str  # FQDN with trailing dot
    rrset_type: str = "A"
    ttl: int = 300
    rrdatas: list[str] = field(default_factory=list)

    def key(self) -> tuple[str, str]:
        return (self.name.lower(), self.rrset_type.upper())

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": "dns#resourceRecordSet",
            "name": self.name,
            "type": self.rrset_type,
            "ttl": self.ttl,
            "rrdatas": list(self.rrdatas),
        }


@dataclass
class ManagedZone:
    id: str
    name: str
    project: str = ""
    dns_name: str = ""  # FQDN with trailing dot
    description: str = ""
    visibility: str = "public"
    name_servers: list[str] = field(
        default_factory=lambda: [
            "ns-cloud-a1.googledomains.com.",
            "ns-cloud-a2.googledomains.com.",
        ]
    )
    create_time: str = ""
    rrsets: dict[tuple[str, str], ResourceRecordSet] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": "dns#managedZone",
            "id": self.id,
            "name": self.name,
            "dnsName": self.dns_name,
            "description": self.description,
            "visibility": self.visibility,
            "nameServers": list(self.name_servers),
            "creationTime": self.create_time,
        }


class DnsDataStore:
    def __init__(self) -> None:
        self.zones: CaseInsensitiveDict = CaseInsensitiveDict()
