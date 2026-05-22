import base64
import json

import pytest
from werkzeug.test import Client
from werkzeug.wrappers import Response

from localstack.gcp.services.kms import KmsProvider, KmsRouter

P = "/v1/projects/p1/locations/us-central1/keyRings"


@pytest.fixture
def client():
    return Client(KmsRouter(provider=KmsProvider()), Response)


def _create_kr(client, kr="kr1"):
    return client.post(f"{P}?keyRingId={kr}", data=b"{}", content_type="application/json")


def _create_ck(client, kr="kr1", ck="ck1"):
    return client.post(
        f"{P}/{kr}/cryptoKeys?cryptoKeyId={ck}", data=b"{}", content_type="application/json"
    )


def test_create_keyring(client):
    r = _create_kr(client)
    assert r.status_code == 200
    assert json.loads(r.data)["name"].endswith("/keyRings/kr1")


def test_duplicate_keyring(client):
    _create_kr(client)
    r = _create_kr(client)
    assert r.status_code == 409


def test_list_keyrings(client):
    _create_kr(client, "kr1")
    _create_kr(client, "kr2")
    r = client.get(P)
    assert len(json.loads(r.data)["keyRings"]) == 2


def test_get_keyring(client):
    _create_kr(client)
    r = client.get(f"{P}/kr1")
    assert r.status_code == 200


def test_keyring_missing(client):
    r = client.get(f"{P}/ghost")
    assert r.status_code == 404


def test_create_cryptokey_auto_v1(client):
    _create_kr(client)
    r = _create_ck(client)
    assert r.status_code == 200
    body = json.loads(r.data)
    assert body["primary"]["name"].endswith("/cryptoKeyVersions/1")


def test_duplicate_cryptokey(client):
    _create_kr(client)
    _create_ck(client)
    r = _create_ck(client)
    assert r.status_code == 409


def test_list_cryptokeys(client):
    _create_kr(client)
    _create_ck(client, ck="a")
    _create_ck(client, ck="b")
    r = client.get(f"{P}/kr1/cryptoKeys")
    assert len(json.loads(r.data)["cryptoKeys"]) == 2


def test_encrypt_decrypt_roundtrip(client):
    _create_kr(client)
    _create_ck(client)
    payload = b"hello world"
    data = base64.b64encode(payload).decode("ascii")
    r = client.post(
        f"{P}/kr1/cryptoKeys/ck1:encrypt",
        data=json.dumps({"plaintext": data}),
        content_type="application/json",
    )
    assert r.status_code == 200
    ct = json.loads(r.data)["ciphertext"]
    r = client.post(
        f"{P}/kr1/cryptoKeys/ck1:decrypt",
        data=json.dumps({"ciphertext": ct}),
        content_type="application/json",
    )
    assert base64.b64decode(json.loads(r.data)["plaintext"]) == payload


def test_encrypt_uses_random_nonce(client):
    _create_kr(client)
    _create_ck(client)
    data = base64.b64encode(b"same").decode("ascii")

    def enc():
        r = client.post(
            f"{P}/kr1/cryptoKeys/ck1:encrypt",
            data=json.dumps({"plaintext": data}),
            content_type="application/json",
        )
        return json.loads(r.data)["ciphertext"]

    assert enc() != enc()


def test_create_cryptokey_version(client):
    _create_kr(client)
    _create_ck(client)
    r = client.post(
        f"{P}/kr1/cryptoKeys/ck1/cryptoKeyVersions",
        data=b"{}",
        content_type="application/json",
    )
    assert r.status_code == 200
    assert json.loads(r.data)["name"].endswith("/cryptoKeyVersions/2")
    r = client.get(f"{P}/kr1/cryptoKeys/ck1")
    assert json.loads(r.data)["primary"]["name"].endswith("/cryptoKeyVersions/2")


def test_get_cryptokey_missing(client):
    _create_kr(client)
    r = client.get(f"{P}/kr1/cryptoKeys/ghost")
    assert r.status_code == 404


def test_encrypt_on_missing_keyring_404(client):
    r = client.post(
        f"{P}/kr1/cryptoKeys/ck1:encrypt",
        data=json.dumps({"plaintext": ""}),
        content_type="application/json",
    )
    assert r.status_code == 404
