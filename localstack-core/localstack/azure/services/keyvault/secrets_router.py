"""Azure Key Vault REST adapter for the secrets data plane (subset of 7.4)."""

from __future__ import annotations

import json
import re

from werkzeug.wrappers import Request, Response

from localstack.azure.exceptions import AzureInvalidRequest, AzureNotFound
from localstack.azure.services.keyvault.provider import MicrosoftKeyVaultProvider

_PATH_LIST_RE = re.compile(r"^/(?P<vault>[^/]+)/secrets$")
_PATH_SECRET_RE = re.compile(r"^/(?P<vault>[^/]+)/secrets/(?P<name>[^/]+)$")
_PATH_VERSION_RE = re.compile(r"^/(?P<vault>[^/]+)/secrets/(?P<name>[^/]+)/(?P<version>[^/]+)$")


def _json(payload, status: int = 200) -> Response:
    return Response(json.dumps(payload), status=status, mimetype="application/json")


def _error(code: str, message: str, status: int) -> Response:
    return _json({"error": {"code": code, "message": message}}, status=status)


def _serialize_version(vault: str, name: str, version) -> dict:
    base = f"https://{vault}.vault.azure.net/secrets/{name}/{version.id}"
    return {
        "id": base,
        "value": version.value,
        "contentType": version.content_type,
        "attributes": {
            "enabled": version.enabled,
            "created": int(version.created.timestamp()),
            "updated": int(version.updated.timestamp()),
        },
        "tags": dict(version.tags),
    }


class KeyVaultSecretsRouter:
    """Path layout: /{vault}/secrets[/{name}[/{version}]]."""

    def __init__(self, provider: MicrosoftKeyVaultProvider) -> None:
        self.provider = provider

    def __call__(self, environ, start_response):
        request = Request(environ)
        response = self._dispatch(request)
        return response(environ, start_response)

    def _dispatch(self, request: Request) -> Response:
        path = request.path
        try:
            if match := _PATH_LIST_RE.match(path):
                return self._list_secrets(request, match.group("vault"))
            if match := _PATH_VERSION_RE.match(path):
                return self._get_version(
                    request, match.group("vault"), match.group("name"), match.group("version")
                )
            if match := _PATH_SECRET_RE.match(path):
                return self._secret_op(request, match.group("vault"), match.group("name"))
        except AzureNotFound as exc:
            return _error("SecretNotFound", str(exc), 404)
        except AzureInvalidRequest as exc:
            return _error("BadRequest", str(exc), 400)
        return _error("NotFound", "unsupported key vault path", 404)

    # -- handlers --

    def _list_secrets(self, request: Request, vault: str) -> Response:
        if request.method != "GET":
            return _error("MethodNotAllowed", f"{request.method} not supported", 405)
        secrets = self.provider.list_secrets(vault)
        return _json(
            {
                "value": [
                    {
                        "id": f"https://{vault}.vault.azure.net/secrets/{s.name}",
                        "attributes": {"enabled": s.latest.enabled},
                    }
                    for s in secrets
                ],
                "nextLink": None,
            }
        )

    def _secret_op(self, request: Request, vault: str, name: str) -> Response:
        if request.method == "PUT":
            try:
                body = json.loads(request.get_data(as_text=True) or "{}")
            except json.JSONDecodeError:
                return _error("BadRequest", "body is not valid JSON", 400)
            value = body.get("value")
            if not value:
                return _error("BadRequest", "secret 'value' is required", 400)
            version = self.provider.set_secret(
                vault,
                name,
                value,
                content_type=body.get("contentType"),
                tags=body.get("tags") or {},
            )
            return _json(_serialize_version(vault, name, version))
        if request.method == "GET":
            version = self.provider.get_secret(vault, name)
            return _json(_serialize_version(vault, name, version))
        if request.method == "DELETE":
            self.provider.delete_secret(vault, name)
            # Azure returns the deleted secret body; minimal impl returns 204
            return Response(status=204)
        return _error("MethodNotAllowed", f"{request.method} not supported", 405)

    def _get_version(
        self, request: Request, vault: str, name: str, version_id: str
    ) -> Response:
        if request.method != "GET":
            return _error("MethodNotAllowed", f"{request.method} not supported", 405)
        version = self.provider.get_secret(vault, name, version=version_id)
        return _json(_serialize_version(vault, name, version))
