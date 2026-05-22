import json

import pytest
from werkzeug.test import Client
from werkzeug.wrappers import Response

from localstack.gcp.services.functions import (
    CloudFunctionsProvider,
    FunctionsControlRouter,
    FunctionsHttpRouter,
    FunctionsRegistry,
)


@pytest.fixture
def provider():
    return CloudFunctionsProvider()


@pytest.fixture
def control_client(provider):
    return Client(FunctionsControlRouter(provider=provider), Response)


@pytest.fixture
def http_client(provider):
    return Client(FunctionsHttpRouter(provider=provider), Response)


def test_create_function(control_client):
    r = control_client.post(
        "/v2/projects/p1/locations/us-central1/functions?functionId=hello",
        data=json.dumps({
            "buildConfig": {"runtime": "python313", "entryPoint": "main"},
            "serviceConfig": {"environmentVariables": {"FOO": "bar"}},
        }),
        content_type="application/json",
    )
    assert r.status_code == 200
    body = json.loads(r.data)
    assert body["name"] == "projects/p1/locations/us-central1/functions/hello"


def test_list_functions(control_client):
    for fid in ("a", "b"):
        control_client.post(
            f"/v2/projects/p1/locations/us-central1/functions?functionId={fid}",
            data=b"{}",
            content_type="application/json",
        )
    r = control_client.get("/v2/projects/p1/locations/us-central1/functions")
    fns = json.loads(r.data)["functions"]
    assert {f["name"].rsplit("/", 1)[1] for f in fns} == {"a", "b"}


def test_get_function(control_client):
    control_client.post(
        "/v2/projects/p1/locations/us-central1/functions?functionId=hello",
        data=b"{}",
        content_type="application/json",
    )
    r = control_client.get("/v2/projects/p1/locations/us-central1/functions/hello")
    assert r.status_code == 200


def test_delete_function(control_client):
    control_client.post(
        "/v2/projects/p1/locations/us-central1/functions?functionId=hello",
        data=b"{}",
        content_type="application/json",
    )
    r = control_client.delete("/v2/projects/p1/locations/us-central1/functions/hello")
    assert r.status_code == 200
    r = control_client.get("/v2/projects/p1/locations/us-central1/functions/hello")
    assert r.status_code == 404


def test_create_requires_function_id(control_client):
    r = control_client.post(
        "/v2/projects/p1/locations/us-central1/functions",
        data=b"{}",
        content_type="application/json",
    )
    assert r.status_code == 400


def test_invoke_registered(provider, control_client, http_client):
    control_client.post(
        "/v2/projects/p1/locations/us-central1/functions?functionId=hello",
        data=b"{}",
        content_type="application/json",
    )

    def handler(env, body):
        return 200, {"X-Echo": "yes"}, b"hi from fn"

    provider.attach_handler(
        "projects/p1/locations/us-central1/functions/hello", handler
    )

    r = http_client.get("/us-central1/p1/hello")
    assert r.status_code == 200
    assert r.data == b"hi from fn"
    assert r.headers["X-Echo"] == "yes"


def test_invoke_unregistered_returns_404(http_client):
    r = http_client.get("/us-central1/p1/missing")
    assert r.status_code == 404


def test_registry_has_lookup():
    r = FunctionsRegistry()
    r.register("us", "p", "f", lambda e, b: (200, {}, b""))
    assert r.has("US", "P", "F")
    assert not r.has("us", "p", "x")
