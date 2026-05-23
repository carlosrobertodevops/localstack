from xml.etree import ElementTree as ET

import pytest
from werkzeug.test import Client
from werkzeug.wrappers import Response

from localstack.azure.services.storage import MicrosoftStorageProvider, QueueRouter


@pytest.fixture
def provider():
    return MicrosoftStorageProvider()


@pytest.fixture
def client(provider):
    return Client(QueueRouter(provider=provider), Response)


def _enqueue_body(text: str) -> bytes:
    root = ET.Element("QueueMessage")
    ET.SubElement(root, "MessageText").text = text
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def test_put_queue_returns_201(client):
    resp = client.put("/acct1/q1")
    assert resp.status_code == 201
    assert resp.headers.get("x-ms-version")


def test_put_queue_idempotent_returns_204(client):
    client.put("/acct1/q1")
    resp = client.put("/acct1/q1")
    assert resp.status_code == 204


def test_delete_queue_returns_204(client):
    client.put("/acct1/q1")
    resp = client.delete("/acct1/q1")
    assert resp.status_code == 204


def test_delete_missing_queue_returns_404(client):
    resp = client.delete("/acct1/missing")
    assert resp.status_code == 404
    assert ET.fromstring(resp.data).findtext("Code") == "QueueNotFound"


def test_enqueue_message_returns_201_with_message_xml(client):
    client.put("/acct1/q1")
    resp = client.post(
        "/acct1/q1/messages",
        data=_enqueue_body("hello"),
        content_type="application/xml",
    )
    assert resp.status_code == 201
    root = ET.fromstring(resp.data)
    assert root.tag == "QueueMessagesList"
    msg = root.find("QueueMessage")
    assert msg is not None
    assert msg.findtext("MessageId")


def test_enqueue_into_missing_queue_returns_404(client):
    resp = client.post(
        "/acct1/missing/messages",
        data=_enqueue_body("hi"),
        content_type="application/xml",
    )
    assert resp.status_code == 404
    assert ET.fromstring(resp.data).findtext("Code") == "QueueNotFound"


def test_enqueue_invalid_xml_returns_400(client):
    client.put("/acct1/q1")
    resp = client.post(
        "/acct1/q1/messages",
        data=b"not xml",
        content_type="application/xml",
    )
    assert resp.status_code == 400


def test_dequeue_returns_visible_messages_with_pop_receipt(client):
    client.put("/acct1/q1")
    for txt in ("a", "b"):
        client.post(
            "/acct1/q1/messages", data=_enqueue_body(txt), content_type="application/xml"
        )
    resp = client.get("/acct1/q1/messages?numofmessages=2")
    assert resp.status_code == 200
    root = ET.fromstring(resp.data)
    msgs = root.findall("QueueMessage")
    assert len(msgs) == 2
    for m in msgs:
        assert m.findtext("MessageId")
        assert m.findtext("PopReceipt")
        assert m.findtext("MessageText") in ("a", "b")
        assert m.findtext("DequeueCount") == "1"


def test_dequeue_default_one_message(client):
    client.put("/acct1/q1")
    client.post("/acct1/q1/messages", data=_enqueue_body("only"), content_type="application/xml")
    client.post("/acct1/q1/messages", data=_enqueue_body("hidden"), content_type="application/xml")
    resp = client.get("/acct1/q1/messages")
    root = ET.fromstring(resp.data)
    assert len(root.findall("QueueMessage")) == 1


def test_delete_message_returns_204(client):
    client.put("/acct1/q1")
    client.post("/acct1/q1/messages", data=_enqueue_body("x"), content_type="application/xml")
    dq = ET.fromstring(client.get("/acct1/q1/messages").data).find("QueueMessage")
    mid = dq.findtext("MessageId")
    receipt = dq.findtext("PopReceipt")
    resp = client.delete(f"/acct1/q1/messages/{mid}?popreceipt={receipt}")
    assert resp.status_code == 204


def test_delete_message_missing_returns_404(client):
    client.put("/acct1/q1")
    resp = client.delete("/acct1/q1/messages/missing-id?popreceipt=abc")
    assert resp.status_code == 404
    assert ET.fromstring(resp.data).findtext("Code") == "MessageNotFound"


def test_delete_message_requires_popreceipt(client):
    client.put("/acct1/q1")
    resp = client.delete("/acct1/q1/messages/some-id")
    assert resp.status_code == 400
