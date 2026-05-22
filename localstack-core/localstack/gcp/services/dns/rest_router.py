from __future__ import annotations

import json

from werkzeug.wrappers import Request, Response

from localstack.gcp.exceptions import GcpError, GcpInvalidRequest, GcpNotFound
from localstack.gcp.serializers import parse_json_body, serialize_error
from localstack.gcp.services.dns.provider import DnsProvider


class DnsRouter:
    def __init__(self, *, provider: DnsProvider) -> None:
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
        if not path.startswith("/dns/v1/projects/"):
            raise GcpNotFound(f"unknown path: {path}")
        rest = path[len("/dns/v1/projects/") :]
        parts = rest.split("/")
        if len(parts) < 2 or parts[1] != "managedZones":
            raise GcpNotFound(f"unknown path: {path}")
        project = parts[0]

        if len(parts) == 2:
            if method == "POST":
                body = parse_json_body(request.get_data())
                name = body.get("name")
                if not name:
                    raise GcpInvalidRequest("name required")
                zone = self.provider.create_zone(
                    project,
                    name,
                    dns_name=body.get("dnsName", ""),
                    description=body.get("description", ""),
                    visibility=body.get("visibility", "public"),
                )
                return self._json(zone.to_dict())
            if method == "GET":
                zones = self.provider.list_zones(project)
                return self._json({"managedZones": [z.to_dict() for z in zones]})
            raise GcpInvalidRequest(f"method {method} not allowed")

        zone_name = parts[2]
        if len(parts) == 3:
            if method == "GET":
                return self._json(self.provider.get_zone(project, zone_name).to_dict())
            if method == "DELETE":
                self.provider.delete_zone(project, zone_name)
                return self._json({})
            raise GcpInvalidRequest(f"method {method} not allowed on zone")

        if parts[3] == "rrsets" and len(parts) == 4 and method == "GET":
            rrsets = self.provider.list_rrsets(project, zone_name)
            return self._json({"rrsets": [r.to_dict() for r in rrsets]})

        if parts[3] == "changes" and len(parts) == 4 and method == "POST":
            body = parse_json_body(request.get_data())
            change = self.provider.apply_changes(
                project,
                zone_name,
                additions=body.get("additions") or [],
                deletions=body.get("deletions") or [],
            )
            return self._json(change)

        raise GcpNotFound(f"unknown sub-path: {path}")

    @staticmethod
    def _json(payload: dict, status: int = 200) -> Response:
        return Response(json.dumps(payload), status=status, mimetype="application/json")
