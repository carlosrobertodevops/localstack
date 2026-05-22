import json

import pytest
from werkzeug.test import Client
from werkzeug.wrappers import Response

from localstack.gcp.services.cloudrun import CloudRunProvider, CloudRunRouter

S = "/v2/projects/p1/locations/us-central1/services"


@pytest.fixture
def client():
    return Client(CloudRunRouter(provider=CloudRunProvider()), Response)


def _create(client, sid="s1", image="img:1", env=None):
    body = {
        "template": {
            "containers": [
                {
                    "image": image,
                    "env": [{"name": k, "value": v} for k, v in (env or {}).items()],
                }
            ]
        }
    }
    return client.post(
        f"{S}?serviceId={sid}", data=json.dumps(body), content_type="application/json"
    )


def test_create_service(client):
    r = _create(client)
    assert r.status_code == 200
    body = json.loads(r.data)
    assert body["generation"] == 1
    assert body["latestReadyRevision"].endswith("/revisions/s1-00001")
    assert body["uri"].startswith("https://s1-")


def test_duplicate_service(client):
    _create(client)
    r = _create(client)
    assert r.status_code == 409


def test_list_services(client):
    _create(client, "a")
    _create(client, "b")
    r = client.get(S)
    assert len(json.loads(r.data)["services"]) == 2


def test_get_service(client):
    _create(client)
    r = client.get(f"{S}/s1")
    assert r.status_code == 200


def test_get_service_missing(client):
    r = client.get(f"{S}/ghost")
    assert r.status_code == 404


def test_delete_service(client):
    _create(client)
    r = client.delete(f"{S}/s1")
    assert r.status_code == 200
    r = client.get(f"{S}/s1")
    assert r.status_code == 404


def test_update_creates_new_revision(client):
    _create(client, image="img:1")
    r = client.patch(
        f"{S}/s1",
        data=json.dumps(
            {"template": {"containers": [{"image": "img:2", "env": []}]}}
        ),
        content_type="application/json",
    )
    body = json.loads(r.data)
    assert body["generation"] == 2
    assert body["latestReadyRevision"].endswith("/revisions/s1-00002")
    assert body["template"]["containers"][0]["image"] == "img:2"


def test_list_revisions(client):
    _create(client)
    client.patch(
        f"{S}/s1",
        data=json.dumps({"template": {"containers": [{"image": "img:2", "env": []}]}}),
        content_type="application/json",
    )
    r = client.get(f"{S}/s1/revisions")
    assert len(json.loads(r.data)["revisions"]) == 2


def test_get_revision(client):
    _create(client)
    r = client.get(f"{S}/s1/revisions/s1-00001")
    assert r.status_code == 200


def test_update_traffic(client):
    _create(client)
    client.patch(
        f"{S}/s1",
        data=json.dumps({"template": {"containers": [{"image": "img:2", "env": []}]}}),
        content_type="application/json",
    )
    rev1 = "projects/p1/locations/us-central1/services/s1/revisions/s1-00001"
    rev2 = "projects/p1/locations/us-central1/services/s1/revisions/s1-00002"
    r = client.post(
        f"{S}/s1:updateTraffic",
        data=json.dumps(
            {"traffic": [{"percent": 30, "revision": rev1}, {"percent": 70, "revision": rev2}]}
        ),
        content_type="application/json",
    )
    assert r.status_code == 200
    body = json.loads(r.data)
    assert sum(t["percent"] for t in body["traffic"]) == 100


def test_update_traffic_bad_percent(client):
    _create(client)
    rev1 = "projects/p1/locations/us-central1/services/s1/revisions/s1-00001"
    r = client.post(
        f"{S}/s1:updateTraffic",
        data=json.dumps({"traffic": [{"percent": 50, "revision": rev1}]}),
        content_type="application/json",
    )
    assert r.status_code == 400


def test_env_preserved(client):
    _create(client, env={"FOO": "bar"})
    r = client.get(f"{S}/s1")
    env = json.loads(r.data)["template"]["containers"][0]["env"]
    assert {"name": "FOO", "value": "bar"} in env


def test_delete_latest_revision_blocked(client):
    _create(client)
    r = client.delete(f"{S}/s1/revisions/s1-00001")
    assert r.status_code == 400
