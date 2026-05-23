import json
import re
from dataclasses import dataclass

import pytest
from werkzeug.test import Client
from werkzeug.wrappers import Request, Response

from localstack.azure.exceptions import AzureInvalidRequest, AzureNotFound
from localstack.azure.handlers import (
    AuthHandler,
    AzureRequestContext,
    ErrorSerializerHandler,
    HandlerChain,
    RequestContextHandler,
)


@pytest.fixture
def context():
    return AzureRequestContext()


def _make_request(path="/p", method="GET", headers=None) -> Request:
    from werkzeug.test import EnvironBuilder

    builder = EnvironBuilder(path=path, method=method, headers=headers or {})
    return Request(builder.get_environ())


# ---- AuthHandler ----


def test_auth_handler_accepts_bearer_token(context):
    handler = AuthHandler(required=True)
    request = _make_request(headers={"Authorization": "Bearer abc.def.ghi"})
    handler.handle(request, context)
    assert context.bearer_token == "abc.def.ghi"


def test_auth_handler_rejects_missing_when_required(context):
    handler = AuthHandler(required=True)
    request = _make_request()
    with pytest.raises(AzureInvalidRequest):
        handler.handle(request, context)


def test_auth_handler_skips_when_not_required(context):
    handler = AuthHandler(required=False)
    request = _make_request()
    handler.handle(request, context)
    assert context.bearer_token is None


def test_auth_handler_rejects_non_bearer_scheme(context):
    handler = AuthHandler(required=True)
    request = _make_request(headers={"Authorization": "Basic xyz"})
    with pytest.raises(AzureInvalidRequest):
        handler.handle(request, context)


# ---- RequestContextHandler ----


def test_request_context_handler_assigns_request_id(context):
    handler = RequestContextHandler()
    request = _make_request()
    handler.handle(request, context)
    assert re.match(r"[0-9a-f-]{36}", context.request_id)


def test_request_context_handler_keeps_caller_request_id(context):
    handler = RequestContextHandler()
    request = _make_request(headers={"x-ms-client-request-id": "client-123"})
    handler.handle(request, context)
    assert context.client_request_id == "client-123"
    assert context.request_id != "client-123"  # server still mints its own


def test_request_context_handler_captures_api_version(context):
    handler = RequestContextHandler()
    request = _make_request(path="/p?api-version=2023-01-01")
    handler.handle(request, context)
    assert context.api_version == "2023-01-01"


# ---- ErrorSerializerHandler ----


def test_error_serializer_translates_azure_notfound():
    handler = ErrorSerializerHandler()
    resp = handler.serialize(AzureNotFound("missing thing"))
    assert resp.status_code == 404
    body = json.loads(resp.data)
    assert body == {"error": {"code": "NotFound", "message": "missing thing"}}


def test_error_serializer_translates_azure_invalid_request():
    handler = ErrorSerializerHandler()
    resp = handler.serialize(AzureInvalidRequest("bad input"))
    assert resp.status_code == 400
    assert json.loads(resp.data)["error"]["code"] == "BadRequest"


def test_error_serializer_translates_unknown_to_500():
    handler = ErrorSerializerHandler()
    resp = handler.serialize(RuntimeError("kaboom"))
    assert resp.status_code == 500
    body = json.loads(resp.data)
    assert body["error"]["code"] == "InternalServerError"


# ---- HandlerChain ----


def test_chain_runs_handlers_in_order_and_returns_inner(context):
    @dataclass
    class Recorder:
        log: list

        def handle(self, request, ctx):
            self.log.append(("pre", request.path))

    log: list = []

    def inner(request, ctx):
        log.append(("inner", request.path))
        return Response("ok", status=200)

    chain = HandlerChain([Recorder(log), Recorder(log)], error_serializer=ErrorSerializerHandler())
    request = _make_request(path="/x")
    resp = chain.invoke(request, context, inner)
    assert resp.status_code == 200
    assert resp.data == b"ok"
    assert log == [("pre", "/x"), ("pre", "/x"), ("inner", "/x")]


def test_chain_serializes_inner_exception(context):
    chain = HandlerChain([], error_serializer=ErrorSerializerHandler())

    def inner(request, ctx):
        raise AzureNotFound("nope")

    resp = chain.invoke(_make_request(), context, inner)
    assert resp.status_code == 404


def test_chain_serializes_pre_handler_exception(context):
    class Boom:
        def handle(self, request, ctx):
            raise AzureInvalidRequest("bad header")

    chain = HandlerChain([Boom()], error_serializer=ErrorSerializerHandler())
    resp = chain.invoke(_make_request(), context, lambda r, c: Response("nope"))
    assert resp.status_code == 400


# ---- end-to-end on a small WSGI app ----


def test_chain_wraps_wsgi_endpoint_and_propagates_context():
    captured: dict = {}

    def inner(request, ctx):
        captured["request_id"] = ctx.request_id
        captured["bearer"] = ctx.bearer_token
        return Response("done", status=200)

    chain = HandlerChain(
        [AuthHandler(required=True), RequestContextHandler()],
        error_serializer=ErrorSerializerHandler(),
    )

    def app(environ, start_response):
        request = Request(environ)
        ctx = AzureRequestContext()
        return chain.invoke(request, ctx, inner)(environ, start_response)

    client = Client(app, Response)
    resp = client.get("/x", headers={"Authorization": "Bearer t-1"})
    assert resp.status_code == 200
    assert captured["bearer"] == "t-1"
    assert captured["request_id"]
