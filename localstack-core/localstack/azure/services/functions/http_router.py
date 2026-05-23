"""WSGI router invoking HTTP-triggered Azure Functions."""

from __future__ import annotations

import json
import traceback
from typing import Any

from werkzeug.wrappers import Request, Response

from localstack.azure.services.functions.provider import MicrosoftWebProvider
from localstack.azure.services.functions.registry import FunctionsRegistry


def _json_error(code: str, message: str, status: int) -> Response:
    payload = json.dumps({"error": {"code": code, "message": message}})
    return Response(payload, status=status, mimetype="application/json")


class FunctionsHttpRouter:
    """Routes `/{app}/api/{function}` to a Python handler in `FunctionsRegistry`."""

    def __init__(self, provider: MicrosoftWebProvider, registry: FunctionsRegistry) -> None:
        self.provider = provider
        self.registry = registry

    def __call__(self, environ, start_response):
        request = Request(environ)
        response = self._dispatch(request)
        return response(environ, start_response)

    def _dispatch(self, request: Request) -> Response:
        parts = request.path.strip("/").split("/")
        if len(parts) != 3 or parts[1] != "api":
            return _json_error("NotFound", "expected /{app}/api/{function}", 404)
        app_name, _, function_name = parts

        if self.provider.find_app(app_name) is None:
            return _json_error("FunctionAppNotFound", f"function app not found: {app_name}", 404)
        handler = self.registry.get(app_name, function_name)
        if handler is None:
            return _json_error(
                "FunctionNotFound",
                f"function not registered: {app_name}/{function_name}",
                404,
            )

        try:
            result = handler(request)
        except Exception as exc:  # noqa: BLE001 — surface any handler error as 500
            tb_last = traceback.format_exception_only(type(exc), exc)[-1].strip()
            return _json_error("FunctionInvocationFailed", tb_last, 500)

        return self._build_response(result)

    @staticmethod
    def _build_response(result: Any) -> Response:
        if isinstance(result, Response):
            return result
        if isinstance(result, (bytes, str)):
            return Response(result, status=200)
        if isinstance(result, dict):
            status = int(result.get("status", 200))
            headers = result.get("headers") or {}
            body = result.get("body", "")
            resp = Response(body, status=status)
            for k, v in headers.items():
                resp.headers[k] = v
            return resp
        return Response(str(result), status=200)
