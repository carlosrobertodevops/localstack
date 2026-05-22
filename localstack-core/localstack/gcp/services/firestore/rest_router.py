"""Firestore REST router (minimal).

| Method | Path                                                                            | Action     |
| ------ | ------------------------------------------------------------------------------- | ---------- |
| POST   | /v1/projects/{p}/databases?databaseId=ID                                        | create db  |
| GET    | /v1/projects/{p}/databases/{d}                                                  | get db     |
| POST   | /v1/projects/{p}/databases/{d}/documents/{coll}?documentId=ID                   | create doc |
| GET    | /v1/projects/{p}/databases/{d}/documents/{coll}                                 | list docs  |
| GET    | /v1/projects/{p}/databases/{d}/documents/{coll}/{id}                            | get doc    |
| PATCH  | /v1/projects/{p}/databases/{d}/documents/{coll}/{id}                            | update doc |
| DELETE | /v1/projects/{p}/databases/{d}/documents/{coll}/{id}                            | delete doc |
"""

from __future__ import annotations

import json

from werkzeug.wrappers import Request, Response

from localstack.gcp.exceptions import GcpError, GcpInvalidRequest, GcpNotFound
from localstack.gcp.serializers import parse_json_body, serialize_error
from localstack.gcp.services.firestore.provider import FirestoreProvider


class FirestoreRouter:
    def __init__(self, *, provider: FirestoreProvider) -> None:
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
        if len(parts) < 2 or parts[1] != "databases":
            raise GcpNotFound(f"unknown path: {path}")
        project = parts[0]

        if len(parts) == 2:
            if method == "POST":
                db_id = request.args.get("databaseId") or "(default)"
                body = parse_json_body(request.get_data()) if request.get_data() else {}
                db = self.provider.create_database(project, db_id, location=body.get("locationId", "nam5"))
                return self._json(db.to_dict())
            raise GcpInvalidRequest(f"method {method} not allowed on /databases")

        database_id = parts[2]

        # GET database
        if len(parts) == 3:
            if method == "GET":
                return self._json(self.provider.get_database(project, database_id).to_dict())
            raise GcpInvalidRequest(f"method {method} not allowed on database")

        if parts[3] != "documents":
            raise GcpNotFound(f"unknown segment: {parts[3]}")

        doc_segments = parts[4:]
        return self._documents(request, method, project, database_id, doc_segments)

    def _documents(self, request: Request, method: str, project: str, database_id: str, segments: list[str]) -> Response:
        if not segments:
            raise GcpInvalidRequest("collection required")
        # if odd number of segments → collection path (no document id)
        # if even → document path
        is_collection = len(segments) % 2 == 1

        if is_collection:
            parent_path = "/".join(segments)
            if method == "POST":
                doc_id = request.args.get("documentId")
                body = parse_json_body(request.get_data())
                doc = self.provider.create_document(project, database_id, parent_path, doc_id, body.get("fields") or {})
                return self._json(doc.to_dict())
            if method == "GET":
                docs = self.provider.list_documents(project, database_id, parent_path)
                return self._json({"documents": [d.to_dict() for d in docs]})
            raise GcpInvalidRequest(f"method {method} not allowed on collection")

        # document
        full = f"projects/{project}/databases/{database_id}/documents/" + "/".join(segments)
        if method == "GET":
            return self._json(self.provider.get_document(full).to_dict())
        if method == "PATCH":
            body = parse_json_body(request.get_data())
            doc = self.provider.patch_document(full, body.get("fields") or {})
            return self._json(doc.to_dict())
        if method == "DELETE":
            self.provider.delete_document(full)
            return self._json({})
        raise GcpInvalidRequest(f"method {method} not allowed on document")

    @staticmethod
    def _json(payload: dict, status: int = 200) -> Response:
        return Response(json.dumps(payload), status=status, mimetype="application/json")
