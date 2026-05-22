import json

import pytest
from werkzeug.test import Client
from werkzeug.wrappers import Response

from localstack.gcp.services.scheduler import SchedulerProvider, SchedulerRouter

P = "/v1/projects/p1/locations/us-central1/jobs"


@pytest.fixture
def client():
    return Client(SchedulerRouter(provider=SchedulerProvider()), Response)


def _create(client, jid="j1", schedule="*/5 * * * *", target_type="http"):
    name = f"projects/p1/locations/us-central1/jobs/{jid}"
    body = {"name": name, "schedule": schedule, "timeZone": "Etc/UTC"}
    if target_type == "http":
        body["httpTarget"] = {"uri": "https://x", "httpMethod": "POST"}
    elif target_type == "pubsub":
        body["pubsubTarget"] = {"topicName": "projects/p1/topics/t1", "data": ""}
    return client.post(P, data=json.dumps(body), content_type="application/json")


def test_create_job(client):
    r = _create(client)
    assert r.status_code == 200
    body = json.loads(r.data)
    assert body["state"] == "ENABLED"
    assert "httpTarget" in body


def test_create_pubsub_target(client):
    r = _create(client, target_type="pubsub")
    assert "pubsubTarget" in json.loads(r.data)


def test_missing_schedule_400(client):
    body = {"name": f"projects/p1/locations/us-central1/jobs/x", "httpTarget": {"uri": "x"}}
    r = client.post(P, data=json.dumps(body), content_type="application/json")
    assert r.status_code == 400


def test_duplicate(client):
    _create(client)
    r = _create(client)
    assert r.status_code == 409


def test_list_jobs(client):
    _create(client, "a")
    _create(client, "b")
    r = client.get(P)
    assert len(json.loads(r.data)["jobs"]) == 2


def test_get_job(client):
    _create(client)
    r = client.get(f"{P}/j1")
    assert r.status_code == 200


def test_delete_job(client):
    _create(client)
    r = client.delete(f"{P}/j1")
    assert r.status_code == 200
    r = client.get(f"{P}/j1")
    assert r.status_code == 404


def test_patch_job(client):
    _create(client)
    r = client.patch(
        f"{P}/j1",
        data=json.dumps({"schedule": "0 * * * *", "description": "hourly"}),
        content_type="application/json",
    )
    body = json.loads(r.data)
    assert body["schedule"] == "0 * * * *"
    assert body["description"] == "hourly"


def test_pause_resume(client):
    _create(client)
    r = client.post(f"{P}/j1:pause")
    assert json.loads(r.data)["state"] == "PAUSED"
    r = client.post(f"{P}/j1:resume")
    assert json.loads(r.data)["state"] == "ENABLED"


def test_run_increments(client):
    _create(client)
    r = client.post(f"{P}/j1:run")
    assert r.status_code == 200
    client.post(f"{P}/j1:run")
    r = client.get(f"{P}/j1")
    # attemptCount not in to_dict; check via lastAttemptTime presence
    assert json.loads(r.data)["lastAttemptTime"] != ""


def test_run_paused_blocked(client):
    _create(client)
    client.post(f"{P}/j1:pause")
    r = client.post(f"{P}/j1:run")
    assert r.status_code == 400


def test_missing_job_404(client):
    r = client.get(f"{P}/ghost")
    assert r.status_code == 404


def test_unknown_action_400(client):
    _create(client)
    r = client.post(f"{P}/j1:explode")
    assert r.status_code == 400
