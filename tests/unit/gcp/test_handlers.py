import json

import pytest
from werkzeug.test import EnvironBuilder
from werkzeug.wrappers import Request, Response

from localstack.gcp.exceptions import GcpInvalidRequest, GcpNotFound
from localstack.gcp.handlers import (
    AuthHandler,
    ErrorSerializerHandler,
    GcpRequestContext,
    HandlerChain,
    RequestContextHandler,
)


def _req(headers=None):
    return Request(EnvironBuilder(headers=headers or {}).get_environ())


def test_auth_handler_optional_missing():
    h = AuthHandler(required=False)
    ctx = GcpRequestContext()
    h.handle(_req(), ctx)
    assert ctx.bearer_token is None


def test_auth_handler_required_raises():
    h = AuthHandler(required=True)
    with pytest.raises(GcpInvalidRequest):
        h.handle(_req(), GcpRequestContext())


def test_auth_handler_bad_scheme():
    h = AuthHandler()
    with pytest.raises(GcpInvalidRequest):
        h.handle(_req({"Authorization": "Basic abc"}), GcpRequestContext())


def test_auth_handler_parses_token():
    h = AuthHandler()
    ctx = GcpRequestContext()
    h.handle(_req({"Authorization": "Bearer abc.def.ghi"}), ctx)
    assert ctx.bearer_token == "abc.def.ghi"


def test_request_context_handler_sets_id():
    h = RequestContextHandler()
    ctx = GcpRequestContext()
    h.handle(_req({"x-goog-request-tag": "tag1"}), ctx)
    assert ctx.request_id
    assert ctx.extras["x-goog-request-tag"] == "tag1"


def test_error_serializer_known_error():
    s = ErrorSerializerHandler()
    resp = s.serialize(GcpNotFound("missing"))
    assert resp.status_code == 404
    body = json.loads(resp.data)
    assert body["error"]["status"] == "NOT_FOUND"


def test_error_serializer_generic():
    s = ErrorSerializerHandler()
    resp = s.serialize(RuntimeError("boom"))
    assert resp.status_code == 500
    assert json.loads(resp.data)["error"]["status"] == "INTERNAL"


def test_handler_chain_invokes_in_order_then_inner():
    chain = HandlerChain(
        [AuthHandler(), RequestContextHandler()],
        error_serializer=ErrorSerializerHandler(),
    )
    ctx = GcpRequestContext()

    def inner(_req, _ctx):
        assert _ctx.request_id
        return Response("ok", status=200)

    resp = chain.invoke(_req({"Authorization": "Bearer t"}), ctx, inner)
    assert resp.status_code == 200
    assert ctx.bearer_token == "t"
    assert resp.headers["x-goog-request-id"] == ctx.request_id


def test_handler_chain_catches_and_serializes():
    chain = HandlerChain([], error_serializer=ErrorSerializerHandler())

    def inner(_req, _ctx):
        raise GcpNotFound("nope")

    resp = chain.invoke(_req(), GcpRequestContext(), inner)
    assert resp.status_code == 404
