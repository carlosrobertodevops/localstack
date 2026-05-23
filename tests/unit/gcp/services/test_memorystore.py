import json

import pytest
from werkzeug.test import Client
from werkzeug.wrappers import Response

from localstack.gcp.services.memorystore import MemorystoreProvider, MemorystoreRouter

P = "/v1/projects/p1/locations/us-central1/instances"


@pytest.fixture
def client():
    return Client(MemorystoreRouter(provider=MemorystoreProvider()), Response)


def _create(client, iid="i1", tier="BASIC", mem=1):
    return client.post(
        f"{P}?instanceId={iid}",
        data=json.dumps({"tier": tier, "memorySizeGb": mem}),
        content_type="application/json",
    )


def test_create_instance(client):
    r = _create(client)
    assert r.status_code == 200
    body = json.loads(r.data)
    assert body["tier"] == "BASIC"
    assert body["state"] == "READY"


def test_invalid_tier(client):
    r = _create(client, tier="BOGUS")
    assert r.status_code == 400


def test_invalid_memory(client):
    r = _create(client, mem=0)
    assert r.status_code == 400


def test_duplicate(client):
    _create(client)
    r = _create(client)
    assert r.status_code == 409


def test_list(client):
    _create(client, "a")
    _create(client, "b")
    r = client.get(P)
    assert len(json.loads(r.data)["instances"]) == 2


def test_get(client):
    _create(client)
    r = client.get(f"{P}/i1")
    assert r.status_code == 200


def test_get_missing(client):
    r = client.get(f"{P}/ghost")
    assert r.status_code == 404


def test_delete(client):
    _create(client)
    r = client.delete(f"{P}/i1")
    assert r.status_code == 200
    r = client.get(f"{P}/i1")
    assert r.status_code == 404


def test_patch_memory(client):
    _create(client)
    r = client.patch(
        f"{P}/i1",
        data=json.dumps({"memorySizeGb": 5}),
        content_type="application/json",
    )
    assert json.loads(r.data)["memorySizeGb"] == 5


def test_patch_labels(client):
    _create(client)
    r = client.patch(
        f"{P}/i1",
        data=json.dumps({"labels": {"env": "prod"}}),
        content_type="application/json",
    )
    assert json.loads(r.data)["labels"] == {"env": "prod"}


def test_failover_requires_ha(client):
    _create(client, tier="BASIC")
    r = client.post(f"{P}/i1:failover")
    assert r.status_code == 400


def test_failover_ha(client):
    _create(client, tier="STANDARD_HA", mem=5)
    r = client.post(f"{P}/i1:failover")
    assert r.status_code == 200


def test_unknown_action(client):
    _create(client)
    r = client.post(f"{P}/i1:explode")
    assert r.status_code == 400
