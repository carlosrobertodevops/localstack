from __future__ import annotations

import json

from werkzeug.wrappers import Request, Response

from localstack.gcp.exceptions import GcpError, GcpInvalidRequest, GcpNotFound
from localstack.gcp.serializers import parse_json_body, serialize_error
from localstack.gcp.services.memorystore.provider import MemorystoreProvider


class MemorystoreRouter:
    def __init__(self, *, provider: MemorystoreProvider) -> None:
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
        if not path.startswith("/v1/projects/"):
            raise GcpNotFound(f"unknown path: {path}")
        rest = path[len("/v1/projects/") :]
        parts = rest.split("/")
        if len(parts) < 4 or parts[1] != "locations" or parts[3] != "instances":
            raise GcpNotFound(f"unknown path: {path}")
        project, location = parts[0], parts[2]

        if len(parts) == 4:
            if method == "POST":
                instance_id = request.args.get("instanceId")
                if not instance_id:
                    raise GcpInvalidRequest("instanceId required")
                body = parse_json_body(request.get_data())
                inst = self.provider.create_instance(
                    project,
                    location,
                    instance_id,
                    tier=body.get("tier", "BASIC"),
                    memory_size_gb=int(body.get("memorySizeGb", 1)),
                    redis_version=body.get("redisVersion", "REDIS_7_0"),
                    authorized_network=body.get("authorizedNetwork", ""),
                    auth_enabled=bool(body.get("authEnabled", False)),
                    labels=body.get("labels"),
                )
                return self._json(inst.to_dict())
            if method == "GET":
                insts = self.provider.list_instances(project, location)
                return self._json({"instances": [i.to_dict() for i in insts]})
            raise GcpInvalidRequest(f"method {method} not allowed")

        instance_segment = parts[4]
        if ":" in instance_segment:
            instance_id, action = instance_segment.split(":", 1)
            return self._instance_action(method, project, location, instance_id, action)

        instance_id = instance_segment
        if len(parts) == 5:
            if method == "GET":
                return self._json(
                    self.provider.get_instance(project, location, instance_id).to_dict()
                )
            if method == "DELETE":
                self.provider.delete_instance(project, location, instance_id)
                return self._json({})
            if method == "PATCH":
                body = parse_json_body(request.get_data()) if request.get_data() else {}
                inst = self.provider.patch_instance(
                    project,
                    location,
                    instance_id,
                    memory_size_gb=int(body["memorySizeGb"]) if "memorySizeGb" in body else None,
                    labels=body.get("labels"),
                )
                return self._json(inst.to_dict())
            raise GcpInvalidRequest(f"method {method} not allowed on instance")

        raise GcpNotFound(f"unknown path: {path}")

    def _instance_action(
        self, method: str, project: str, location: str, instance_id: str, action: str
    ) -> Response:
        if method != "POST":
            raise GcpInvalidRequest(f"method {method} not allowed for action {action}")
        if action == "failover":
            inst = self.provider.failover(project, location, instance_id)
            return self._json(inst.to_dict())
        raise GcpInvalidRequest(f"unknown action: {action}")

    @staticmethod
    def _json(payload: dict, status: int = 200) -> Response:
        return Response(json.dumps(payload), status=status, mimetype="application/json")
