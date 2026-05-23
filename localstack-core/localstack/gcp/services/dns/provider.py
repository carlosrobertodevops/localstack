from __future__ import annotations

import datetime
import uuid

from localstack.gcp.exceptions import GcpAlreadyExists, GcpInvalidRequest, GcpNotFound
from localstack.gcp.resource_manager import ResourceManagerProvider
from localstack.gcp.services.dns.models import (
    DnsDataStore,
    ManagedZone,
    ResourceRecordSet,
)
from localstack.gcp.stores import GcpStores


def _now() -> str:
    return datetime.datetime.now(datetime.UTC).isoformat()


def _ensure_dot(name: str) -> str:
    return name if name.endswith(".") else name + "."


class DnsProvider:
    def __init__(
        self,
        *,
        resource_manager: ResourceManagerProvider | None = None,
        stores: GcpStores | None = None,
    ) -> None:
        self.stores = stores or GcpStores()
        self.resource_manager = resource_manager or ResourceManagerProvider(stores=self.stores)
        self.data = DnsDataStore()

    def _key(self, project: str, zone: str) -> str:
        return f"{project}/{zone}"

    def create_zone(
        self,
        project: str,
        zone_name: str,
        *,
        dns_name: str,
        description: str = "",
        visibility: str = "public",
    ) -> ManagedZone:
        if not dns_name:
            raise GcpInvalidRequest("dnsName required")
        k = self._key(project, zone_name)
        if k in self.data.zones:
            raise GcpAlreadyExists(f"managed zone '{zone_name}' already exists in '{project}'")
        self.resource_manager.ensure_project(project)
        zone = ManagedZone(
            id=str(uuid.uuid4().int)[:16],
            name=zone_name,
            project=project,
            dns_name=_ensure_dot(dns_name),
            description=description,
            visibility=visibility,
            create_time=_now(),
        )
        soa = ResourceRecordSet(
            name=zone.dns_name,
            rrset_type="SOA",
            ttl=21600,
            rrdatas=[f"ns-cloud-a1.googledomains.com. cloud-dns-hostmaster.google.com. 1 21600 3600 259200 300"],
        )
        ns = ResourceRecordSet(
            name=zone.dns_name,
            rrset_type="NS",
            ttl=21600,
            rrdatas=list(zone.name_servers),
        )
        zone.rrsets[soa.key()] = soa
        zone.rrsets[ns.key()] = ns
        self.data.zones[k] = zone
        return zone

    def get_zone(self, project: str, zone_name: str) -> ManagedZone:
        k = self._key(project, zone_name)
        zone = self.data.zones.get(k)
        if zone is None:
            raise GcpNotFound(f"managed zone '{zone_name}' not found")
        return zone

    def list_zones(self, project: str) -> list[ManagedZone]:
        prefix = f"{project}/"
        return [z for k, z in self.data.zones.items() if k.startswith(prefix)]

    def delete_zone(self, project: str, zone_name: str) -> None:
        zone = self.get_zone(project, zone_name)
        # block delete if extra rrsets exist
        non_default = [
            rs for rs in zone.rrsets.values() if rs.rrset_type not in ("SOA", "NS")
        ]
        if non_default:
            raise GcpInvalidRequest(
                f"zone '{zone_name}' not empty (contains {len(non_default)} records)"
            )
        del self.data.zones[self._key(project, zone_name)]

    def list_rrsets(self, project: str, zone_name: str) -> list[ResourceRecordSet]:
        zone = self.get_zone(project, zone_name)
        return list(zone.rrsets.values())

    def apply_changes(
        self,
        project: str,
        zone_name: str,
        additions: list[dict],
        deletions: list[dict],
    ) -> dict:
        zone = self.get_zone(project, zone_name)
        # validate deletions first
        del_keys = []
        for d in deletions:
            name = _ensure_dot(d.get("name", ""))
            rtype = d.get("type", "A").upper()
            k = (name.lower(), rtype)
            if k not in zone.rrsets:
                raise GcpNotFound(f"rrset {name} {rtype} not found")
            del_keys.append(k)
        for k in del_keys:
            del zone.rrsets[k]
        added: list[ResourceRecordSet] = []
        for a in additions:
            name = _ensure_dot(a.get("name", ""))
            rtype = a.get("type", "A").upper()
            rrset = ResourceRecordSet(
                name=name,
                rrset_type=rtype,
                ttl=int(a.get("ttl", 300)),
                rrdatas=list(a.get("rrdatas") or []),
            )
            if rrset.key() in zone.rrsets:
                raise GcpAlreadyExists(f"rrset {name} {rtype} already exists")
            zone.rrsets[rrset.key()] = rrset
            added.append(rrset)
        return {
            "kind": "dns#change",
            "id": uuid.uuid4().hex[:12],
            "additions": [a.to_dict() for a in added],
            "deletions": [
                {"name": k[0], "type": k[1]} for k in del_keys
            ],
            "status": "done",
            "startTime": _now(),
        }
