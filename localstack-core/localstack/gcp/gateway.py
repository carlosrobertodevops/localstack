"""GCP edge gateway — dispatches requests by host + path to service routers."""

from __future__ import annotations

import json
import re
from typing import Callable

from werkzeug.wrappers import Request, Response

from localstack.gcp.resource_manager import ResourceManagerProvider
from localstack.gcp.services.bigquery import BigQueryProvider, BigQueryRouter
from localstack.gcp.services.cloudrun import CloudRunProvider, CloudRunRouter
from localstack.gcp.services.cloudsql import CloudSqlProvider, CloudSqlRouter
from localstack.gcp.services.cloudtasks import CloudTasksProvider, CloudTasksRouter
from localstack.gcp.services.dns import DnsProvider, DnsRouter
from localstack.gcp.services.firestore import FirestoreProvider, FirestoreRouter
from localstack.gcp.services.functions import (
    CloudFunctionsProvider,
    FunctionsControlRouter,
    FunctionsHttpRouter,
)
from localstack.gcp.services.iam import IamProvider, IamTokenRouter
from localstack.gcp.services.kms import KmsProvider, KmsRouter
from localstack.gcp.services.logging import LoggingProvider, LoggingRouter
from localstack.gcp.services.memorystore import MemorystoreProvider, MemorystoreRouter
from localstack.gcp.services.pubsub import PubSubProvider, PubSubRouter
from localstack.gcp.services.scheduler import SchedulerProvider, SchedulerRouter
from localstack.gcp.services.secretmanager import (
    SecretManagerProvider,
    SecretManagerRouter,
)
from localstack.gcp.services.spanner import SpannerProvider, SpannerRouter
from localstack.gcp.services.storage import (
    CloudStorageProvider,
    StorageJsonRouter,
    StorageXmlRouter,
)
from localstack.gcp.stores import GcpStores

_FUNCTIONS_HOST_RE = re.compile(
    r"^(?P<region>[a-z0-9-]+)-(?P<project>[a-z0-9-]+)\.cloudfunctions\.net$", re.IGNORECASE
)

_HOST_STORAGE = "storage.googleapis.com"
_HOST_PUBSUB = "pubsub.googleapis.com"
_HOST_FIRESTORE = "firestore.googleapis.com"
_HOST_FUNCTIONS_CTRL = "cloudfunctions.googleapis.com"
_HOST_IAM = "iam.googleapis.com"
_HOST_OAUTH2 = "oauth2.googleapis.com"
_HOST_BIGQUERY = "bigquery.googleapis.com"
_HOST_SECRETMANAGER = "secretmanager.googleapis.com"
_HOST_KMS = "cloudkms.googleapis.com"
_HOST_TASKS = "cloudtasks.googleapis.com"
_HOST_RUN = "run.googleapis.com"
_HOST_LOGGING = "logging.googleapis.com"
_HOST_SQL = "sqladmin.googleapis.com"
_HOST_SCHEDULER = "cloudscheduler.googleapis.com"
_HOST_DNS = "dns.googleapis.com"
_HOST_SPANNER = "spanner.googleapis.com"
_HOST_REDIS = "redis.googleapis.com"


def _not_found() -> Response:
    return Response(
        json.dumps({"error": {"code": 404, "status": "NOT_FOUND", "message": "no route matched"}}),
        status=404,
        mimetype="application/json",
    )


