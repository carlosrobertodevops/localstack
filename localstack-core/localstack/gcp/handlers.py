"""Reusable handler chain for the GCP gateway.

Analogous to ``localstack.azure.handlers``. Parses ``Authorization: Bearer`` tokens,
extracts the request context (request id, api version), and serializes errors to
GCP-style JSON: ``{"error": {"code": <int>, "status": <name>, "message": <str>}}``.
"""

from __future__ import annotations

import json
import traceback
from dataclasses import dataclass, field
from typing import Any, Callable, Protocol
from uuid import uuid4

from werkzeug.wrappers import Request, Response

from localstack.gcp.exceptions import (
    GcpAlreadyExists,
    GcpError,
    GcpInvalidRequest,
    GcpNotFound,
    GcpUnsupportedOperation,
)


@dataclass
class GcpRequestContext:
    request_id: str = ""
    bearer_token: str | None = None
    project_id: str | None = None
    api_version: str | None = None
    extras: dict[str, Any] = field(default_factory=dict)


class Handler(Protocol):
    def handle(self, request: Request, context: GcpRequestContext) -> None: ...


class AuthHandler:
    def __init__(self, *, required: bool = False) -> None:
        self.required = required

    def handle(self, request: Request, context: GcpRequestContext) -> None:
        header = request.headers.get("Authorization")
        if not header:
            if self.required:
                raise GcpInvalidRequest("Authorization header required")
            return
        scheme, _, token = header.partition(" ")
        if scheme.lower() != "bearer" or not token:
            raise GcpInvalidRequest("Authorization scheme must be 'Bearer'")
        context.bearer_token = token


class RequestContextHandler:
    def handle(self, request: Request, context: GcpRequestContext) -> None:
        context.request_id = str(uuid4())
        # GCP uses ?alt= or path; api-version is conveyed via path segment (/v1/...).
        # we just leave api_version to be set by service routers if relevant.
        # Forward x-goog-* correlation headers via extras
        for k in request.headers.keys():
            if k.lower().startswith("x-goog-"):
                context.extras[k.lower()] = request.headers.get(k)


class ErrorSerializerHandler:
    _STATUS_MAP = {
        GcpNotFound: (404, "NOT_FOUND"),
        GcpAlreadyExists: (409, "ALREADY_EXISTS"),
        GcpInvalidRequest: (400, "INVALID_ARGUMENT"),
        GcpUnsupportedOperation: (501, "UNIMPLEMENTED"),
    }

    def serialize(self, exc: BaseException) -> Response:
        for exc_type, (status, code) in self._STATUS_MAP.items():
            if isinstance(exc, exc_type):
                return self._build(code, str(exc), status)
        if isinstance(exc, GcpError):
            return self._build(getattr(exc, "code", "INTERNAL"), str(exc), getattr(exc, "status_code", 500))
        last = traceback.format_exception_only(type(exc), exc)[-1].strip()
        return self._build("INTERNAL", last, 500)

    @staticmethod
    def _build(code: str, message: str, status: int) -> Response:
        body = json.dumps({"error": {"code": status, "status": code, "message": message}})
        return Response(body, status=status, mimetype="application/json")


InnerCallable = Callable[[Request, GcpRequestContext], Response]


class HandlerChain:
    def __init__(self, handlers: list[Handler], *, error_serializer: ErrorSerializerHandler) -> None:
        self.handlers = list(handlers)
        self.error_serializer = error_serializer

    def invoke(self, request: Request, context: GcpRequestContext, inner: InnerCallable) -> Response:
        try:
            for handler in self.handlers:
                handler.handle(request, context)
            response = inner(request, context)
        except BaseException as exc:  # noqa: BLE001
            response = self.error_serializer.serialize(exc)
        if context.request_id:
            response.headers.setdefault("x-goog-request-id", context.request_id)
        return response
