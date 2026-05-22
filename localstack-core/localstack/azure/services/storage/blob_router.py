"""Azure Blob Storage REST adapter (subset of REST API 2023-11-03)."""

from __future__ import annotations

from email.utils import format_datetime
from uuid import uuid4
from xml.etree import ElementTree as ET

from werkzeug.wrappers import Request, Response

from localstack.azure.exceptions import AzureNotFound
from localstack.azure.services.storage.provider import MicrosoftStorageProvider

X_MS_VERSION = "2023-11-03"
_META_PREFIX = "x-ms-meta-"


def _xml_error(code: str, message: str, status: int) -> Response:
    root = ET.Element("Error")
    ET.SubElement(root, "Code").text = code
    ET.SubElement(root, "Message").text = message
    body = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    return _with_headers(Response(body, status=status, mimetype="application/xml"))


def _with_headers(resp: Response) -> Response:
    resp.headers["x-ms-version"] = X_MS_VERSION
    resp.headers["x-ms-request-id"] = str(uuid4())
    return resp


def _metadata_from_headers(headers) -> dict[str, str]:
    out: dict[str, str] = {}
    for k, v in headers.items():
        if k.lower().startswith(_META_PREFIX):
            out[k[len(_META_PREFIX) :]] = v
    return out


def _add_metadata_headers(resp: Response, metadata: dict[str, str]) -> None:
    for k, v in metadata.items():
        resp.headers[f"{_META_PREFIX}{k}"] = v


class BlobRouter:
    """WSGI router for Azure Blob Storage data-plane operations.

    Path layout (host-based routing not yet wired): /{account}/{container}[/{blob}]
    """

    def __init__(self, provider: MicrosoftStorageProvider) -> None:
        self.provider = provider

    def __call__(self, environ, start_response):
        request = Request(environ)
        response = self._dispatch(request)
        return response(environ, start_response)

    def _dispatch(self, request: Request) -> Response:
        path = request.path.strip("/")
        if not path:
            return _xml_error("InvalidUri", "missing account in path", 400)
        parts = path.split("/", 2)
        account = parts[0]
        container = parts[1] if len(parts) > 1 else None
        blob = parts[2] if len(parts) > 2 else None

        restype = request.args.get("restype")
        comp = request.args.get("comp")

        try:
            if blob is None and container is not None and restype == "container":
                return self._container_op(request, account, container, comp)
            if blob is not None:
                return self._blob_op(request, account, container, blob)
        except AzureNotFound as exc:
            return _xml_error(self._notfound_code(exc), str(exc), 404)

        return _xml_error("InvalidUri", "unsupported request shape", 400)

    # -- container ops --

    def _container_op(
        self, request: Request, account: str, container: str, comp: str | None
    ) -> Response:
        if request.method == "PUT":
            existing = self.provider.data_store.ensure_account(account).containers
            if container in existing:
                return _xml_error("ContainerAlreadyExists", "container exists", 409)
            self.provider.create_container(
                account, container, metadata=_metadata_from_headers(request.headers)
            )
            return _with_headers(Response(status=201))
        if request.method == "DELETE":
            try:
                self.provider.delete_container(account, container)
            except AzureNotFound as exc:
                return _xml_error("ContainerNotFound", str(exc), 404)
            return _with_headers(Response(status=202))
        if request.method == "GET" and comp == "list":
            try:
                blobs = self.provider.list_blobs(
                    account, container, prefix=request.args.get("prefix") or None
                )
            except AzureNotFound as exc:
                return _xml_error("ContainerNotFound", str(exc), 404)
            xml = self._list_blobs_xml(container, blobs, request.args.get("prefix") or "")
            return _with_headers(Response(xml, status=200, mimetype="application/xml"))
        return _xml_error("MethodNotAllowed", f"{request.method} not supported", 405)

    # -- blob ops --

    def _blob_op(self, request: Request, account: str, container: str, blob: str) -> Response:
        if request.method == "PUT":
            if request.headers.get("x-ms-blob-type") != "BlockBlob":
                return _xml_error(
                    "MissingRequiredHeader", "x-ms-blob-type=BlockBlob required", 400
                )
            try:
                self.provider.get_container(account, container)
            except AzureNotFound as exc:
                return _xml_error("ContainerNotFound", str(exc), 404)
            saved = self.provider.put_blob(
                account,
                container,
                blob,
                request.get_data(),
                metadata=_metadata_from_headers(request.headers),
                content_type=request.headers.get("Content-Type"),
            )
            resp = Response(status=201)
            resp.headers["ETag"] = f'"{saved.etag}"'
            resp.headers["Last-Modified"] = format_datetime(saved.last_modified, usegmt=True)
            return _with_headers(resp)

        if request.method in ("GET", "HEAD"):
            try:
                obj = self.provider.get_blob(account, container, blob)
            except AzureNotFound as exc:
                return _xml_error(self._notfound_code(exc), str(exc), 404)
            body = b"" if request.method == "HEAD" else obj.content
            resp = Response(
                body,
                status=200,
                mimetype=obj.content_type or "application/octet-stream",
            )
            resp.headers["Content-Length"] = str(len(obj.content))
            resp.headers["ETag"] = f'"{obj.etag}"'
            resp.headers["Last-Modified"] = format_datetime(obj.last_modified, usegmt=True)
            _add_metadata_headers(resp, obj.metadata)
            return _with_headers(resp)

        if request.method == "DELETE":
            try:
                self.provider.delete_blob(account, container, blob)
            except AzureNotFound as exc:
                return _xml_error(self._notfound_code(exc), str(exc), 404)
            return _with_headers(Response(status=202))

        return _xml_error("MethodNotAllowed", f"{request.method} not supported", 405)

    # -- helpers --

    @staticmethod
    def _list_blobs_xml(container: str, blobs, prefix: str) -> bytes:
        root = ET.Element("EnumerationResults", ContainerName=container)
        if prefix:
            ET.SubElement(root, "Prefix").text = prefix
        blobs_el = ET.SubElement(root, "Blobs")
        for blob in blobs:
            b = ET.SubElement(blobs_el, "Blob")
            ET.SubElement(b, "Name").text = blob.name
            props = ET.SubElement(b, "Properties")
            ET.SubElement(props, "Content-Length").text = str(len(blob.content))
            ET.SubElement(props, "Content-Type").text = blob.content_type or ""
            ET.SubElement(props, "Etag").text = blob.etag or ""
            ET.SubElement(props, "Last-Modified").text = format_datetime(
                blob.last_modified, usegmt=True
            )
        ET.SubElement(root, "NextMarker")
        return ET.tostring(root, encoding="utf-8", xml_declaration=True)

    @staticmethod
    def _notfound_code(exc: AzureNotFound) -> str:
        msg = str(exc).lower()
        if "blob not found" in msg:
            return "BlobNotFound"
        return "ContainerNotFound"
