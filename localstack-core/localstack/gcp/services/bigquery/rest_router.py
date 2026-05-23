from __future__ import annotations

import json

from werkzeug.wrappers import Request, Response

from localstack.gcp.exceptions import GcpError, GcpInvalidRequest, GcpNotFound
from localstack.gcp.serializers import parse_json_body, serialize_error
from localstack.gcp.services.bigquery.provider import BigQueryProvider


class BigQueryRouter:
    def __init__(self, *, provider: BigQueryProvider) -> None:
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
        if not path.startswith("/bigquery/v2/projects/"):
            raise GcpNotFound(f"unknown path: {path}")
        rest = path[len("/bigquery/v2/projects/") :]
        parts = rest.split("/")
        if not parts:
            raise GcpNotFound(f"unknown path: {path}")
        project = parts[0]

        if len(parts) >= 2 and parts[1] == "jobs":
            return self._jobs(request, method, project, parts[2:])

        if len(parts) >= 2 and parts[1] == "datasets":
            return self._datasets(request, method, project, parts[2:])

        raise GcpNotFound(f"unknown path: {path}")

    def _datasets(
        self, request: Request, method: str, project: str, sub: list[str]
    ) -> Response:
        if not sub:
            if method == "POST":
                body = parse_json_body(request.get_data())
                ref = body.get("datasetReference") or {}
                ds_id = ref.get("datasetId")
                if not ds_id:
                    raise GcpInvalidRequest("datasetReference.datasetId required")
                ds = self.provider.create_dataset(
                    project,
                    ds_id,
                    location=body.get("location", "US"),
                    labels=body.get("labels"),
                )
                return self._json(ds.to_dict())
            if method == "GET":
                datasets = self.provider.list_datasets(project)
                return self._json({"datasets": [d.to_dict() for d in datasets]})
            raise GcpInvalidRequest(f"method {method} not allowed on /datasets")

        dataset_id = sub[0]
        if len(sub) == 1:
            if method == "GET":
                return self._json(self.provider.get_dataset(project, dataset_id).to_dict())
            if method == "DELETE":
                self.provider.delete_dataset(project, dataset_id)
                return self._json({})
            raise GcpInvalidRequest(f"method {method} not allowed on dataset")

        if sub[1] != "tables":
            raise GcpNotFound(f"unknown segment: {sub[1]}")

        if len(sub) == 2:
            if method == "POST":
                body = parse_json_body(request.get_data())
                ref = body.get("tableReference") or {}
                tbl_id = ref.get("tableId")
                if not tbl_id:
                    raise GcpInvalidRequest("tableReference.tableId required")
                tbl = self.provider.create_table(
                    project, dataset_id, tbl_id, schema=body.get("schema")
                )
                return self._json(tbl.to_dict())
            if method == "GET":
                tables = self.provider.list_tables(project, dataset_id)
                return self._json({"tables": [t.to_dict() for t in tables]})
            raise GcpInvalidRequest(f"method {method} not allowed on /tables")

        table_id = sub[2]
        if len(sub) == 3:
            if method == "GET":
                return self._json(
                    self.provider.get_table(project, dataset_id, table_id).to_dict()
                )
            if method == "DELETE":
                self.provider.delete_table(project, dataset_id, table_id)
                return self._json({})
            raise GcpInvalidRequest(f"method {method} not allowed on table")

        if len(sub) == 4 and sub[3] == "insertAll" and method == "POST":
            body = parse_json_body(request.get_data())
            rows = [r.get("json", {}) for r in (body.get("rows") or [])]
            inserted = self.provider.insert_table_data(project, dataset_id, table_id, rows)
            return self._json({"kind": "bigquery#tableDataInsertAllResponse", "inserted": inserted})

        raise GcpNotFound(f"unknown table path")

    def _jobs(
        self, request: Request, method: str, project: str, sub: list[str]
    ) -> Response:
        if not sub:
            if method == "POST":
                body = parse_json_body(request.get_data())
                config = body.get("configuration") or {}
                query_cfg = config.get("query") or {}
                if "query" in query_cfg:
                    job = self.provider.run_query(project, query_cfg["query"])
                else:
                    job = self.provider.create_stub_job(project)
                return self._json(job.to_dict())
            raise GcpInvalidRequest(f"method {method} not allowed on /jobs")

        if len(sub) == 1 and method == "GET":
            return self._json(self.provider.get_job(project, sub[0]).to_dict())

        raise GcpNotFound(f"unknown jobs path")

    @staticmethod
    def _json(payload: dict, status: int = 200) -> Response:
        return Response(json.dumps(payload), status=status, mimetype="application/json")
