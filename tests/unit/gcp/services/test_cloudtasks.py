import json

import pytest
from werkzeug.test import Client
from werkzeug.wrappers import Response

from localstack.gcp.services.cloudtasks import CloudTasksProvider, CloudTasksRouter

Q = "/v2/projects/p1/locations/us-central1/queues"


@pytest.fixture
def client():
    return Client(CloudTasksRouter(provider=CloudTasksProvider()), Response)


def _create_q(client, qid="q1"):
    return client.post(f"{Q}?queueId={qid}", data=b"{}", content_type="application/json")


def _create_task(client, qid="q1", body=None):
    body = body or {"task": {"httpRequest": {"url": "https://x", "httpMethod": "POST"}}}
    return client.post(
        f"{Q}/{qid}/tasks", data=json.dumps(body), content_type="application/json"
    )


def test_create_queue(client):
    r = _create_q(client)
    assert r.status_code == 200
    assert json.loads(r.data)["name"].endswith("/queues/q1")


def test_duplicate_queue(client):
    _create_q(client)
    r = _create_q(client)
    assert r.status_code == 409


def test_list_queues(client):
    _create_q(client, "a")
    _create_q(client, "b")
    r = client.get(Q)
    assert len(json.loads(r.data)["queues"]) == 2


def test_get_queue(client):
    _create_q(client)
    r = client.get(f"{Q}/q1")
    assert r.status_code == 200


def test_get_queue_missing(client):
    r = client.get(f"{Q}/ghost")
    assert r.status_code == 404


def test_delete_queue(client):
    _create_q(client)
    r = client.delete(f"{Q}/q1")
    assert r.status_code == 200
    r = client.get(f"{Q}/q1")
    assert r.status_code == 404


def test_pause_resume(client):
    _create_q(client)
    r = client.post(f"{Q}/q1:pause")
    assert json.loads(r.data)["state"] == "PAUSED"
    r = client.post(f"{Q}/q1:resume")
    assert json.loads(r.data)["state"] == "RUNNING"


def test_create_task_autogen_id(client):
    _create_q(client)
    r = _create_task(client)
    assert r.status_code == 200
    assert "/tasks/" in json.loads(r.data)["name"]


def test_create_task_named(client):
    _create_q(client)
    name = "projects/p1/locations/us-central1/queues/q1/tasks/t1"
    r = _create_task(client, body={"task": {"name": name, "httpRequest": {}}})
    assert json.loads(r.data)["name"] == name


def test_list_tasks(client):
    _create_q(client)
    _create_task(client)
    _create_task(client)
    r = client.get(f"{Q}/q1/tasks")
    assert len(json.loads(r.data)["tasks"]) == 2


def test_run_task_increments_dispatch(client):
    _create_q(client)
    name = "projects/p1/locations/us-central1/queues/q1/tasks/t1"
    _create_task(client, body={"task": {"name": name, "httpRequest": {}}})
    r = client.post(f"{Q}/q1/tasks/t1:run")
    body = json.loads(r.data)
    assert body["dispatchCount"] == 1
    assert body["state"] == "DISPATCHED"
    client.post(f"{Q}/q1/tasks/t1:run")
    r = client.get(f"{Q}/q1/tasks/t1")
    assert json.loads(r.data)["dispatchCount"] == 2


def test_delete_task(client):
    _create_q(client)
    name = "projects/p1/locations/us-central1/queues/q1/tasks/t1"
    _create_task(client, body={"task": {"name": name, "httpRequest": {}}})
    r = client.delete(f"{Q}/q1/tasks/t1")
    assert r.status_code == 200
    r = client.get(f"{Q}/q1/tasks/t1")
    assert r.status_code == 404


def test_create_task_in_missing_queue_404(client):
    r = _create_task(client, qid="ghost")
    assert r.status_code == 404
