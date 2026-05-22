import json

import pytest
from werkzeug.test import Client
from werkzeug.wrappers import Response

from localstack.azure.services.eventgrid import EventGridRouter, MicrosoftEventGridProvider


@pytest.fixture
def provider():
    return MicrosoftEventGridProvider()


@pytest.fixture
def client(provider):
    return Client(EventGridRouter(provider=provider), Response)


# -- provider --


def test_create_topic_idempotent(provider):
    a = provider.create_topic("t1")
    b = provider.create_topic("t1")
    assert a is b


def test_publish_fans_out_to_all_subscriptions(provider):
    provider.create_topic("t1")
    provider.create_subscription("t1", "a", endpoint="http://a")
    provider.create_subscription("t1", "b", endpoint="http://b")
    events = [{"subject": "s", "eventType": "e", "data": {"x": 1}}]
    provider.publish_events("t1", events)
    assert len(provider.delivered_for("t1", "a")) == 1
    assert len(provider.delivered_for("t1", "b")) == 1


def test_publish_validates_event_fields(provider):
    from localstack.azure.exceptions import AzureInvalidRequest

    provider.create_topic("t1")
    with pytest.raises(AzureInvalidRequest):
        provider.publish_events("t1", [{"subject": "s"}])


def test_publish_to_missing_topic_raises(provider):
    from localstack.azure.exceptions import AzureNotFound

    with pytest.raises(AzureNotFound):
        provider.publish_events("missing", [{"subject": "s", "eventType": "e", "data": {}}])


def test_subscription_requires_endpoint(provider):
    from localstack.azure.exceptions import AzureInvalidRequest

    provider.create_topic("t1")
    with pytest.raises(AzureInvalidRequest):
        provider.create_subscription("t1", "x", endpoint="")


# -- REST --


def test_rest_create_topic(client):
    assert client.put("/topics/t1").status_code == 201
    assert json.loads(client.get("/topics/t1").data)["name"] == "t1"


def test_rest_create_subscription_and_publish_flow(client):
    client.put("/topics/t1")
    sub_body = json.dumps(
        {"properties": {"destination": {"endpoint": "https://webhook/x"}}}
    )
    resp = client.put(
        "/topics/t1/eventSubscriptions/sub1",
        data=sub_body,
        content_type="application/json",
    )
    assert resp.status_code == 201

    publish = client.post(
        "/topics/t1:publish",
        data=json.dumps([{"subject": "s", "eventType": "e", "data": {"v": 1}}]),
        content_type="application/json",
    )
    assert publish.status_code == 200
    assert json.loads(publish.data)["count"] == 1

    delivered = client.get("/topics/t1/eventSubscriptions/sub1/_delivered")
    body = json.loads(delivered.data)
    assert len(body["value"]) == 1
    assert body["value"][0]["data"] == {"v": 1}


def test_rest_publish_to_missing_topic_returns_404(client):
    resp = client.post(
        "/topics/missing:publish",
        data=json.dumps([{"subject": "s", "eventType": "e", "data": {}}]),
        content_type="application/json",
    )
    assert resp.status_code == 404


def test_rest_invalid_publish_body_returns_400(client):
    client.put("/topics/t1")
    resp = client.post(
        "/topics/t1:publish",
        data=json.dumps({"not": "list"}),
        content_type="application/json",
    )
    assert resp.status_code == 400


def test_rest_list_subscriptions(client):
    client.put("/topics/t1")
    for n in ("a", "b"):
        client.put(
            f"/topics/t1/eventSubscriptions/{n}",
            data=json.dumps({"properties": {"destination": {"endpoint": "http://x"}}}),
            content_type="application/json",
        )
    resp = client.get("/topics/t1/eventSubscriptions")
    names = sorted(s["name"] for s in json.loads(resp.data)["value"])
    assert names == ["a", "b"]


def test_rest_delete_topic(client):
    client.put("/topics/t1")
    assert client.delete("/topics/t1").status_code == 204
    assert client.get("/topics/t1").status_code == 404


def test_rest_unknown_path(client):
    assert client.get("/anything").status_code == 404
