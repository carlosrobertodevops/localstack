from __future__ import annotations

import base64
import json

from werkzeug.wrappers import Request, Response

from localstack.gcp.exceptions import GcpError, GcpInvalidRequest, GcpNotFound
from localstack.gcp.serializers import parse_json_body, serialize_error
from localstack.gcp.services.secretmanager.provider import SecretManagerProvider


class SecretManagerRouter:
    def __init__(self, *, provider: SecretManagerProvider) -> None:
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
        if len(parts) < 2 or parts[1] != "secrets":
            raise GcpNotFound(f"unknown path: {path}")
        project = parts[0]

        if len(parts) == 2:
            if method == "POST":
                secret_id = request.args.get("secretId")
                if not secret_id:
                    raise GcpInvalidRequest("secretId query parameter required")
                body = parse_json_body(request.get_data()) if request.get_data() else {}
                secret = self.provider.create_secret(
                    project,
                    secret_id,
                    labels=body.get("labels"),
                    replication=body.get("replication"),
                )
                return self._json(secret.to_dict())
            if method == "GET":
                secrets = self.provider.list_secrets(project)
                return self._json({"secrets": [s.to_dict() for s in secrets]})
            raise GcpInvalidRequest(f"method {method} not allowed on /secrets")

        secret_segment = parts[2]
        # action suffix: secrets/{id}:action
        if ":" in secret_segment:
            secret_id, action = secret_segment.split(":", 1)
            return self._secret_action(request, method, project, secret_id, action)
        secret_id = secret_segment

        if len(parts) == 3:
            if method == "GET":
                return self._json(self.provider.get_secret(project, secret_id).to_dict())
            if method == "DELETE":
                self.provider.delete_secret(project, secret_id)
                return self._json({})
            raise GcpInvalidRequest(f"method {method} not allowed on secret")

        if parts[3] != "versions":
            raise GcpNotFound(f"unknown segment: {parts[3]}")

        if len(parts) == 4:
            if method == "GET":
                versions = self.provider.list_versions(project, secret_id)
                return self._json({"versions": [v.to_dict() for v in versions]})
            raise GcpInvalidRequest(f"method {method} not allowed on /versions")

        version_segment = parts[4]
        if ":" in version_segment:
            version, action = version_segment.split(":", 1)
            return self._version_action(method, project, secret_id, version, action)

        if method == "GET":
            v = self.provider.get_secret_version(project, secret_id, version_segment)
            return self._json(v.to_dict())
        raise GcpInvalidRequest(f"method {method} not allowed on version")

    def _secret_action(
        self, request: Request, method: str, project: str, secret_id: str, action: str
    ) -> Response:
        if method != "POST":
            raise GcpInvalidRequest(f"method {method} not allowed for action {action}")
        if action == "addVersion":
            body = parse_json_body(request.get_data())
            payload = body.get("payload") or {}
            data_b64 = payload.get("data", "")
            data = base64.b64decode(data_b64) if data_b64 else b""
            v = self.provider.add_secret_version(project, secret_id, data)
            return self._json(v.to_dict())
        raise GcpInvalidRequest(f"unknown action: {action}")

    def _version_action(
        self, method: str, project: str, secret_id: str, version: str, action: str
    ) -> Response:
        if method != "POST" and action != "access":
            raise GcpInvalidRequest(f"method {method} not allowed for action {action}")
        if action == "access":
            v = self.provider.access_secret_version(project, secret_id, version)
            return self._json(
                {
                    "name": v.name,
                    "payload": {"data": base64.b64encode(v.payload_data).decode("ascii")},
                }
            )
        if action == "disable":
            v = self.provider.disable_secret_version(project, secret_id, version)
            return self._json(v.to_dict())
        if action == "enable":
            v = self.provider.enable_secret_version(project, secret_id, version)
            return self._json(v.to_dict())
        if action == "destroy":
            v = self.provider.destroy_secret_version(project, secret_id, version)
            return self._json(v.to_dict())
        raise GcpInvalidRequest(f"unknown action: {action}")

    @staticmethod
    def _json(payload: dict, status: int = 200) -> Response:
        return Response(json.dumps(payload), status=status, mimetype="application/json")
