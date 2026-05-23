"""Cross-cloud edge dispatcher.

Picks a registered cloud by host suffix and proxies the WSGI request to that
cloud's gateway. Lets AWS + Azure (and future GCP) share a single listening port.
"""

from __future__ import annotations

import fnmatch
import json
from typing import Any, Callable

from werkzeug.wrappers import Request, Response

from localstack.cloud.base import CloudProvider
from localstack.cloud.registry import CloudRegistry
from localstack.cloud.registry import registry as default_registry


def _not_found() -> Response:
    return Response(
        json.dumps({"error": {"code": "NoCloudMatched", "message": "no cloud matched the host"}}),
        status=404,
        mimetype="application/json",
    )


class MultiCloudEdge:
    """WSGI app routing per-host to the matching cloud gateway."""

    def __init__(
        self,
        *,
        registry: CloudRegistry | None = None,
        default_cloud: str | None = None,
    ) -> None:
        self.registry = registry if registry is not None else default_registry
        self.default_cloud = default_cloud
        self._gateway_cache: dict[str, Callable[..., Any]] = {}

    def __call__(self, environ, start_response):
        request = Request(environ)
        cloud = self._match(request)
        if cloud is None:
            return _not_found()(environ, start_response)
        gateway = self._gateway_cache.get(cloud.name)
        if gateway is None:
            gateway = cloud.build_gateway()
            self._gateway_cache[cloud.name] = gateway
        return gateway(environ, start_response)

    def _match(self, request: Request) -> CloudProvider | None:
        host = (request.host or "").split(":", 1)[0].lower()
        for cloud in self.registry:
            for pattern in cloud.edge_hosts:
                if fnmatch.fnmatch(host, pattern.lower()):
                    return cloud
        if self.default_cloud:
            return self.registry.get(self.default_cloud)
        return None
