"""Cloud Functions control plane router.

| Method | Path                                                              | Action          |
| ------ | ----------------------------------------------------------------- | --------------- |
| POST   | /v2/projects/{p}/locations/{l}/functions?functionId=ID            | create function |
| GET    | /v2/projects/{p}/locations/{l}/functions                          | list functions  |
| GET    | /v2/projects/{p}/locations/{l}/functions/{f}                      | get function    |
| DELETE | /v2/projects/{p}/locations/{l}/functions/{f}                      | delete function |
"""

from __future__ import annotations

import json

from werkzeug.wrappers import Request, Response

from localstack.gcp.exceptions import GcpError, GcpInvalidRequest, GcpNotFound
from localstack.gcp.serializers import parse_json_body, serialize_error
from localstack.gcp.services.functions.provider import CloudFunctionsProvider


class FunctionsControlRouter:
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
        path = request.path
        method = request.method.upper()
        if not path.startswith("/v2/projects/"):
            raise GcpNotFound(f"unknown path: {path}")
        rest = path[len("/v2/projects/") :]
        parts = rest.split("/")
        if len(parts) < 4 or parts[1] != "locations" or parts[3] != "functions":
            raise GcpNotFound(f"unknown path: {path}")
        project = parts[0]
        location = parts[2]
        tail = parts[4] if len(parts) > 4 else ""

        if not tail:
            if method == "POST":
                fid = request.args.get("functionId")
                if not fid:
                    raise GcpInvalidRequest("query parameter 'functionId' required")
                body = parse_json_body(request.get_data()) if request.get_data() else {}
                bc = body.get("buildConfig") or {}
                sc = body.get("serviceConfig") or {}
                full = f"projects/{project}/locations/{location}/functions/{fid}"
                fn = self.provider.create_function(
                    full,
                    runtime=bc.get("runtime", "python313"),
                    entry_point=bc.get("entryPoint", "main"),
                    environment=sc.get("environmentVariables"),
                    labels=body.get("labels"),
                )
                return self._json(fn.to_dict())
            if method == "GET":
                items = self.provider.list_functions(project, location)
                return self._json({"functions": [f.to_dict() for f in items]})
            raise GcpInvalidRequest(f"method {method} not allowed on collection")

        full = f"projects/{project}/locations/{location}/functions/{tail}"
        if method == "GET":
            return self._json(self.provider.get_function(full).to_dict())
        if method == "DELETE":
            self.provider.delete_function(full)
            return self._json({})
        raise GcpInvalidRequest(f"method {method} not allowed on function")

    @staticmethod
    def _json(payload: dict, status: int = 200) -> Response:
        return Response(json.dumps(payload), status=status, mimetype="application/json")
