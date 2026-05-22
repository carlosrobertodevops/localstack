import json

import pytest
from werkzeug.test import Client
from werkzeug.wrappers import Response

from localstack.azure.scope import AzureScope
from localstack.azure.services.keyvault import (
    KeyVaultSecretsRouter,
    MicrosoftKeyVaultProvider,
)


@pytest.fixture
def scope():
    return AzureScope.for_resource_group("sub-1", "rg-dev", location="eastus")


@pytest.fixture
def provider(scope):
    p = MicrosoftKeyVaultProvider()
    p.resource_manager.create_or_update_resource_group(scope, "rg-dev", {"location": "eastus"})
    p.create_vault(scope, "vault1", {"location": "eastus"})
    return p


@pytest.fixture
def client(provider):
    return Client(KeyVaultSecretsRouter(provider=provider), Response)


# -- provider direct --


def test_provider_set_and_get_secret(provider):
    v = provider.set_secret("vault1", "db-pwd", "s3cret!", content_type="text/plain")
    got = provider.get_secret("vault1", "db-pwd")
    assert got.value == "s3cret!"
    assert got.content_type == "text/plain"
    assert got.id == v.id


def test_provider_get_specific_version(provider):
    v1 = provider.set_secret("vault1", "key", "old")
    v2 = provider.set_secret("vault1", "key", "new")
    assert provider.get_secret("vault1", "key").value == "new"
    assert provider.get_secret("vault1", "key", version=v1.id).value == "old"
    assert provider.get_secret("vault1", "key", version=v2.id).value == "new"


def test_provider_rejects_empty_value(provider):
    from localstack.azure.exceptions import AzureInvalidRequest

    with pytest.raises(AzureInvalidRequest):
        provider.set_secret("vault1", "x", "")


def test_provider_list_secrets_sorted(provider):
    for n in ("c", "a", "b"):
        provider.set_secret("vault1", n, "v")
    names = [s.name for s in provider.list_secrets("vault1")]
    assert names == ["a", "b", "c"]


def test_provider_delete_secret(provider):
    from localstack.azure.exceptions import AzureNotFound

    provider.set_secret("vault1", "x", "v")
    provider.delete_secret("vault1", "x")
    with pytest.raises(AzureNotFound):
        provider.get_secret("vault1", "x")


# -- REST router --


def test_put_secret_returns_id_and_value(client):
    resp = client.put(
        "/vault1/secrets/db-pwd",
        data=json.dumps({"value": "abc", "contentType": "text/plain"}),
        content_type="application/json",
    )
    assert resp.status_code == 200
    body = json.loads(resp.data)
    assert body["value"] == "abc"
    assert body["contentType"] == "text/plain"
    assert body["id"].startswith("https://vault1.vault.azure.net/secrets/db-pwd/")


def test_put_secret_requires_value(client):
    resp = client.put(
        "/vault1/secrets/x",
        data=json.dumps({}),
        content_type="application/json",
    )
    assert resp.status_code == 400


def test_get_secret_returns_latest(client):
    client.put(
        "/vault1/secrets/x",
        data=json.dumps({"value": "v1"}),
        content_type="application/json",
    )
    client.put(
        "/vault1/secrets/x",
        data=json.dumps({"value": "v2"}),
        content_type="application/json",
    )
    resp = client.get("/vault1/secrets/x")
    assert json.loads(resp.data)["value"] == "v2"


def test_get_specific_version(client):
    first = client.put(
        "/vault1/secrets/x",
        data=json.dumps({"value": "old"}),
        content_type="application/json",
    )
    vid = json.loads(first.data)["id"].rsplit("/", 1)[-1]
    client.put(
        "/vault1/secrets/x",
        data=json.dumps({"value": "new"}),
        content_type="application/json",
    )
    resp = client.get(f"/vault1/secrets/x/{vid}")
    assert json.loads(resp.data)["value"] == "old"


def test_get_missing_secret_returns_404(client):
    resp = client.get("/vault1/secrets/missing")
    assert resp.status_code == 404


def test_list_secrets(client):
    for n in ("a", "b"):
        client.put(
            f"/vault1/secrets/{n}",
            data=json.dumps({"value": "v"}),
            content_type="application/json",
        )
    resp = client.get("/vault1/secrets")
    body = json.loads(resp.data)
    assert sorted(s["id"].rsplit("/", 1)[-1] for s in body["value"]) == ["a", "b"]


def test_delete_secret_returns_204(client):
    client.put(
        "/vault1/secrets/x",
        data=json.dumps({"value": "v"}),
        content_type="application/json",
    )
    resp = client.delete("/vault1/secrets/x")
    assert resp.status_code == 204
    assert client.get("/vault1/secrets/x").status_code == 404


def test_unknown_route_returns_404(client):
    assert client.get("/vault1/anything-else").status_code == 404
