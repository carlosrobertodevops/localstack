from __future__ import annotations

import json

from werkzeug.wrappers import Request, Response

from localstack.gcp.exceptions import GcpError, GcpInvalidRequest, GcpNotFound
from localstack.gcp.serializers import parse_json_body, serialize_error
from localstack.gcp.services.cloudrun.provider import CloudRunProvider


def _extract_template(body: dict) -> tuple[str, dict[str, str]]:
    template = body.get("template") or {}
    containers = template.get("containers") or []
    if not containers:
        return "", {}
    c0 = containers[0]
    image = c0.get("image", "")
    env_list = c0.get("env") or []
    env = {e["name"]: e.get("value", "") for e in env_list if "name" in e}
    return image, env


class CloudRunRouter:
    def __init__(self, *, provider: CloudRunProvider) -> None:
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
        if len(parts) < 4 or parts[1] != "locations" or parts[3] != "services":
            raise GcpNotFound(f"unknown path: {path}")
        project, location = parts[0], parts[2]

        if len(parts) == 4:
            if method == "POST":
                service_id = request.args.get("serviceId")
                if not service_id:
                    raise GcpInvalidRequest("serviceId required")
                body = parse_json_body(request.get_data()) if request.get_data() else {}
                image, env = _extract_template(body)
                svc = self.provider.create_service(
                    project, location, service_id, image=image, env=env
                )
                return self._json(svc.to_dict())
            if method == "GET":
                svcs = self.provider.list_services(project, location)
                return self._json({"services": [s.to_dict() for s in svcs]})
            raise GcpInvalidRequest(f"method {method} not allowed on /services")

        service_segment = parts[4]
        if ":" in service_segment:
            service_id, action = service_segment.split(":", 1)
            return self._service_action(request, method, project, location, service_id, action)
        service_id = service_segment

        if len(parts) == 5:
            if method == "GET":
                return self._json(
                    self.provider.get_service(project, location, service_id).to_dict()
                )
            if method == "PATCH":
                body = parse_json_body(request.get_data()) if request.get_data() else {}
                image, env = _extract_template(body)
                svc = self.provider.update_service(
                    project,
                    location,
                    service_id,
                    image=image or None,
                    env=env or None,
                )
                return self._json(svc.to_dict())
            if method == "DELETE":
                self.provider.delete_service(project, location, service_id)
                return self._json({})
            raise GcpInvalidRequest(f"method {method} not allowed on service")

        if parts[5] != "revisions":
            raise GcpNotFound(f"unknown segment: {parts[5]}")

        if len(parts) == 6 and method == "GET":
            revs = self.provider.list_revisions(project, location, service_id)
            return self._json({"revisions": [r.to_dict() for r in revs]})

        if len(parts) == 7:
            rev_name = f"projects/{project}/locations/{location}/services/{service_id}/revisions/{parts[6]}"
            if method == "GET":
                return self._json(self.provider.get_revision(rev_name).to_dict())
            if method == "DELETE":
                self.provider.delete_revision(rev_name)
                return self._json({})

        raise GcpNotFound(f"unknown path: {path}")

    def _service_action(
        self,
        request: Request,
        method: str,
        project: str,
        location: str,
        service_id: str,
        action: str,
    ) -> Response:
        if method != "POST":
            raise GcpInvalidRequest(f"method {method} not allowed for action {action}")
        body = parse_json_body(request.get_data()) if request.get_data() else {}
        if action == "updateTraffic":
            svc = self.provider.update_traffic(
                project, location, service_id, body.get("traffic", [])
            )
            return self._json(svc.to_dict())
        raise GcpInvalidRequest(f"unknown action: {action}")

    @staticmethod
    def _json(payload: dict, status: int = 200) -> Response:
        return Response(json.dumps(payload), status=status, mimetype="application/json")
