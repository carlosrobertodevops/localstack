import json

import pytest
from werkzeug.test import Client
from werkzeug.wrappers import Response

from localstack.azure.scope import AzureScope
from localstack.azure.services.functions import (
    FunctionsRegistry,
    FunctionsHttpRouter,
    MicrosoftWebProvider,
)


@pytest.fixture
def scope():
    return AzureScope.for_resource_group("sub-1", "rg-dev", location="eastus")


@pytest.fixture
def provider():
    return MicrosoftWebProvider()


@pytest.fixture
def registry():
    return FunctionsRegistry()


@pytest.fixture
def client(provider, registry):
    return Client(FunctionsHttpRouter(provider=provider, registry=registry), Response)


def _register_app(provider, scope, name="app1"):
    provider.resource_manager.create_or_update_resource_group(
        scope, scope.resource_group, {"location": "eastus"}
    )
    provider.create_function_app(scope, name, {"location": "eastus"})


def test_invoke_registered_function(provider, scope, registry, client):
    _register_app(provider, scope)
    registry.register("app1", "hello", lambda req: {"body": "hi"})
    resp = client.get("/app1/api/hello")
    assert resp.status_code == 200
    assert resp.data == b"hi"


def test_invoke_returns_status_and_headers(provider, scope, registry, client):
    _register_app(provider, scope)
    registry.register(
        "app1",
        "json",
        lambda req: {
            "status": 201,
            "headers": {"Content-Type": "application/json", "X-Custom": "y"},
            "body": json.dumps({"ok": True}),
        },
    )
    resp = client.post("/app1/api/json", data=b"input")
    assert resp.status_code == 201
    assert resp.headers["Content-Type"] == "application/json"
    assert resp.headers["X-Custom"] == "y"
    assert json.loads(resp.data) == {"ok": True}


def test_handler_receives_request_object(provider, scope, registry, client):
    _register_app(provider, scope)
    captured = {}

    def handler(req):
        captured["method"] = req.method
        captured["body"] = req.get_data(as_text=True)
        captured["q"] = req.args.get("x")
        return {"body": "ok"}

    registry.register("app1", "echo", handler)
    client.post("/app1/api/echo?x=42", data=b"payload")
    assert captured == {"method": "POST", "body": "payload", "q": "42"}


def test_invoke_missing_app_returns_404(client):
    resp = client.get("/no-app/api/anything")
    assert resp.status_code == 404
    assert json.loads(resp.data)["error"]["code"] == "FunctionAppNotFound"


def test_invoke_missing_function_returns_404(provider, scope, client):
    _register_app(provider, scope)
    resp = client.get("/app1/api/no-fn")
    assert resp.status_code == 404
    assert json.loads(resp.data)["error"]["code"] == "FunctionNotFound"


def test_handler_exception_returns_500(provider, scope, registry, client):
    _register_app(provider, scope)

    def boom(req):
        raise RuntimeError("kaboom")

    registry.register("app1", "boom", boom)
    resp = client.get("/app1/api/boom")
    assert resp.status_code == 500
    body = json.loads(resp.data)
    assert body["error"]["code"] == "FunctionInvocationFailed"
    assert "kaboom" in body["error"]["message"]


def test_handler_returns_plain_bytes(provider, scope, registry, client):
    _register_app(provider, scope)
    registry.register("app1", "bytes", lambda req: b"raw-bytes")
    resp = client.get("/app1/api/bytes")
    assert resp.status_code == 200
    assert resp.data == b"raw-bytes"


def test_unknown_path_returns_404(client):
    resp = client.get("/some/weird/path")
    assert resp.status_code == 404


def test_registry_unregister(provider, scope, registry, client):
    _register_app(provider, scope)
    registry.register("app1", "fn", lambda req: {"body": "ok"})
    assert registry.list_functions("app1") == ("fn",)
    registry.unregister("app1", "fn")
    resp = client.get("/app1/api/fn")
    assert resp.status_code == 404
