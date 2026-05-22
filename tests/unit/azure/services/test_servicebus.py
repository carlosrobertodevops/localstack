import pytest
from werkzeug.test import Client
from werkzeug.wrappers import Response

from localstack.azure.scope import AzureScope
from localstack.azure.services.servicebus import (
    MicrosoftServiceBusProvider,
    ServiceBusRouter,
)


@pytest.fixture
def scope():
    return AzureScope.for_resource_group("sub-1", "rg-dev", location="eastus")


@pytest.fixture
def provider(scope):
    p = MicrosoftServiceBusProvider()
    p.resource_manager.create_or_update_resource_group(scope, "rg-dev", {"location": "eastus"})
    p.create_namespace(scope, "ns1", {"location": "eastus"})
    return p


@pytest.fixture
def client(provider):
    return Client(ServiceBusRouter(provider=provider), Response)


# -- provider direct --


def test_queue_send_and_receive(provider):
    provider.create_queue("ns1", "q1")
    m = provider.send_queue_message("ns1", "q1", "hello")
    assert m.body == "hello"
    got = provider.receive_queue_message("ns1", "q1")
    assert got.body == "hello"
    assert got.delivery_count == 1
    assert provider.receive_queue_message("ns1", "q1") is None


def test_topic_subscriptions_each_get_message(provider):
    provider.create_topic("ns1", "t1")
    provider.create_subscription("ns1", "t1", "a")
    provider.create_subscription("ns1", "t1", "b")
    provider.publish_topic_message("ns1", "t1", "boom")
    assert provider.receive_subscription_message("ns1", "t1", "a").body == "boom"
    assert provider.receive_subscription_message("ns1", "t1", "b").body == "boom"


def test_missing_queue_raises(provider):
    from localstack.azure.exceptions import AzureNotFound

    with pytest.raises(AzureNotFound):
        provider.send_queue_message("ns1", "missing-q", "x")


# -- REST router --


def test_put_queue_returns_201(client):
    assert client.put("/ns1/queues/q1").status_code == 201


def test_send_and_receive_via_rest(client):
    client.put("/ns1/queues/q1")
    send = client.post("/ns1/queues/q1/messages", data="hi", content_type="text/plain")
    assert send.status_code == 201
    recv = client.get("/ns1/queues/q1/messages")
    assert recv.status_code == 200
    import json

    assert json.loads(recv.data)["body"] == "hi"
    empty = client.get("/ns1/queues/q1/messages")
    assert empty.status_code == 204


def test_put_topic_and_subscription(client):
    assert client.put("/ns1/topics/t1").status_code == 201
    assert client.put("/ns1/topics/t1/subscriptions/sub1").status_code == 201


def test_publish_topic_fanout_via_rest(client):
    client.put("/ns1/topics/t1")
    client.put("/ns1/topics/t1/subscriptions/a")
    client.put("/ns1/topics/t1/subscriptions/b")
    client.post("/ns1/topics/t1/messages", data="x", content_type="text/plain")
    import json

    for sub in ("a", "b"):
        resp = client.get(f"/ns1/topics/t1/subscriptions/{sub}/messages")
        assert resp.status_code == 200
        assert json.loads(resp.data)["body"] == "x"


def test_delete_missing_queue_returns_404(client):
    resp = client.delete("/ns1/queues/missing")
    assert resp.status_code == 404


def test_unknown_route_returns_404(client):
    assert client.get("/ns1/random").status_code == 404
