"""GCS XML (S3-compatible) router — minimal subset.

| Method | Path                  | Action                       |
| ------ | --------------------- | ---------------------------- |
| PUT    | /{bucket}             | create bucket (needs ?project) |
| GET    | /{bucket}             | list objects (XML)           |
| DELETE | /{bucket}             | delete bucket                |
| PUT    | /{bucket}/{object}    | upload                       |
| GET    | /{bucket}/{object}    | download body                |
| DELETE | /{bucket}/{object}    | delete object                |
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from urllib.parse import unquote

from werkzeug.wrappers import Request, Response

from localstack.gcp.exceptions import GcpError, GcpInvalidRequest, GcpNotFound
from localstack.gcp.services.storage.provider import CloudStorageProvider


def _error_xml(code: str, msg: str, status: int) -> Response:
    root = ET.Element("Error")
    ET.SubElement(root, "Code").text = code
    ET.SubElement(root, "Message").text = msg
    return Response(ET.tostring(root, encoding="utf-8"), status=status, mimetype="application/xml")


class StorageXmlRouter:
    def __init__(self, *, provider: CloudStorageProvider) -> None:
        self.provider = provider

    def __call__(self, environ, start_response):
        request = Request(environ)
        try:
            response = self._dispatch(request)
        except GcpNotFound as exc:
            response = _error_xml("NoSuchKey", str(exc), 404)
        except GcpInvalidRequest as exc:
            response = _error_xml("InvalidRequest", str(exc), 400)
        except GcpError as exc:
            response = _error_xml(exc.code, str(exc), exc.status_code)
        return response(environ, start_response)

    def _dispatch(self, request: Request) -> Response:
        path = request.path.lstrip("/")
        if not path:
            raise GcpInvalidRequest("path required")
        parts = path.split("/", 1)
        bucket = unquote(parts[0])
        rest = unquote(parts[1]) if len(parts) > 1 else ""
        method = request.method.upper()

        if not rest:
            return self._bucket(request, method, bucket)
        return self._object(request, method, bucket, rest)

    def _bucket(self, request: Request, method: str, bucket: str) -> Response:
        if method == "PUT":
            project = request.args.get("project") or request.headers.get("x-goog-project-id", "default")
            self.provider.create_bucket(project=project, name=bucket)
            return Response(status=200)
        if method == "GET":
            prefix = request.args.get("prefix")
            objs = self.provider.list_objects(bucket, prefix=prefix)
            root = ET.Element("ListBucketResult")
            ET.SubElement(root, "Name").text = bucket
            for o in objs:
                contents = ET.SubElement(root, "Contents")
                ET.SubElement(contents, "Key").text = o.name
                ET.SubElement(contents, "Size").text = str(o.size)
                ET.SubElement(contents, "ETag").text = o.etag
            return Response(ET.tostring(root, encoding="utf-8"), status=200, mimetype="application/xml")
        if method == "DELETE":
            self.provider.delete_bucket(bucket)
            return Response(status=204)
        raise GcpInvalidRequest(f"method {method} not allowed on bucket")

    def _object(self, request: Request, method: str, bucket: str, object_name: str) -> Response:
        if method == "PUT":
            ct = request.headers.get("Content-Type", "application/octet-stream")
            self.provider.put_object(bucket, object_name, request.get_data(), content_type=ct)
            return Response(status=200)
        if method == "GET":
            obj = self.provider.get_object(bucket, object_name)
            resp = Response(obj.content, status=200, mimetype=obj.content_type)
            resp.headers["ETag"] = obj.etag
            return resp
        if method == "DELETE":
            self.provider.delete_object(bucket, object_name)
            return Response(status=204)
        raise GcpInvalidRequest(f"method {method} not allowed on object")
