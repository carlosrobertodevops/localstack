"""Forwards requests that look like Azure or GCP CLI calls to the appropriate cloud gateway.

The AWS gateway is the only listener on :4566, so requests issued by `az` /
`gcloud` configured against http://localhost:4566 arrive here with Host
set to localhost. This handler matches by host suffix and by path prefix and
dispatches to the registered cloud gateway via WSGI.
"""

from __future__ import annotations

import logging

from localstack.platform.http import Response

from ..api import RequestContext
from ..chain import Handler, HandlerChain

LOG = logging.getLogger(__name__)


_AZURE_HOST_SUFFIXES = (
    ".blob.core.windows.net",
    ".queue.core.windows.net",
    ".table.core.windows.net",
    ".file.core.windows.net",
    ".documents.azure.com",
    ".azurewebsites.net",
    ".vault.azure.net",
)
_AZURE_HOSTS = {
    "login.microsoftonline.com",
    "login.microsoft.com",
    "login.windows.net",
    "management.azure.com",
    "graph.microsoft.com",
}

_GCP_HOST_SUFFIXES = (
    ".googleapis.com",
    ".cloudfunctions.net",
)

_AZURE_PATH_PREFIXES = (
    "/subscriptions/",
    "/tenants/",
    "/providers/",
)
_AZURE_PATH_EXACT = {"/metadata/endpoints"}

_GCP_PATH_PREFIXES = (
    "/storage/v1/",
    "/upload/storage/v1/",
    "/bigquery/v2/projects/",
    "/sql/v1beta4/projects/",
    "/dns/v1/projects/",
)


def _looks_like_gcp_v1_projects(path: str) -> bool:
    # /v1/projects/<id>/(topics|subscriptions|databases|secrets|keyRings|serviceAccounts|locations)
    if not (path.startswith("/v1/projects/") or path.startswith("/v2/projects/")):
        return False
    tail = path.split("/", 4)
    if len(tail) < 5:
        return False
    return any(
        seg in path
        for seg in (
            "/topics",
            "/subscriptions",
            "/databases",
            "/secrets",
            "/keyRings",
            "/serviceAccounts",
            "/locations/",
            "/queues",
            "/services",
            "/functions",
        )
    )


class MultiCloudRouterHandler(Handler):
    def __init__(self) -> None:
        self._gateway_cache: dict[str, object] = {}

    def _gateway_for(self, cloud_name: str):
        gw = self._gateway_cache.get(cloud_name)
        if gw is not None:
            return gw
        from localstack.cloud.builtin import register_builtins
        from localstack.cloud.registry import registry

        if len(registry) == 0:
            register_builtins(registry)
        provider = registry.get(cloud_name)
        if provider is None:
            return None
        try:
            gw = provider.build_gateway()
        except Exception:
            LOG.exception("failed to build gateway for cloud %s", cloud_name)
            return None
        self._gateway_cache[cloud_name] = gw
        return gw

    def _match_cloud(self, host: str, path: str) -> str | None:
        if host in _AZURE_HOSTS:
            return "azure"
        if any(host.endswith(suffix) for suffix in _AZURE_HOST_SUFFIXES):
            return "azure"
        if any(host.endswith(suffix) for suffix in _GCP_HOST_SUFFIXES):
            return "gcp"
        if path in _AZURE_PATH_EXACT:
            return "azure"
        if any(path.startswith(p) for p in _AZURE_PATH_PREFIXES):
            return "azure"
        if path.endswith("/oauth2/v2.0/token"):
            return "azure"
        if path.endswith("/.well-known/openid-configuration"):
            return "azure"
        if "/discovery/v2.0/keys" in path or path == "/common/discovery/instance":
            return "azure"
        if "/oauth2/v2.0/" in path:
            return "azure"
        if any(path.startswith(p) for p in _GCP_PATH_PREFIXES):
            return "gcp"
        if _looks_like_gcp_v1_projects(path):
            return "gcp"
        if path.startswith("/v2/entries:"):
            return "gcp"
        return None

    def __call__(self, chain: HandlerChain, context: RequestContext, response: Response):
        request = context.request
        host = (request.host or "").split(":", 1)[0].lower()
        cloud = self._match_cloud(host, request.path)
        if cloud is None:
            return
        gw = self._gateway_for(cloud)
        if gw is None:
            return

        captured: dict = {}

        def _start_response(status, headers, exc_info=None):
            captured["status"] = status
            captured["headers"] = headers
            return lambda b: None

        try:
            body_iter = gw(request.environ, _start_response)
            body = b"".join(body_iter)
        except Exception:
            LOG.exception("multi-cloud dispatch to %s failed", cloud)
            return

        status_line = captured.get("status", "500 Internal Server Error")
        try:
            status_code = int(status_line.split(" ", 1)[0])
        except ValueError:
            status_code = 500

        response.status_code = status_code
        for key, value in captured.get("headers", []):
            if key.lower() in ("content-length", "transfer-encoding"):
                continue
            response.headers[key] = value
        response.data = body
        chain.stop()
