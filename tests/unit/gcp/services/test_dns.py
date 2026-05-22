import json

import pytest
from werkzeug.test import Client
from werkzeug.wrappers import Response

from localstack.gcp.services.dns import DnsProvider, DnsRouter

P = "/dns/v1/projects/p1/managedZones"


@pytest.fixture
def client():
    return Client(DnsRouter(provider=DnsProvider()), Response)


def _create(client, zone="z1", dns="example.com."):
    return client.post(
        P,
        data=json.dumps({"name": zone, "dnsName": dns, "description": "test"}),
        content_type="application/json",
    )


def _change(client, zone="z1", additions=None, deletions=None):
    return client.post(
        f"{P}/{zone}/changes",
        data=json.dumps(
            {"additions": additions or [], "deletions": deletions or []}
        ),
        content_type="application/json",
    )


def test_create_zone(client):
    r = _create(client)
    assert r.status_code == 200
    body = json.loads(r.data)
    assert body["name"] == "z1"
    assert body["dnsName"] == "example.com."


def test_missing_dns_name_400(client):
    r = client.post(
        P,
        data=json.dumps({"name": "z1"}),
        content_type="application/json",
    )
    assert r.status_code == 400


def test_duplicate_zone(client):
    _create(client)
    r = _create(client)
    assert r.status_code == 409


def test_list_zones(client):
    _create(client, "a", "a.com.")
    _create(client, "b", "b.com.")
    r = client.get(P)
    assert len(json.loads(r.data)["managedZones"]) == 2


def test_get_zone(client):
    _create(client)
    r = client.get(f"{P}/z1")
    assert r.status_code == 200


def test_zone_includes_default_soa_ns(client):
    _create(client)
    r = client.get(f"{P}/z1/rrsets")
    types = {rs["type"] for rs in json.loads(r.data)["rrsets"]}
    assert {"SOA", "NS"} <= types


def test_add_a_record(client):
    _create(client)
    r = _change(
        client,
        additions=[
            {"name": "www.example.com.", "type": "A", "ttl": 300, "rrdatas": ["1.2.3.4"]}
        ],
    )
    assert r.status_code == 200
    body = json.loads(r.data)
    assert body["additions"][0]["rrdatas"] == ["1.2.3.4"]


def test_add_duplicate_record(client):
    _create(client)
    add = [{"name": "www.example.com.", "type": "A", "rrdatas": ["1.2.3.4"]}]
    _change(client, additions=add)
    r = _change(client, additions=add)
    assert r.status_code == 409


def test_delete_record(client):
    _create(client)
    add = [{"name": "www.example.com.", "type": "A", "rrdatas": ["1.2.3.4"]}]
    _change(client, additions=add)
    r = _change(
        client,
        deletions=[{"name": "www.example.com.", "type": "A"}],
    )
    assert r.status_code == 200
    r = client.get(f"{P}/z1/rrsets")
    types = {rs["type"] for rs in json.loads(r.data)["rrsets"]}
    assert "A" not in types


def test_delete_missing_record(client):
    _create(client)
    r = _change(
        client,
        deletions=[{"name": "ghost.example.com.", "type": "A"}],
    )
    assert r.status_code == 404


def test_delete_zone_with_records_blocked(client):
    _create(client)
    _change(
        client,
        additions=[
            {"name": "x.example.com.", "type": "A", "rrdatas": ["1.2.3.4"]}
        ],
    )
    r = client.delete(f"{P}/z1")
    assert r.status_code == 400


def test_delete_empty_zone(client):
    _create(client)
    r = client.delete(f"{P}/z1")
    assert r.status_code == 200
    r = client.get(f"{P}/z1")
    assert r.status_code == 404


def test_name_auto_dot(client):
    _create(client, dns="example.org")
    r = client.get(f"{P}/z1")
    assert json.loads(r.data)["dnsName"] == "example.org."


def test_missing_zone_404(client):
    r = client.get(f"{P}/ghost")
    assert r.status_code == 404