class GcpGateway:
    def __init__(self) -> None:
        self.stores = GcpStores()
        self.resource_manager = ResourceManagerProvider(stores=self.stores)
        self.storage_provider = CloudStorageProvider(
            resource_manager=self.resource_manager, stores=self.stores
        )
        self.pubsub_provider = PubSubProvider(
            resource_manager=self.resource_manager, stores=self.stores
        )
        self.firestore_provider = FirestoreProvider(
            resource_manager=self.resource_manager, stores=self.stores
        )
        self.functions_provider = CloudFunctionsProvider(
            resource_manager=self.resource_manager, stores=self.stores
        )
        self.iam_provider = IamProvider(
            resource_manager=self.resource_manager, stores=self.stores
        )
        self.bigquery_provider = BigQueryProvider(
            resource_manager=self.resource_manager, stores=self.stores
        )
        self.secretmanager_provider = SecretManagerProvider(
            resource_manager=self.resource_manager, stores=self.stores
        )
        self.kms_provider = KmsProvider(
            resource_manager=self.resource_manager, stores=self.stores
        )
        self.cloudtasks_provider = CloudTasksProvider(
            resource_manager=self.resource_manager, stores=self.stores
        )
        self.cloudrun_provider = CloudRunProvider(
            resource_manager=self.resource_manager, stores=self.stores
        )
        self.logging_provider = LoggingProvider(
            resource_manager=self.resource_manager, stores=self.stores
        )
        self.cloudsql_provider = CloudSqlProvider(
            resource_manager=self.resource_manager, stores=self.stores
        )
        self.scheduler_provider = SchedulerProvider(
            resource_manager=self.resource_manager, stores=self.stores
        )
        self.dns_provider = DnsProvider(
            resource_manager=self.resource_manager, stores=self.stores
        )
        self.spanner_provider = SpannerProvider(
            resource_manager=self.resource_manager, stores=self.stores
        )
        self.memorystore_provider = MemorystoreProvider(
            resource_manager=self.resource_manager, stores=self.stores
        )

        self.storage_json_router = StorageJsonRouter(provider=self.storage_provider)
        self.storage_xml_router = StorageXmlRouter(provider=self.storage_provider)
        self.pubsub_router = PubSubRouter(provider=self.pubsub_provider)
        self.firestore_router = FirestoreRouter(provider=self.firestore_provider)
        self.functions_http_router = FunctionsHttpRouter(provider=self.functions_provider)
        self.functions_control_router = FunctionsControlRouter(provider=self.functions_provider)
        self.iam_router = IamTokenRouter(provider=self.iam_provider)
        self.bigquery_router = BigQueryRouter(provider=self.bigquery_provider)
        self.secretmanager_router = SecretManagerRouter(provider=self.secretmanager_provider)
        self.kms_router = KmsRouter(provider=self.kms_provider)
        self.cloudtasks_router = CloudTasksRouter(provider=self.cloudtasks_provider)
        self.cloudrun_router = CloudRunRouter(provider=self.cloudrun_provider)
        self.logging_router = LoggingRouter(provider=self.logging_provider)
        self.cloudsql_router = CloudSqlRouter(provider=self.cloudsql_provider)
        self.scheduler_router = SchedulerRouter(provider=self.scheduler_provider)
        self.dns_router = DnsRouter(provider=self.dns_provider)
        self.spanner_router = SpannerRouter(provider=self.spanner_provider)
        self.memorystore_router = MemorystoreRouter(provider=self.memorystore_provider)

    def __call__(self, environ, start_response):
        request = Request(environ)
        target, rewrite = self._select_router(request)
        if target is None:
            return _not_found()(environ, start_response)
        if rewrite is not None:
            environ = {**environ, "PATH_INFO": rewrite}
        return target(environ, start_response)

    def _select_router(self, request: Request) -> tuple[Callable | None, str | None]:
        host = (request.host or "").split(":", 1)[0].lower()
        path = request.path

        if host == _HOST_OAUTH2 or path in {"/token", "/oauth2/v4/token", "/oauth2/v3/token"}:
            return self.iam_router, None

        if host == _HOST_STORAGE:
            if path.startswith("/storage/v1/") or path.startswith("/upload/storage/v1/"):
                return self.storage_json_router, None
            return self.storage_xml_router, None

        if host == _HOST_PUBSUB:
            return self.pubsub_router, None
        if host == _HOST_FIRESTORE:
            return self.firestore_router, None
        if host == _HOST_FUNCTIONS_CTRL:
            return self.functions_control_router, None

        m = _FUNCTIONS_HOST_RE.match(host)
        if m:
            return self.functions_http_router, f"/{m.group('region')}/{m.group('project')}{path}"

        if host == _HOST_IAM:
            return self.iam_router, None
        if host == _HOST_BIGQUERY:
            return self.bigquery_router, None
        if host == _HOST_SECRETMANAGER:
            return self.secretmanager_router, None
        if host == _HOST_KMS:
            return self.kms_router, None
        if host == _HOST_TASKS:
            return self.cloudtasks_router, None
        if host == _HOST_RUN:
            return self.cloudrun_router, None
        if host == _HOST_LOGGING:
            return self.logging_router, None
        if host == _HOST_SQL:
            return self.cloudsql_router, None
        if host == _HOST_SCHEDULER:
            return self.scheduler_router, None
        if host == _HOST_DNS:
            return self.dns_router, None
        if host == _HOST_SPANNER:
            return self.spanner_router, None
        if host == _HOST_REDIS:
            return self.memorystore_router, None

        # path-based fallbacks (no Host header)
        if path.startswith("/storage/v1/") or path.startswith("/upload/storage/v1/"):
            return self.storage_json_router, None
        if path.startswith("/v1/projects/") and (
            "/topics" in path or "/subscriptions" in path
        ):
            return self.pubsub_router, None
        if path.startswith("/v1/projects/") and "/databases" in path and "/instances/" not in path:
            return self.firestore_router, None
        if path.startswith("/v2/projects/") and "/functions" in path:
            return self.functions_control_router, None
        if path.startswith("/v1/projects/") and "/serviceAccounts" in path:
            return self.iam_router, None
        if path.startswith("/bigquery/v2/projects/"):
            return self.bigquery_router, None
        if path.startswith("/v1/projects/") and "/secrets" in path:
            return self.secretmanager_router, None
        if path.startswith("/v1/projects/") and "/keyRings" in path:
            return self.kms_router, None
        if path.startswith("/v2/projects/") and "/queues" in path:
            return self.cloudtasks_router, None
        if path.startswith("/v2/projects/") and "/services" in path:
            return self.cloudrun_router, None
        if path.startswith("/v2/entries:") or (
            path.startswith("/v2/projects/") and ("/logs/" in path or "/sinks" in path)
        ):
            return self.logging_router, None
        if path.startswith("/sql/v1beta4/projects/"):
            return self.cloudsql_router, None
        if path.startswith("/dns/v1/projects/"):
            return self.dns_router, None
        if path.startswith("/v1/projects/") and "/locations/" in path and "/jobs" in path:
            return self.scheduler_router, None
        if path.startswith("/v1/projects/") and "/instances/" in path:
            # spanner: /v1/projects/{p}/instances/{i}[/databases|/sessions]
            # memorystore: /v1/projects/{p}/locations/{l}/instances/{i}
            if "/locations/" in path:
                return self.memorystore_router, None
            return self.spanner_router, None

        return None, None
