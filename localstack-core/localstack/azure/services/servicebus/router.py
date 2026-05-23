"""Azure Service Bus REST adapter (subset of 2022-10-01-preview)."""

from __future__ import annotations

import json
import re

from werkzeug.wrappers import Request, Response

from localstack.azure.exceptions import AzureInvalidRequest, AzureNotFound
from localstack.azure.services.servicebus.provider import MicrosoftServiceBusProvider

_QUEUE_RE = re.compile(r"^/(?P<ns>[^/]+)/queues/(?P<q>[^/]+)$")
_QUEUE_MSG_RE = re.compile(r"^/(?P<ns>[^/]+)/queues/(?P<q>[^/]+)/messages$")
_TOPIC_RE = re.compile(r"^/(?P<ns>[^/]+)/topics/(?P<t>[^/]+)$")
_TOPIC_MSG_RE = re.compile(r"^/(?P<ns>[^/]+)/topics/(?P<t>[^/]+)/messages$")
_SUB_RE = re.compile(r"^/(?P<ns>[^/]+)/topics/(?P<t>[^/]+)/subscriptions/(?P<s>[^/]+)$")
_SUB_MSG_RE = re.compile(
    r"^/(?P<ns>[^/]+)/topics/(?P<t>[^/]+)/subscriptions/(?P<s>[^/]+)/messages$"
)


def _json(payload, status: int = 200) -> Response:
    return Response(json.dumps(payload), status=status, mimetype="application/json")


def _error(code: str, msg: str, status: int) -> Response:
    return _json({"error": {"code": code, "message": msg}}, status=status)


class ServiceBusRouter:
    """Path layout: /{namespace}/(queues|topics)/{name}[/messages] etc."""

    def __init__(self, provider: MicrosoftServiceBusProvider) -> None:
        self.provider = provider

    def __call__(self, environ, start_response):
        request = Request(environ)
        response = self._dispatch(request)
        return response(environ, start_response)

    def _dispatch(self, request: Request) -> Response:
        path = request.path
        try:
            if m := _SUB_MSG_RE.match(path):
                return self._sub_msg(request, m["ns"], m["t"], m["s"])
            if m := _SUB_RE.match(path):
                return self._sub(request, m["ns"], m["t"], m["s"])
            if m := _TOPIC_MSG_RE.match(path):
                return self._topic_msg(request, m["ns"], m["t"])
            if m := _TOPIC_RE.match(path):
                return self._topic(request, m["ns"], m["t"])
            if m := _QUEUE_MSG_RE.match(path):
                return self._queue_msg(request, m["ns"], m["q"])
            if m := _QUEUE_RE.match(path):
                return self._queue(request, m["ns"], m["q"])
        except AzureNotFound as exc:
            return _error("NotFound", str(exc), 404)
        except AzureInvalidRequest as exc:
            return _error("BadRequest", str(exc), 400)
        return _error("NotFound", "unsupported service bus path", 404)

    # -- queues --

    def _queue(self, request: Request, ns: str, q: str) -> Response:
        if request.method == "PUT":
            self.provider.create_queue(ns, q)
            return Response(status=201)
        if request.method == "DELETE":
            self.provider.delete_queue(ns, q)
            return Response(status=204)
        return _error("MethodNotAllowed", f"{request.method} not supported", 405)

    def _queue_msg(self, request: Request, ns: str, q: str) -> Response:
        if request.method == "POST":
            msg = self.provider.send_queue_message(ns, q, _body(request))
            return _json({"messageId": msg.message_id, "body": msg.body}, status=201)
        if request.method == "GET":  # peek-receive
            msg = self.provider.receive_queue_message(ns, q)
            if msg is None:
                return Response(status=204)
            return _json({"messageId": msg.message_id, "body": msg.body})
        return _error("MethodNotAllowed", f"{request.method} not supported", 405)

    # -- topics --

    def _topic(self, request: Request, ns: str, t: str) -> Response:
        if request.method == "PUT":
            self.provider.create_topic(ns, t)
            return Response(status=201)
        return _error("MethodNotAllowed", f"{request.method} not supported", 405)

    def _topic_msg(self, request: Request, ns: str, t: str) -> Response:
        if request.method == "POST":
            msg = self.provider.publish_topic_message(ns, t, _body(request))
            return _json({"messageId": msg.message_id}, status=201)
        return _error("MethodNotAllowed", f"{request.method} not supported", 405)

    def _sub(self, request: Request, ns: str, t: str, s: str) -> Response:
        if request.method == "PUT":
            self.provider.create_subscription(ns, t, s)
            return Response(status=201)
        return _error("MethodNotAllowed", f"{request.method} not supported", 405)

    def _sub_msg(self, request: Request, ns: str, t: str, s: str) -> Response:
        if request.method == "GET":
            msg = self.provider.receive_subscription_message(ns, t, s)
            if msg is None:
                return Response(status=204)
            return _json({"messageId": msg.message_id, "body": msg.body})
        return _error("MethodNotAllowed", f"{request.method} not supported", 405)


def _body(request: Request) -> str:
    return request.get_data(as_text=True)
