"""GCS JSON API router.

Subset of https://cloud.google.com/storage/docs/json_api/v1/buckets endpoints:

| Method | Path                                | Action                |
| ------ | ----------------------------------- | --------------------- |
| POST   | /storage/v1/b?project=PID           | create bucket         |
| GET    | /storage/v1/b?project=PID           | list buckets          |
| GET    | /storage/v1/b/{bucket}              | get bucket            |
| DELETE | /storage/v1/b/{bucket}              | delete bucket         |
| POST   | /upload/storage/v1/b/{bucket}/o?name=N | upload object      |
| GET    | /storage/v1/b/{bucket}/o            | list objects          |
| GET    | /storage/v1/b/{bucket}/o/{object}   | get object metadata   |
| GET    | /storage/v1/b/{bucket}/o/{object}?alt=media | download body |
| DELETE | /storage/v1/b/{bucket}/o/{object}   | delete object         |
"""

from __future__ import annotations

import json
from urllib.parse import unquote

from werkzeug.wrappers import Request, Response

from localstack.gcp.exceptions import GcpError, GcpInvalidRequest, GcpNotFound
from localstack.gcp.serializers import parse_json_body, serialize_error
from localstack.gcp.services.storage.provider import CloudStorageProvider


class StorageJsonRouter:
    def __init__(self, *, provider: CloudStorageProvider) -> None:
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

        if path.startswith("/upload/storage/v1/b/"):
            return self._handle_upload(request, path[len("/upload/storage/v1/b/") :])

        if not path.startswith("/storage/v1/b"):
            raise GcpNotFound(f"unknown path: {path}")

        suffix = path[len("/storage/v1/b") :]
        if suffix == "" or suffix == "/":
            return self._bucket_collection(request, method)

        suffix = suffix.lstrip("/")
        parts = suffix.split("/", 2)
        bucket = unquote(parts[0])

        if len(parts) == 1:
            return self._bucket_item(method, bucket)

        if parts[1] == "o":
            if len(parts) == 2 or parts[2] == "":
                return self._object_collection(request, method, bucket)
            object_name = unquote(parts[2])
            return self._object_item(request, method, bucket, object_name)

        raise GcpNotFound(f"unknown path: {path}")

    # bucket collection
    def _bucket_collection(self, request: Request, method: str) -> Response:
        if method == "POST":
            project = request.args.get("project")
            if not project:
                raise GcpInvalidRequest("query parameter 'project' is required")
            body = parse_json_body(request.get_data())
            name = body.get("name")
            if not name:
                raise GcpInvalidRequest("'name' is required in body")
            bucket = self.provider.create_bucket(
                project=project,
                name=name,
                location=body.get("location", "US"),
                labels=body.get("labels"),
            )
            return Response(json.dumps(bucket.to_dict()), status=200, mimetype="application/json")
        if method == "GET":
            project = request.args.get("project")
            buckets = self.provider.list_buckets(project=project)
            payload = {"kind": "storage#buckets", "items": [b.to_dict() for b in buckets]}
            return Response(json.dumps(payload), status=200, mimetype="application/json")
        raise GcpInvalidRequest(f"method {method} not allowed on /b")

    def _bucket_item(self, method: str, bucket: str) -> Response:
        if method == "GET":
            b = self.provider.get_bucket(bucket)
            return Response(json.dumps(b.to_dict()), status=200, mimetype="application/json")
        if method == "DELETE":
            self.provider.delete_bucket(bucket)
            return Response(status=204)
        raise GcpInvalidRequest(f"method {method} not allowed on bucket item")

    def _object_collection(self, request: Request, method: str, bucket: str) -> Response:
        if method == "GET":
            prefix = request.args.get("prefix")
            objs = self.provider.list_objects(bucket, prefix=prefix)
            payload = {"kind": "storage#objects", "items": [o.to_dict() for o in objs]}
            return Response(json.dumps(payload), status=200, mimetype="application/json")
        raise GcpInvalidRequest(f"method {method} not allowed on /o")

    def _object_item(self, request: Request, method: str, bucket: str, object_name: str) -> Response:
        if method == "GET":
            obj = self.provider.get_object(bucket, object_name)
            if request.args.get("alt") == "media":
                resp = Response(obj.content, status=200, mimetype=obj.content_type)
                resp.headers["x-goog-generation"] = str(obj.generation)
                return resp
            return Response(json.dumps(obj.to_dict()), status=200, mimetype="application/json")
        if method == "DELETE":
            self.provider.delete_object(bucket, object_name)
            return Response(status=204)
        raise GcpInvalidRequest(f"method {method} not allowed on object item")

    def _handle_upload(self, request: Request, suffix: str) -> Response:
        # suffix: "{bucket}/o" — name comes from query string
        parts = suffix.split("/", 1)
        if len(parts) < 2 or parts[1] != "o":
            raise GcpInvalidRequest(f"upload path invalid: {request.path}")
        bucket = unquote(parts[0])
        if request.method.upper() != "POST":
            raise GcpInvalidRequest("upload requires POST")
        name = request.args.get("name")
        if not name:
            raise GcpInvalidRequest("query parameter 'name' is required for upload")
        content_type = request.headers.get("Content-Type", "application/octet-stream")
        obj = self.provider.put_object(
            bucket, name, request.get_data(), content_type=content_type
        )
        return Response(json.dumps(obj.to_dict()), status=200, mimetype="application/json")
