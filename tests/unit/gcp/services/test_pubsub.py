import base64
import json

import pytest
from werkzeug.test import Client
from werkzeug.wrappers import Response

from localstack.gcp.services.pubsub import PubSubProvider, PubSubRouter


@pytest.fixture
def client():
    return Client(PubSubRouter(provider=PubSubProvider()), Response)


def test_create_topic(client):
    r = client.put("/v1/projects/p1/topics/t1")
    assert r.status_code == 200
    body = json.loads(r.data)
    assert body["name"] == "projects/p1/topics/t1"


def test_list_topics(client):
    client.put("/v1/projects/p1/topics/t1")
    client.put("/v1/projects/p1/topics/t2")
    r = client.get("/v1/projects/p1/topics")
    topics = json.loads(r.data)["topics"]
    assert {t["name"] for t in topics} == {
        "projects/p1/topics/t1",
        "projects/p1/topics/t2",
    }


def test_delete_topic(client):
    client.put("/v1/projects/p1/topics/t1")
    r = client.delete("/v1/projects/p1/topics/t1")
    assert r.status_code == 200
    r = client.get("/v1/projects/p1/topics/t1")
    assert r.status_code == 404


def test_create_subscription_requires_topic(client):
    r = client.put(
        "/v1/projects/p1/subscriptions/s1",
        data=json.dumps({"topic": "projects/p1/topics/ghost"}),
        content_type="application/json",
    )
    assert r.status_code == 404


def test_publish_and_pull(client):
    client.put("/v1/projects/p1/topics/t1")
    client.put(
        "/v1/projects/p1/subscriptions/s1",
        data=json.dumps({"topic": "projects/p1/topics/t1"}),
        content_type="application/json",
    )
    payload = base64.b64encode(b"hello").decode("ascii")
    r = client.post(
        "/v1/projects/p1/topics/t1:publish",
        data=json.dumps({"messages": [{"data": payload}]}),
        content_type="application/json",
    )
    assert r.status_code == 200
    assert len(json.loads(r.data)["messageIds"]) == 1

    r = client.post(
        "/v1/projects/p1/subscriptions/s1:pull",
        data=json.dumps({"maxMessages": 10}),
        content_type="application/json",
    )
    received = json.loads(r.data)["receivedMessages"]
    assert len(received) == 1
    assert base64.b64decode(received[0]["message"]["data"]) == b"hello"


def test_pull_empty(client):
    client.put("/v1/projects/p1/topics/t1")
    client.put(
        "/v1/projects/p1/subscriptions/s1",
        data=json.dumps({"topic": "projects/p1/topics/t1"}),
        content_type="application/json",
    )
    r = client.post(
        "/v1/projects/p1/subscriptions/s1:pull",
        data=json.dumps({"maxMessages": 5}),
        content_type="application/json",
    )
    assert json.loads(r.data)["receivedMessages"] == []


def test_publish_fanout_multiple_subs(client):
    client.put("/v1/projects/p1/topics/t1")
    for s in ("s1", "s2"):
        client.put(
            f"/v1/projects/p1/subscriptions/{s}",
            data=json.dumps({"topic": "projects/p1/topics/t1"}),
            content_type="application/json",
        )
    client.post(
        "/v1/projects/p1/topics/t1:publish",
        data=json.dumps({"messages": [{"data": base64.b64encode(b"x").decode()}]}),
        content_type="application/json",
    )
    for s in ("s1", "s2"):
        r = client.post(
            f"/v1/projects/p1/subscriptions/{s}:pull",
            data=json.dumps({"maxMessages": 5}),
            content_type="application/json",
        )
        assert len(json.loads(r.data)["receivedMessages"]) == 1


def test_ack(client):
    client.put("/v1/projects/p1/topics/t1")
    client.put(
        "/v1/projects/p1/subscriptions/s1",
        data=json.dumps({"topic": "projects/p1/topics/t1"}),
        content_type="application/json",
    )
    r = client.post(
        "/v1/projects/p1/subscriptions/s1:acknowledge",
        data=json.dumps({"ackIds": ["a1"]}),
        content_type="application/json",
    )
    assert r.status_code == 200


def test_list_subscriptions(client):
    client.put("/v1/projects/p1/topics/t1")
    for s in ("s1", "s2"):
        client.put(
            f"/v1/projects/p1/subscriptions/{s}",
            data=json.dumps({"topic": "projects/p1/topics/t1"}),
            content_type="application/json",
        )
    r = client.get("/v1/projects/p1/subscriptions")
    subs = json.loads(r.data)["subscriptions"]
    assert len(subs) == 2


def test_delete_topic_cascades_subscriptions(client):
    client.put("/v1/projects/p1/topics/t1")
    client.put(
        "/v1/projects/p1/subscriptions/s1",
        data=json.dumps({"topic": "projects/p1/topics/t1"}),
        content_type="application/json",
    )
    client.delete("/v1/projects/p1/topics/t1")
    r = client.get("/v1/projects/p1/subscriptions/s1")
    assert r.status_code == 404
