from __future__ import annotations

import json

from werkzeug.wrappers import Request, Response

from localstack.gcp.exceptions import GcpError, GcpInvalidRequest, GcpNotFound
from localstack.gcp.serializers import parse_json_body, serialize_error
from localstack.gcp.services.cloudsql.provider import CloudSqlProvider


class CloudSqlRouter:
    def __init__(self, *, provider: CloudSqlProvider) -> None:
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
        if not path.startswith("/sql/v1beta4/projects/"):
            raise GcpNotFound(f"unknown path: {path}")
        rest = path[len("/sql/v1beta4/projects/") :]
        parts = rest.split("/")
        if len(parts) < 2 or parts[1] != "instances":
            raise GcpNotFound(f"unknown path: {path}")
        project = parts[0]

        if len(parts) == 2:
            if method == "POST":
                body = parse_json_body(request.get_data())
                name = body.get("name")
                if not name:
                    raise GcpInvalidRequest("instance name required")
                settings = body.get("settings") or {}
                inst = self.provider.create_instance(
                    project,
                    name,
                    region=body.get("region", "us-central1"),
                    database_version=body.get("databaseVersion", "MYSQL_8_0"),
                    tier=settings.get("tier", "db-n1-standard-1"),
                )
                return self._json(inst.to_dict())
            if method == "GET":
                insts = self.provider.list_instances(project)
                return self._json({"items": [i.to_dict() for i in insts]})
            raise GcpInvalidRequest(f"method {method} not allowed")

        instance = parts[2]
        if len(parts) == 3:
            if method == "GET":
                return self._json(self.provider.get_instance(project, instance).to_dict())
            if method == "DELETE":
                self.provider.delete_instance(project, instance)
                return self._json({})
            if method == "PATCH":
                body = parse_json_body(request.get_data()) if request.get_data() else {}
                settings = body.get("settings") or {}
                inst = self.provider.patch_instance(
                    project, instance, tier=settings.get("tier")
                )
                return self._json(inst.to_dict())
            raise GcpInvalidRequest(f"method {method} not allowed on instance")

        if parts[3] == "databases":
            return self._databases(request, method, project, instance, parts[4:])
        if parts[3] == "users":
            return self._users(request, method, project, instance, parts[4:])

        raise GcpNotFound(f"unknown sub-resource: {parts[3]}")

    def _databases(
        self, request: Request, method: str, project: str, instance: str, sub: list[str]
    ) -> Response:
        if not sub:
            if method == "POST":
                body = parse_json_body(request.get_data())
                name = body.get("name")
                if not name:
                    raise GcpInvalidRequest("database name required")
                db = self.provider.create_database(
                    project, instance, name, charset=body.get("charset", "utf8")
                )
                return self._json(db.to_dict())
            if method == "GET":
                dbs = self.provider.list_databases(project, instance)
                return self._json({"items": [d.to_dict() for d in dbs]})
        if len(sub) == 1:
            database = sub[0]
            if method == "GET":
                return self._json(
                    self.provider.get_database(project, instance, database).to_dict()
                )
            if method == "DELETE":
                self.provider.delete_database(project, instance, database)
                return self._json({})
        raise GcpInvalidRequest("unsupported database operation")

    def _users(
        self, request: Request, method: str, project: str, instance: str, sub: list[str]
    ) -> Response:
        if not sub:
            if method == "POST":
                body = parse_json_body(request.get_data())
                name = body.get("name")
                if not name:
                    raise GcpInvalidRequest("user name required")
                u = self.provider.create_user(
                    project,
                    instance,
                    name,
                    host=body.get("host", "%"),
                    password=body.get("password", ""),
                )
                return self._json(u.to_dict())
            if method == "GET":
                users = self.provider.list_users(project, instance)
                return self._json({"items": [u.to_dict() for u in users]})
            if method == "DELETE":
                name = request.args.get("name")
                host = request.args.get("host", "%")
                if not name:
                    raise GcpInvalidRequest("name query parameter required")
                self.provider.delete_user(project, instance, name, host)
                return self._json({})
        raise GcpInvalidRequest("unsupported user operation")

    @staticmethod
    def _json(payload: dict, status: int = 200) -> Response:
        return Response(json.dumps(payload), status=status, mimetype="application/json")
