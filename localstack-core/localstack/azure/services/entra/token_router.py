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
_OIDC_CONFIG_RE = re.compile(
    r"^/(?P<tenant>[^/]+)/v2\.0/\.well-known/openid-configuration$"
)
_OIDC_CONFIG_NOPATH_RE = re.compile(
    r"^/(?P<tenant>[^/]+)/\.well-known/openid-configuration$"
)
_OIDC_KEYS_RE = re.compile(r"^/(?P<tenant>[^/]+)/discovery/v2\.0/keys$")
_DISCOVERY_INSTANCE_RE = re.compile(r"^/common/discovery/instance$")
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
        path = request.path

        if _DISCOVERY_INSTANCE_RE.match(path):
            return self._discovery_instance(request)

        oidc_match = _OIDC_CONFIG_RE.match(path) or _OIDC_CONFIG_NOPATH_RE.match(path)
        if oidc_match:
            return self._openid_configuration(request, oidc_match.group("tenant"))

        keys_match = _OIDC_KEYS_RE.match(path)
        if keys_match:
            return self._jwks(keys_match.group("tenant"))

        match = _TOKEN_PATH_RE.match(path)
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

    def _base_url(self, request: Request) -> str:
        scheme = request.environ.get("wsgi.url_scheme", "http")
        return f"{scheme}://{request.host}"

    def _openid_configuration(self, request: Request, tenant: str) -> Response:
        base = self._base_url(request)
        return _json_response(
            {
                "token_endpoint": f"{base}/{tenant}/oauth2/v2.0/token",
                "token_endpoint_auth_methods_supported": [
                    "client_secret_post",
                    "client_secret_basic",
                    "private_key_jwt",
                ],
                "jwks_uri": f"{base}/{tenant}/discovery/v2.0/keys",
                "response_modes_supported": ["query", "fragment", "form_post"],
                "subject_types_supported": ["pairwise"],
                "id_token_signing_alg_values_supported": ["HS256"],
                "response_types_supported": [
                    "code",
                    "id_token",
                    "code id_token",
                    "id_token token",
                ],
                "scopes_supported": ["openid", "profile", "email", "offline_access"],
                "issuer": f"{base}/{tenant}/v2.0",
                "request_uri_parameter_supported": False,
                "userinfo_endpoint": f"{base}/oidc/userinfo",
                "authorization_endpoint": f"{base}/{tenant}/oauth2/v2.0/authorize",
                "device_authorization_endpoint": f"{base}/{tenant}/oauth2/v2.0/devicecode",
                "http_logout_supported": True,
                "frontchannel_logout_supported": True,
                "end_session_endpoint": f"{base}/{tenant}/oauth2/v2.0/logout",
                "claims_supported": [
                    "sub",
                    "iss",
                    "cloud_instance_name",
                    "cloud_instance_host_name",
                    "cloud_graph_host_name",
                    "msgraph_host",
                    "aud",
                    "exp",
                    "iat",
                    "auth_time",
                    "acr",
                    "nonce",
                    "preferred_username",
                    "name",
                    "tid",
                    "ver",
                    "at_hash",
                    "c_hash",
                    "email",
                ],
                "kerberos_endpoint": f"{base}/{tenant}/kerberos",
                "tenant_region_scope": "WW",
                "cloud_instance_name": "localstack",
                "cloud_graph_host_name": request.host,
                "msgraph_host": request.host,
                "rbac_url": base,
            }
        )

    def _jwks(self, tenant: str) -> Response:
        return _json_response({"keys": []})

    def _discovery_instance(self, request: Request) -> Response:
        base = self._base_url(request)
        # Accepts ?authorization_endpoint=...
        return _json_response(
            {
                "tenant_discovery_endpoint": f"{base}/common/v2.0/.well-known/openid-configuration",
                "api-version": "1.1",
                "metadata": [
                    {
                        "preferred_network": request.host,
                        "preferred_cache": request.host,
                        "aliases": [request.host, "localhost"],
                    }
                ],
            }
        )
