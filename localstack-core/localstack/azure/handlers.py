"""Reusable handler chain for the Azure gateway.

Analogous to `localstack.aws.chain` but Azure-flavored: minimal middleware that
extracts bearer tokens, populates a request context, and serializes errors to
ARM-style JSON.
"""

from __future__ import annotations

import json
import traceback
from dataclasses import dataclass, field
from typing import Any, Callable, Protocol
from uuid import uuid4

from werkzeug.wrappers import Request, Response

from localstack.azure.exceptions import (
    AzureError,
    AzureInvalidRequest,
    AzureNotFound,
    AzureUnsupportedOperation,
)


@dataclass
class AzureRequestContext:
    """Per-request state populated by handlers and read by inner endpoints."""

    request_id: str = ""
    client_request_id: str | None = None
    api_version: str | None = None
    bearer_token: str | None = None
    extras: dict[str, Any] = field(default_factory=dict)


class Handler(Protocol):
    def handle(self, request: Request, context: AzureRequestContext) -> None: ...


# ---- handlers ----


class AuthHandler:
    """Parse `Authorization: Bearer <jwt>` into the context.

    With `required=False` skips when the header is missing. With `required=True`
    raises `AzureInvalidRequest` for missing / non-Bearer auth.
    """

    def __init__(self, *, required: bool = False) -> None:
        self.required = required

    def handle(self, request: Request, context: AzureRequestContext) -> None:
        header = request.headers.get("Authorization")
        if not header:
            if self.required:
                raise AzureInvalidRequest("Authorization header required")
            return
        scheme, _, token = header.partition(" ")
        if scheme.lower() != "bearer" or not token:
            raise AzureInvalidRequest("Authorization scheme must be 'Bearer'")
        context.bearer_token = token


class RequestContextHandler:
    """Mint a per-request id and capture client-provided correlation headers."""

    def handle(self, request: Request, context: AzureRequestContext) -> None:
        context.request_id = str(uuid4())
        context.client_request_id = request.headers.get("x-ms-client-request-id")
        context.api_version = request.args.get("api-version")


class ErrorSerializerHandler:
    """Translate Python exceptions into ARM-style JSON error responses."""

    _STATUS_MAP = {
        AzureNotFound: (404, "NotFound"),
        AzureInvalidRequest: (400, "BadRequest"),
        AzureUnsupportedOperation: (501, "UnsupportedAzureOperation"),
    }

    def serialize(self, exc: BaseException) -> Response:
        for exc_type, (status, code) in self._STATUS_MAP.items():
            if isinstance(exc, exc_type):
                return self._build(code, str(exc), status)
        if isinstance(exc, AzureError):
            return self._build(getattr(exc, "code", "AzureError"), str(exc), getattr(exc, "status_code", 500))
        last = traceback.format_exception_only(type(exc), exc)[-1].strip()
        return self._build("InternalServerError", last, 500)

    @staticmethod
    def _build(code: str, message: str, status: int) -> Response:
        body = json.dumps({"error": {"code": code, "message": message}})
        return Response(body, status=status, mimetype="application/json")


# ---- chain ----


InnerCallable = Callable[[Request, AzureRequestContext], Response]


class HandlerChain:
    """Runs pre-handlers in order then the inner endpoint, serializing any error."""

    def __init__(
        self,
        handlers: list[Handler],
        *,
        error_serializer: ErrorSerializerHandler,
    ) -> None:
        self.handlers = list(handlers)
        self.error_serializer = error_serializer

    def invoke(
        self,
        request: Request,
        context: AzureRequestContext,
        inner: InnerCallable,
    ) -> Response:
        try:
            for handler in self.handlers:
                handler.handle(request, context)
            response = inner(request, context)
        except BaseException as exc:  # noqa: BLE001 — convert to ARM error JSON
            response = self.error_serializer.serialize(exc)
        # propagate request id back to the client (Azure standard headers)
        if context.request_id:
            response.headers.setdefault("x-ms-request-id", context.request_id)
        if context.client_request_id:
            response.headers.setdefault("x-ms-client-request-id", context.client_request_id)
        return response
