"""Azure edge gateway — dispatches requests to ARM / data-plane routers by host.

Path-based fallback (no Host header or Host=`localhost`) routes to ARM router so
local-tests can target the gateway without DNS gymnastics.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable

from werkzeug.wrappers import Request, Response

from localstack.azure.arm_router import ArmRouter
from localstack.azure.defaults import create_default_registry
from localstack.azure.resource_manager import ResourceManagerProvider
from localstack.azure.services.cosmos import CosmosSqlRouter, MicrosoftDocumentDBProvider
from localstack.azure.services.entra import EntraTokenRouter
from localstack.azure.services.functions import (
    FunctionsHttpRouter,
    FunctionsRegistry,
    MicrosoftWebProvider,
)
from localstack.azure.services.storage import (
    BlobRouter,
    MicrosoftStorageProvider,
    QueueRouter,
)
from localstack.azure.stores import AzureStores

_BLOB_HOST_RE = re.compile(r"^(?P<acct>[^.]+)\.blob\.core\.windows\.net$", re.IGNORECASE)
_QUEUE_HOST_RE = re.compile(r"^(?P<acct>[^.]+)\.queue\.core\.windows\.net$", re.IGNORECASE)
_FUNCTIONS_HOST_RE = re.compile(r"^(?P<app>[^.]+)\.azurewebsites\.net$", re.IGNORECASE)
_COSMOS_HOST_RE = re.compile(r"^(?P<acct>[^.]+)\.documents\.azure\.com$", re.IGNORECASE)
_ENTRA_HOSTS = frozenset(
    {"login.microsoftonline.com", "login.microsoft.com", "login.windows.net"}
)


def _not_found() -> Response:
    return Response(
        json.dumps({"error": {"code": "RouteNotFound", "message": "no route matched"}}),
        status=404,
        mimetype="application/json",
    )


def _arm_metadata_endpoints(endpoint: str) -> Response:
    body = {
        "galleryEndpoint": endpoint,
        "graphEndpoint": endpoint,
        "portalEndpoint": endpoint,
        "authentication": {
            "loginEndpoint": endpoint,
            "audiences": [endpoint],
            "tenant": "localstack-tenant",
            "identityProvider": "AAD",
        },
        "graph": endpoint,
        "graphAudience": endpoint,
        "msGraph": endpoint,
        "appInsightsResourceId": endpoint,
        "appInsightsTelemetryChannelResourceId": endpoint,
        "synapseAnalyticsResourceId": endpoint,
        "logAnalyticsResourceId": endpoint,
        "ossrDbmsResourceId": endpoint,
        "microsoftGraphResourceId": endpoint,
        "media": endpoint,
        "attestationResourceId": endpoint,
        "batch": endpoint,
        "resourceManager": endpoint,
        "vmImageAliasDoc": endpoint,
        "sqlManagement": endpoint,
        "activeDirectoryDataLake": endpoint,
        "suffixes": {
            "azureDataLakeStoreFileSystem": "azuredatalakestore.net",
            "acrLoginServer": "azurecr.io",
            "sqlServerHostname": ".database.windows.net",
            "azureDataLakeAnalyticsCatalogAndJob": "azuredatalakeanalytics.net",
            "keyVaultDns": ".vault.azure.net",
            "storage": "core.windows.net",
            "storageSyncEndpointSuffix": "afs.azure.net",
            "mhsmDns": ".managedhsm.azure.net",
            "mysqlServerEndpoint": ".mysql.database.azure.com",
            "postgresqlServerEndpoint": ".postgres.database.azure.com",
            "mariadbServerEndpoint": ".mariadb.database.azure.com",
            "synapseAnalytics": ".dev.azuresynapse.net",
            "attestationEndpoint": ".attest.azure.net",
        },
        "name": "LocalStack",
        "type": "Microsoft.Azure",
    }
    return Response(json.dumps(body), status=200, mimetype="application/json")


class AzureGateway:
    """Single WSGI entrypoint mounting every Azure router."""

    def __init__(self) -> None:
        self.stores = AzureStores()
        registry = create_default_registry()
        self.resource_manager = ResourceManagerProvider(stores=self.stores, registry=registry)
        self.storage_provider = MicrosoftStorageProvider(
            resource_manager=self.resource_manager, stores=self.stores
        )
        self.functions_provider = MicrosoftWebProvider(
            resource_manager=self.resource_manager, stores=self.stores
        )
        self.cosmos_provider = MicrosoftDocumentDBProvider(
            resource_manager=self.resource_manager, stores=self.stores
        )
        self.functions_registry = FunctionsRegistry()

        self.arm_router = ArmRouter(provider=self.resource_manager)
        self.blob_router = BlobRouter(provider=self.storage_provider)
        self.queue_router = QueueRouter(provider=self.storage_provider)
        self.cosmos_router = CosmosSqlRouter(provider=self.cosmos_provider)
        self.functions_router = FunctionsHttpRouter(
            provider=self.functions_provider, registry=self.functions_registry
        )
        self.entra_router = EntraTokenRouter()

    def __call__(self, environ, start_response):
        request = Request(environ)
        if request.path == "/metadata/endpoints":
            scheme = environ.get("wsgi.url_scheme", "http")
            endpoint = f"{scheme}://{request.host}"
            return _arm_metadata_endpoints(endpoint)(environ, start_response)
        target, rewrite = self._select_router(request)
        if target is None:
            return _not_found()(environ, start_response)
        if rewrite is not None:
            environ = {**environ, "PATH_INFO": rewrite}
        return target(environ, start_response)

    def _select_router(
        self, request: Request
    ) -> tuple[Callable | None, str | None]:
        host = (request.host or "").split(":", 1)[0].lower()

        if host in _ENTRA_HOSTS:
            return self.entra_router, None

        m = _BLOB_HOST_RE.match(host)
        if m:
            return self.blob_router, f"/{m.group('acct')}{request.path}"

        m = _QUEUE_HOST_RE.match(host)
        if m:
            return self.queue_router, f"/{m.group('acct')}{request.path}"

        m = _FUNCTIONS_HOST_RE.match(host)
        if m:
            return self.functions_router, f"/{m.group('app')}{request.path}"

        m = _COSMOS_HOST_RE.match(host)
        if m:
            return self.cosmos_router, f"/{m.group('acct')}{request.path}"

        # path-based fallback: ARM control plane
        if request.path.startswith("/subscriptions/"):
            return self.arm_router, None

        # entra fallback for /{tenant}/oauth2/v2.0/token regardless of host
        if request.path.endswith("/oauth2/v2.0/token"):
            return self.entra_router, None

        # OpenID Connect discovery paths used by `az login` and SDKs
        if (
            request.path.endswith("/.well-known/openid-configuration")
            or "/discovery/v2.0/keys" in request.path
            or request.path == "/common/discovery/instance"
        ):
            return self.entra_router, None

        return None, None
