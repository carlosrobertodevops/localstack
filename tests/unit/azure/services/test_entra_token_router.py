import base64
import json

import pytest
from werkzeug.test import Client
from werkzeug.wrappers import Response

from localstack.azure.services.entra import EntraTokenRouter


@pytest.fixture
def client():
    return Client(EntraTokenRouter(), Response)


def _decode_jwt_payload(token: str) -> dict:
    _, payload, _ = token.split(".")
    # base64url decode with padding
    padded = payload + "=" * (-len(payload) % 4)
    return json.loads(base64.urlsafe_b64decode(padded))


def test_client_credentials_flow_returns_jwt(client):
    resp = client.post(
        "/contoso.onmicrosoft.com/oauth2/v2.0/token",
        data={
            "grant_type": "client_credentials",
            "client_id": "app-1",
            "client_secret": "secret",
            "scope": "https://management.azure.com/.default",
        },
    )
    assert resp.status_code == 200
    body = json.loads(resp.data)
    assert body["token_type"] == "Bearer"
    assert body["expires_in"] == 3600
    assert "access_token" in body
    claims = _decode_jwt_payload(body["access_token"])
    assert claims["aud"] == "https://management.azure.com/"
    assert claims["iss"].endswith("/contoso.onmicrosoft.com/v2.0")
    assert claims["appid"] == "app-1"


def test_password_grant_returns_jwt_with_upn(client):
    resp = client.post(
        "/tenant-1/oauth2/v2.0/token",
        data={
            "grant_type": "password",
            "username": "alice@tenant-1",
            "password": "x",
            "client_id": "cli",
            "scope": "user.read",
        },
    )
    assert resp.status_code == 200
    body = json.loads(resp.data)
    claims = _decode_jwt_payload(body["access_token"])
    assert claims["upn"] == "alice@tenant-1"
    assert claims["appid"] == "cli"


def test_missing_grant_type_returns_400(client):
    resp = client.post(
        "/tenant-1/oauth2/v2.0/token",
        data={"client_id": "x"},
    )
    assert resp.status_code == 400
    body = json.loads(resp.data)
    assert body["error"] == "invalid_request"


def test_unsupported_grant_type_returns_400(client):
    resp = client.post(
        "/tenant-1/oauth2/v2.0/token",
        data={"grant_type": "device_code", "client_id": "x"},
    )
    assert resp.status_code == 400
    assert json.loads(resp.data)["error"] == "unsupported_grant_type"


def test_unknown_route_returns_404(client):
    assert client.get("/anything").status_code == 404


def test_get_method_not_allowed(client):
    assert client.get("/tenant-1/oauth2/v2.0/token").status_code == 405
