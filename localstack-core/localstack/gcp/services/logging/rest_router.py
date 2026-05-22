from __future__ import annotations

import json

from werkzeug.wrappers import Request, Response

from localstack.gcp.exceptions import GcpError, GcpInvalidRequest, GcpNotFound
from localstack.gcp.serializers import parse_json_body, serialize_error
from localstack.gcp.services.logging.provider import LoggingProvider


class LoggingRouter:
    def __init__(self, *, provider: LoggingProvider) -> None:
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

        if path == "/v2/entries:write" and method == "POST":
            body = parse_json_body(request.get_data())
            count = self.provider.write_log_entries(body.get("entries") or [])
            return self._json({"entriesWritten": count})

        if path == "/v2/entries:list" and method == "POST":
            body = parse_json_body(request.get_data())
            projects = body.get("projectIds") or body.get("resourceNames") or []
            # accept either ['p1'] or ['projects/p1']
            resolved = [p.split("/", 1)[1] if p.startswith("projects/") else p for p in projects]
            filter_expr = body.get("filter", "")
            page_size = int(body.get("pageSize") or 50)
            entries: list = []
            for proj in resolved:
                entries.extend(
                    self.provider.list_log_entries(
                        proj, filter_expr=filter_expr, page_size=page_size
                    )
                )
            return self._json({"entries": [e.to_dict() for e in entries]})

        if path.startswith("/v2/projects/"):
            rest = path[len("/v2/projects/") :]
            parts = rest.split("/")
            project = parts[0]

            if len(parts) >= 3 and parts[1] == "logs":
                log_id = "/".join(parts[2:])
                if method == "DELETE":
                    log_name = f"projects/{project}/logs/{log_id}"
                    self.provider.delete_log(project, log_name)
                    return self._json({})

            if len(parts) >= 2 and parts[1] == "sinks":
                if len(parts) == 2:
                    if method == "POST":
                        body = parse_json_body(request.get_data())
                        name = body.get("name") or ""
                        sink_id = name.rsplit("/", 1)[-1] if name else None
                        if not sink_id:
                            raise GcpInvalidRequest("sink name required")
                        sink = self.provider.create_sink(
                            project,
                            sink_id,
                            destination=body.get("destination", ""),
                            filter_expr=body.get("filter", ""),
                        )
                        return self._json(sink.to_dict())
                    if method == "GET":
                        sinks = self.provider.list_sinks(project)
                        return self._json({"sinks": [s.to_dict() for s in sinks]})
                if len(parts) == 3:
                    sink_id = parts[2]
                    if method == "GET":
                        return self._json(self.provider.get_sink(project, sink_id).to_dict())
                    if method == "DELETE":
                        self.provider.delete_sink(project, sink_id)
                        return self._json({})
                    if method == "PATCH":
                        body = parse_json_body(request.get_data())
                        sink = self.provider.update_sink(
                            project,
                            sink_id,
                            destination=body.get("destination"),
                            filter_expr=body.get("filter"),
                        )
                        return self._json(sink.to_dict())

        raise GcpNotFound(f"unknown path: {path}")

    @staticmethod
    def _json(payload: dict, status: int = 200) -> Response:
        return Response(json.dumps(payload), status=status, mimetype="application/json")
