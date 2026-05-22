import base64
import json

import pytest
from werkzeug.test import Client
from werkzeug.wrappers import Response

from localstack.gcp.services.iam import IamProvider, IamTokenRouter


@pytest.fixture
def client():
    return Client(IamTokenRouter(provider=IamProvider()), Response)


def test_mint_token_client_credentials(client):
    r = client.post(
        "/token",
        data={"grant_type": "client_credentials", "client_id": "svc@p1.iam.gserviceaccount.com", "scope": "https://www.googleapis.com/auth/cloud-platform"},
    )
    assert r.status_code == 200
    body = json.loads(r.data)
    assert body["token_type"] == "Bearer"
    assert body["access_token"].count(".") == 2  # JWT format
    header_b64, payload_b64, _ = body["access_token"].split(".")
    padded = payload_b64 + "=" * (-len(payload_b64) % 4)
    payload = json.loads(base64.urlsafe_b64decode(padded))
    assert payload["iss"] == "svc@p1.iam.gserviceaccount.com"


def test_mint_token_jwt_bearer_requires_assertion(client):
    r = client.post(
        "/token",
        data={"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer"},
    )
    assert r.status_code == 400


def test_mint_token_jwt_bearer(client):
    r = client.post(
        "/token",
        data={
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "assertion": "eyJ.eyJ.signed",
        },
    )
    assert r.status_code == 200


def test_unsupported_grant_type(client):
    r = client.post("/token", data={"grant_type": "password"})
    assert r.status_code == 400


def test_oauth2_v4_token(client):
    r = client.post("/oauth2/v4/token", data={"grant_type": "client_credentials"})
    assert r.status_code == 200


def test_create_service_account(client):
    r = client.post(
        "/v1/projects/p1/serviceAccounts",
        data=json.dumps({"accountId": "svc1", "serviceAccount": {"displayName": "Service 1"}}),
        content_type="application/json",
    )
    assert r.status_code == 200
    body = json.loads(r.data)
    assert body["email"] == "svc1@p1.iam.gserviceaccount.com"


def test_create_service_account_requires_account_id(client):
    r = client.post(
        "/v1/projects/p1/serviceAccounts",
        data=json.dumps({}),
        content_type="application/json",
    )
    assert r.status_code == 400


def test_list_service_accounts(client):
    for sid in ("a", "b"):
        client.post(
            "/v1/projects/p1/serviceAccounts",
            data=json.dumps({"accountId": sid}),
            content_type="application/json",
        )
    r = client.get("/v1/projects/p1/serviceAccounts")
    body = json.loads(r.data)
    assert len(body["accounts"]) == 2


def test_get_service_account(client):
    client.post(
        "/v1/projects/p1/serviceAccounts",
        data=json.dumps({"accountId": "svc1"}),
        content_type="application/json",
    )
    r = client.get("/v1/projects/p1/serviceAccounts/svc1@p1.iam.gserviceaccount.com")
    assert r.status_code == 200


def test_delete_service_account(client):
    client.post(
        "/v1/projects/p1/serviceAccounts",
        data=json.dumps({"accountId": "svc1"}),
        content_type="application/json",
    )
    r = client.delete("/v1/projects/p1/serviceAccounts/svc1@p1.iam.gserviceaccount.com")
    assert r.status_code == 200
    r = client.get("/v1/projects/p1/serviceAccounts/svc1@p1.iam.gserviceaccount.com")
    assert r.status_code == 404


def test_duplicate_service_account_conflict(client):
    client.post(
        "/v1/projects/p1/serviceAccounts",
        data=json.dumps({"accountId": "svc1"}),
        content_type="application/json",
    )
    r = client.post(
        "/v1/projects/p1/serviceAccounts",
        data=json.dumps({"accountId": "svc1"}),
        content_type="application/json",
    )
    assert r.status_code == 409
