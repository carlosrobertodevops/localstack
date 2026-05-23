"""Pub/Sub REST router.

| Method | Path                                                           | Action          |
| ------ | -------------------------------------------------------------- | --------------- |
| PUT    | /v1/projects/{p}/topics/{t}                                    | create topic    |
| GET    | /v1/projects/{p}/topics/{t}                                    | get topic       |
| DELETE | /v1/projects/{p}/topics/{t}                                    | delete topic    |
| GET    | /v1/projects/{p}/topics                                        | list topics     |
| POST   | /v1/projects/{p}/topics/{t}:publish                            | publish         |
| PUT    | /v1/projects/{p}/subscriptions/{s}                             | create sub      |
| GET    | /v1/projects/{p}/subscriptions/{s}                             | get sub         |
| DELETE | /v1/projects/{p}/subscriptions/{s}                             | delete sub      |
| GET    | /v1/projects/{p}/subscriptions                                 | list subs       |
| POST   | /v1/projects/{p}/subscriptions/{s}:pull                        | pull            |
| POST   | /v1/projects/{p}/subscriptions/{s}:acknowledge                 | ack             |
"""

from __future__ import annotations

import json

from werkzeug.wrappers import Request, Response

from localstack.gcp.exceptions import GcpError, GcpInvalidRequest, GcpNotFound
from localstack.gcp.serializers import parse_json_body, serialize_error
from localstack.gcp.services.pubsub.provider import PubSubProvider


class PubSubRouter:
    def __init__(self, *, provider: PubSubProvider) -> None:
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
        parts = rest.split("/", 2)
        if len(parts) < 2:
            raise GcpNotFound(f"unknown path: {path}")
        project_id, kind = parts[0], parts[1]
        tail = parts[2] if len(parts) > 2 else ""

        if kind == "topics":
            return self._topics(request, method, project_id, tail)
        if kind == "subscriptions":
            return self._subscriptions(request, method, project_id, tail)
        raise GcpNotFound(f"unknown collection: {kind}")

    def _topics(self, request: Request, method: str, project: str, tail: str) -> Response:
        if not tail:
            if method == "GET":
                topics = self.provider.list_topics(project)
                payload = {"topics": [t.to_dict() for t in topics]}
                return self._json(payload)
            raise GcpInvalidRequest(f"method {method} not allowed on topics")

        if ":" in tail:
            topic_id, _, action = tail.partition(":")
            full = f"projects/{project}/topics/{topic_id}"
            if action == "publish" and method == "POST":
                body = parse_json_body(request.get_data())
                ids = self.provider.publish(full, body.get("messages") or [])
                return self._json({"messageIds": ids})
            raise GcpInvalidRequest(f"action {action} unknown")

        full = f"projects/{project}/topics/{tail}"
        if method == "PUT":
            body = parse_json_body(request.get_data()) if request.get_data() else {}
            topic = self.provider.create_topic(full, labels=body.get("labels"))
            return self._json(topic.to_dict())
        if method == "GET":
            return self._json(self.provider.get_topic(full).to_dict())
        if method == "DELETE":
            self.provider.delete_topic(full)
            return self._json({})
        raise GcpInvalidRequest(f"method {method} not allowed on topic")

    def _subscriptions(self, request: Request, method: str, project: str, tail: str) -> Response:
        if not tail:
            if method == "GET":
                subs = self.provider.list_subscriptions(project)
                return self._json({"subscriptions": [s.to_dict() for s in subs]})
            raise GcpInvalidRequest(f"method {method} not allowed on subscriptions")

        if ":" in tail:
            sub_id, _, action = tail.partition(":")
            full = f"projects/{project}/subscriptions/{sub_id}"
            if action == "pull" and method == "POST":
                body = parse_json_body(request.get_data())
                max_m = int(body.get("maxMessages", 10))
                received = self.provider.pull(full, max_messages=max_m)
                return self._json({"receivedMessages": received})
            if action == "acknowledge" and method == "POST":
                body = parse_json_body(request.get_data())
                self.provider.acknowledge(full, body.get("ackIds") or [])
                return self._json({})
            raise GcpInvalidRequest(f"action {action} unknown")

        full = f"projects/{project}/subscriptions/{tail}"
        if method == "PUT":
            body = parse_json_body(request.get_data())
            topic = body.get("topic")
            if not topic:
                raise GcpInvalidRequest("'topic' is required")
            sub = self.provider.create_subscription(
                full, topic, ack_deadline=int(body.get("ackDeadlineSeconds", 10)), labels=body.get("labels")
            )
            return self._json(sub.to_dict())
        if method == "GET":
            return self._json(self.provider.get_subscription(full).to_dict())
        if method == "DELETE":
            self.provider.delete_subscription(full)
            return self._json({})
        raise GcpInvalidRequest(f"method {method} not allowed on subscription")

    @staticmethod
    def _json(payload: dict, status: int = 200) -> Response:
        return Response(json.dumps(payload), status=status, mimetype="application/json")
