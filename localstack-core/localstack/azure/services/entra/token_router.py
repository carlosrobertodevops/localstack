"""Mock Microsoft Entra ID (Azure AD) v2.0 token endpoint.

Produces an unsigned-but-decodable JWT shaped like a real Azure access token. Not
cryptographically valid — meant for local-only tests that decode `appid`/`upn`/`aud`.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import time
from typing import Any

from werkzeug.wrappers import Request, Response

_TOKEN_PATH_RE = re.compile(r"^/(?P<tenant>[^/]+)/oauth2/v2\.0/token$")
_DEFAULT_LIFETIME_S = 3600
_HMAC_SECRET = b"localstack-azure-entra-mock"


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _json_response(payload: dict[str, Any], status: int = 200) -> Response:
    return Response(json.dumps(payload), status=status, mimetype="application/json")


def _error(code: str, description: str, status: int = 400) -> Response:
    return _json_response({"error": code, "error_description": description}, status=status)


def _scope_to_audience(scope: str | None) -> str:
    if not scope:
        return "https://management.azure.com/"
    first = scope.split()[0]
    if first.endswith("/.default"):
        return first[: -len(".default")]
    return first


def _build_jwt(tenant: str, claims: dict[str, Any]) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    header_segment = _b64url(json.dumps(header, separators=(",", ":")).encode())
    payload_segment = _b64url(json.dumps(claims, separators=(",", ":")).encode())
    signing_input = f"{header_segment}.{payload_segment}".encode()
    sig = hmac.new(_HMAC_SECRET, signing_input, hashlib.sha256).digest()
    return f"{header_segment}.{payload_segment}.{_b64url(sig)}"


class EntraTokenRouter:
    """WSGI router for `POST /{tenant}/oauth2/v2.0/token`."""

    def __call__(self, environ, start_response):
        request = Request(environ)
        response = self._dispatch(request)
        return response(environ, start_response)

    def _dispatch(self, request: Request) -> Response:
        match = _TOKEN_PATH_RE.match(request.path)
        if not match:
            return _error("not_found", "unknown route", status=404)
        if request.method != "POST":
            return _error("method_not_allowed", f"{request.method} not supported", status=405)

        tenant = match.group("tenant")
        form = request.form
        grant_type = form.get("grant_type")
        client_id = form.get("client_id")
        scope = form.get("scope")

        if not grant_type:
            return _error("invalid_request", "grant_type is required")
        if grant_type not in ("client_credentials", "password"):
            return _error("unsupported_grant_type", f"grant '{grant_type}' not supported")
        if not client_id:
            return _error("invalid_client", "client_id is required")

        now = int(time.time())
        claims: dict[str, Any] = {
            "iss": f"https://localhost/{tenant}/v2.0",
            "aud": _scope_to_audience(scope),
            "iat": now,
            "nbf": now,
            "exp": now + _DEFAULT_LIFETIME_S,
            "appid": client_id,
            "tid": tenant,
        }
        if grant_type == "password":
            claims["upn"] = form.get("username", "")

        token = _build_jwt(tenant, claims)
        return _json_response(
            {
                "token_type": "Bearer",
                "expires_in": _DEFAULT_LIFETIME_S,
                "ext_expires_in": _DEFAULT_LIFETIME_S,
                "access_token": token,
            }
        )
