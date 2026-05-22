"""HTTP trigger router for Cloud Functions.

Host pattern: ``{region}-{project}.cloudfunctions.net``. The function name is the first
path segment: ``/{function}/...``. After rewriting, the remainder of the path is passed
to the handler via ``environ['PATH_INFO']``.
"""

from __future__ import annotations

import re

from werkzeug.wrappers import Request, Response

from localstack.gcp.exceptions import GcpError, GcpNotFound
from localstack.gcp.serializers import serialize_error
from localstack.gcp.services.functions.provider import CloudFunctionsProvider

# Path-form (used after host rewrite or for testing): /{region}/{project}/{function}/...
_PATH_RE = re.compile(r"^/(?P<region>[^/]+)/(?P<project>[^/]+)/(?P<function>[^/]+)(?P<rest>(/.*)?)$")


class FunctionsHttpRouter:
    def __init__(self, *, provider: CloudFunctionsProvider) -> None:
        self.provider = provider

    def __call__(self, environ, start_response):
        request = Request(environ)
        try:
            response = self._dispatch(request)
        except GcpError as exc:
            status, body = serialize_error(exc)
            response = Response(body, status=status, mimetype="application/json")
        return response(environ, start_response)

    def _dispatch(self, request: Request) -> Response:
        m = _PATH_RE.match(request.path)
        if not m:
            raise GcpNotFound(f"unknown function path: {request.path}")
        region = m.group("region")
        project = m.group("project")
        function = m.group("function")
        status, headers, body = self.provider.invoke(
            region=region,
            project=project,
            function=function,
            request_env={"path": m.group("rest") or "/", "method": request.method, "headers": dict(request.headers)},
            body=request.get_data(),
        )
        resp = Response(body, status=status)
        for k, v in (headers or {}).items():
            resp.headers[k] = v
        return resp
