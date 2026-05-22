from __future__ import annotations

import json

from werkzeug.wrappers import Request, Response

from localstack.gcp.exceptions import GcpError, GcpInvalidRequest, GcpNotFound
from localstack.gcp.serializers import parse_json_body, serialize_error
from localstack.gcp.services.spanner.provider import SpannerProvider


class SpannerRouter:
    def __init__(self, *, provider: SpannerProvider) -> None:
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
        if len(parts) < 2 or parts[1] != "instances":
            raise GcpNotFound(f"unknown path: {path}")
        project = parts[0]

        if len(parts) == 2:
            if method == "POST":
                body = parse_json_body(request.get_data())
                instance_id = body.get("instanceId")
                inst_body = body.get("instance") or {}
                if not instance_id:
                    raise GcpInvalidRequest("instanceId required")
                inst = self.provider.create_instance(
                    project,
                    instance_id,
                    config=inst_body.get("config", "projects/_/instanceConfigs/regional-us-central1"),
                    display_name=inst_body.get("displayName", ""),
                    node_count=int(inst_body.get("nodeCount", 1)),
                )
                return self._json(inst.to_dict())
            if method == "GET":
                insts = self.provider.list_instances(project)
                return self._json({"instances": [i.to_dict() for i in insts]})
            raise GcpInvalidRequest(f"method {method} not allowed")

        instance_id = parts[2]
        if len(parts) == 3:
            if method == "GET":
                return self._json(
                    self.provider.get_instance(project, instance_id).to_dict()
                )
            if method == "DELETE":
                self.provider.delete_instance(project, instance_id)
                return self._json({})
            raise GcpInvalidRequest(f"method {method} not allowed on instance")

        if parts[3] != "databases":
            raise GcpNotFound(f"unknown segment: {parts[3]}")

        if len(parts) == 4:
            if method == "POST":
                body = parse_json_body(request.get_data())
                db_id = body.get("createStatement", "").split()[-1].strip("`") if "createStatement" in body else body.get("databaseId")
                if not db_id:
                    raise GcpInvalidRequest("databaseId or createStatement required")
                db = self.provider.create_database(
                    project,
                    instance_id,
                    db_id,
                    extra_statements=body.get("extraStatements"),
                )
                return self._json(db.to_dict())
            if method == "GET":
                dbs = self.provider.list_databases(project, instance_id)
                return self._json({"databases": [d.to_dict() for d in dbs]})

        db_id = parts[4]
        if len(parts) == 5:
            if method == "GET":
                return self._json(
                    self.provider.get_database(project, instance_id, db_id).to_dict()
                )
            if method == "DELETE":
                self.provider.delete_database(project, instance_id, db_id)
                return self._json({})

        if len(parts) == 6 and parts[5] == "ddl" and method == "PATCH":
            body = parse_json_body(request.get_data())
            db = self.provider.update_ddl(
                project, instance_id, db_id, body.get("statements") or []
            )
            return self._json(db.to_dict())

        if parts[5] == "sessions":
            return self._sessions(request, method, project, instance_id, db_id, parts[6:])

        raise GcpNotFound(f"unknown path: {path}")

    def _sessions(
        self,
        request: Request,
        method: str,
        project: str,
        instance_id: str,
        db_id: str,
        sub: list[str],
    ) -> Response:
        if not sub:
            if method == "POST":
                sess = self.provider.create_session(project, instance_id, db_id)
                return self._json(sess.to_dict())
            if method == "GET":
                sessions = self.provider.list_sessions(project, instance_id, db_id)
                return self._json({"sessions": [s.to_dict() for s in sessions]})

        if len(sub) == 1:
            session_segment = sub[0]
            if ":" in session_segment:
                sid, action = session_segment.split(":", 1)
                full_name = f"projects/{project}/instances/{instance_id}/databases/{db_id}/sessions/{sid}"
                if action == "executeSql" and method == "POST":
                    body = parse_json_body(request.get_data())
                    result = self.provider.execute_sql(full_name, body.get("sql", ""))
                    return self._json(result)
                raise GcpInvalidRequest(f"unknown action {action}")
            if method == "DELETE":
                full_name = f"projects/{project}/instances/{instance_id}/databases/{db_id}/sessions/{session_segment}"
                self.provider.delete_session(full_name)
                return self._json({})

        raise GcpNotFound("unknown sessions path")

    @staticmethod
    def _json(payload: dict, status: int = 200) -> Response:
        return Response(json.dumps(payload), status=status, mimetype="application/json")
