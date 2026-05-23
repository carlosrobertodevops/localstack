"""Event Grid REST adapter (subset of 2023-12-15-preview)."""

from __future__ import annotations

import json
import re

from werkzeug.wrappers import Request, Response

from localstack.azure.exceptions import AzureInvalidRequest, AzureNotFound
from localstack.azure.services.eventgrid.provider import MicrosoftEventGridProvider

_TOPIC_RE = re.compile(r"^/topics/(?P<t>[^/]+)$")
_TOPIC_EVENTS_RE = re.compile(r"^/topics/(?P<t>[^/]+):publish$")
_TOPIC_SUBS_RE = re.compile(r"^/topics/(?P<t>[^/]+)/eventSubscriptions$")
_SUB_RE = re.compile(r"^/topics/(?P<t>[^/]+)/eventSubscriptions/(?P<s>[^/]+)$")
_SUB_DELIVERED_RE = re.compile(
    r"^/topics/(?P<t>[^/]+)/eventSubscriptions/(?P<s>[^/]+)/_delivered$"
)


def _json(payload, status: int = 200) -> Response:
    return Response(json.dumps(payload, default=str), status=status, mimetype="application/json")


def _error(code: str, msg: str, status: int) -> Response:
    return _json({"error": {"code": code, "message": msg}}, status=status)


class EventGridRouter:
    """Path layout:
    /topics/{t}
    /topics/{t}:publish
    /topics/{t}/eventSubscriptions
    /topics/{t}/eventSubscriptions/{s}
    /topics/{t}/eventSubscriptions/{s}/_delivered    (testing helper)
    """

    def __init__(self, provider: MicrosoftEventGridProvider) -> None:
        self.provider = provider

    def __call__(self, environ, start_response):
        request = Request(environ)
        response = self._dispatch(request)
        return response(environ, start_response)

    def _dispatch(self, request: Request) -> Response:
        path = request.path
        try:
            if m := _SUB_DELIVERED_RE.match(path):
                return self._delivered(request, m["t"], m["s"])
            if m := _SUB_RE.match(path):
                return self._sub(request, m["t"], m["s"])
            if m := _TOPIC_SUBS_RE.match(path):
                return self._topic_subs(request, m["t"])
            if m := _TOPIC_EVENTS_RE.match(path):
                return self._publish(request, m["t"])
            if m := _TOPIC_RE.match(path):
                return self._topic(request, m["t"])
        except AzureNotFound as exc:
            return _error("NotFound", str(exc), 404)
        except AzureInvalidRequest as exc:
            return _error("BadRequest", str(exc), 400)
        return _error("NotFound", "unsupported event grid path", 404)

    def _topic(self, request: Request, t: str) -> Response:
        if request.method == "PUT":
            self.provider.create_topic(t)
            return Response(status=201)
        if request.method == "DELETE":
            self.provider.delete_topic(t)
            return Response(status=204)
        if request.method == "GET":
            topic = self.provider.get_topic(t)
            return _json({"name": topic.name})
        return _error("MethodNotAllowed", f"{request.method} not supported", 405)

    def _topic_subs(self, request: Request, t: str) -> Response:
        if request.method == "GET":
            subs = self.provider.list_subscriptions(t)
            return _json({"value": [{"name": s.name, "endpoint": s.endpoint} for s in subs]})
        return _error("MethodNotAllowed", f"{request.method} not supported", 405)

    def _sub(self, request: Request, t: str, s: str) -> Response:
        if request.method == "PUT":
            body = _json_body(request)
            endpoint = (body.get("properties") or {}).get("destination", {}).get("endpoint")
            sub = self.provider.create_subscription(t, s, endpoint=endpoint or "")
            return _json({"name": sub.name, "endpoint": sub.endpoint}, status=201)
        if request.method == "DELETE":
            self.provider.delete_subscription(t, s)
            return Response(status=204)
        return _error("MethodNotAllowed", f"{request.method} not supported", 405)

    def _publish(self, request: Request, t: str) -> Response:
        if request.method != "POST":
            return _error("MethodNotAllowed", f"{request.method} not supported", 405)
        body = _json_body(request)
        if not isinstance(body, list):
            return _error("BadRequest", "expected JSON array of events", 400)
        events = self.provider.publish_events(t, body)
        return _json({"count": len(events)}, status=200)

    def _delivered(self, request: Request, t: str, s: str) -> Response:
        if request.method != "GET":
            return _error("MethodNotAllowed", f"{request.method} not supported", 405)
        events = self.provider.delivered_for(t, s)
        return _json(
            {
                "value": [
                    {
                        "id": e.id,
                        "subject": e.subject,
                        "eventType": e.event_type,
                        "data": e.data,
                        "eventTime": e.event_time.isoformat(),
                        "dataVersion": e.data_version,
                    }
                    for e in events
                ]
            }
        )


def _json_body(request: Request):
    raw = request.get_data(as_text=True) or "null"
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise AzureInvalidRequest(f"invalid JSON: {exc.msg}")
