"""Azure Queue Storage REST adapter (subset of REST API 2023-11-03)."""

from __future__ import annotations

from uuid import uuid4
from xml.etree import ElementTree as ET

from werkzeug.wrappers import Request, Response

from localstack.azure.exceptions import AzureNotFound
from localstack.azure.services.storage.provider import MicrosoftStorageProvider

X_MS_VERSION = "2023-11-03"


def _with_headers(resp: Response) -> Response:
    resp.headers["x-ms-version"] = X_MS_VERSION
    resp.headers["x-ms-request-id"] = str(uuid4())
    return resp


def _xml_error(code: str, message: str, status: int) -> Response:
    root = ET.Element("Error")
    ET.SubElement(root, "Code").text = code
    ET.SubElement(root, "Message").text = message
    body = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    return _with_headers(Response(body, status=status, mimetype="application/xml"))


def _xml_response(root: ET.Element, status: int = 200) -> Response:
    body = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    return _with_headers(Response(body, status=status, mimetype="application/xml"))


class QueueRouter:
    """WSGI router for Azure Queue Storage data-plane operations.

    Path layout (host-based routing not yet wired): /{account}/{queue}[/messages[/{id}]]
    """

    def __init__(self, provider: MicrosoftStorageProvider) -> None:
        self.provider = provider

    def __call__(self, environ, start_response):
        request = Request(environ)
        response = self._dispatch(request)
        return response(environ, start_response)

    def _dispatch(self, request: Request) -> Response:
        parts = request.path.strip("/").split("/")
        if len(parts) < 2:
            return _xml_error("InvalidUri", "expected /{account}/{queue}[...]", 400)
        account = parts[0]
        queue = parts[1]
        tail = parts[2:]

        try:
            if not tail:
                return self._queue_op(request, account, queue)
            if tail[0] == "messages" and len(tail) == 1:
                return self._messages_op(request, account, queue)
            if tail[0] == "messages" and len(tail) == 2:
                return self._message_op(request, account, queue, message_id=tail[1])
        except AzureNotFound as exc:
            return _xml_error(self._notfound_code(exc), str(exc), 404)

        return _xml_error("InvalidUri", "unsupported queue path", 400)

    # -- queue ops --

    def _queue_op(self, request: Request, account: str, queue: str) -> Response:
        if request.method == "PUT":
            existing = self.provider.data_store.ensure_account(account).queues
            if queue in existing:
                return _with_headers(Response(status=204))
            self.provider.create_queue(account, queue)
            return _with_headers(Response(status=201))
        if request.method == "DELETE":
            try:
                self.provider.delete_queue(account, queue)
            except AzureNotFound as exc:
                return _xml_error("QueueNotFound", str(exc), 404)
            return _with_headers(Response(status=204))
        return _xml_error("MethodNotAllowed", f"{request.method} not supported", 405)

    # -- messages collection --

    def _messages_op(self, request: Request, account: str, queue: str) -> Response:
        if request.method == "POST":
            text = self._parse_enqueue_body(request.get_data(as_text=True))
            if text is None:
                return _xml_error("InvalidXmlDocument", "invalid QueueMessage XML", 400)
            try:
                msg = self.provider.send_message(account, queue, text)
            except AzureNotFound as exc:
                return _xml_error("QueueNotFound", str(exc), 404)
            root = ET.Element("QueueMessagesList")
            self._append_message(root, msg, include_text=False)
            return _xml_response(root, status=201)
        if request.method == "GET":
            try:
                num = int(request.args.get("numofmessages", "1"))
            except ValueError:
                return _xml_error("InvalidQueryParameter", "numofmessages must be integer", 400)
            try:
                msgs = self.provider.receive_messages(account, queue, num_messages=num)
            except AzureNotFound as exc:
                return _xml_error("QueueNotFound", str(exc), 404)
            root = ET.Element("QueueMessagesList")
            for m in msgs:
                self._append_message(root, m, include_text=True)
            return _xml_response(root, status=200)
        return _xml_error("MethodNotAllowed", f"{request.method} not supported", 405)

    # -- single message --

    def _message_op(
        self, request: Request, account: str, queue: str, *, message_id: str
    ) -> Response:
        if request.method == "DELETE":
            receipt = request.args.get("popreceipt")
            if not receipt:
                return _xml_error("MissingRequiredParameter", "popreceipt required", 400)
            try:
                self.provider.delete_message(account, queue, message_id, receipt)
            except AzureNotFound as exc:
                code = "MessageNotFound" if "message" in str(exc).lower() else "QueueNotFound"
                return _xml_error(code, str(exc), 404)
            return _with_headers(Response(status=204))
        return _xml_error("MethodNotAllowed", f"{request.method} not supported", 405)

    # -- helpers --

    @staticmethod
    def _parse_enqueue_body(body: str) -> str | None:
        if not body:
            return None
        try:
            root = ET.fromstring(body)
        except ET.ParseError:
            return None
        if root.tag != "QueueMessage":
            return None
        return root.findtext("MessageText") or ""

    @staticmethod
    def _append_message(parent: ET.Element, msg, *, include_text: bool) -> None:
        node = ET.SubElement(parent, "QueueMessage")
        ET.SubElement(node, "MessageId").text = msg.message_id
        ET.SubElement(node, "InsertionTime").text = msg.insertion_time.isoformat()
        if msg.pop_receipt:
            ET.SubElement(node, "PopReceipt").text = msg.pop_receipt
        ET.SubElement(node, "DequeueCount").text = str(msg.dequeue_count)
        if include_text:
            ET.SubElement(node, "MessageText").text = msg.content

    @staticmethod
    def _notfound_code(exc: AzureNotFound) -> str:
        msg = str(exc).lower()
        if "message" in msg:
            return "MessageNotFound"
        return "QueueNotFound"
