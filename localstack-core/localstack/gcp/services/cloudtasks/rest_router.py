from __future__ import annotations

import json

from werkzeug.wrappers import Request, Response

from localstack.gcp.exceptions import GcpError, GcpInvalidRequest, GcpNotFound
from localstack.gcp.serializers import parse_json_body, serialize_error
from localstack.gcp.services.cloudtasks.provider import CloudTasksProvider


class CloudTasksRouter:
    def __init__(self, *, provider: CloudTasksProvider) -> None:
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
        if not path.startswith("/v2/projects/"):
            raise GcpNotFound(f"unknown path: {path}")
        rest = path[len("/v2/projects/") :]
        parts = rest.split("/")
        if len(parts) < 4 or parts[1] != "locations" or parts[3] != "queues":
            raise GcpNotFound(f"unknown path: {path}")
        project, location = parts[0], parts[2]

        if len(parts) == 4:
            if method == "POST":
                queue_id = request.args.get("queueId")
                if not queue_id:
                    body = parse_json_body(request.get_data()) if request.get_data() else {}
                    name = body.get("name") or ""
                    queue_id = name.rsplit("/", 1)[-1] if name else None
                if not queue_id:
                    raise GcpInvalidRequest("queueId or name required")
                q = self.provider.create_queue(project, location, queue_id)
                return self._json(q.to_dict())
            if method == "GET":
                qs = self.provider.list_queues(project, location)
                return self._json({"queues": [q.to_dict() for q in qs]})
            raise GcpInvalidRequest(f"method {method} not allowed on /queues")

        queue_segment = parts[4]
        if ":" in queue_segment:
            queue_id, action = queue_segment.split(":", 1)
            return self._queue_action(method, project, location, queue_id, action)
        queue_id = queue_segment

        if len(parts) == 5:
            if method == "GET":
                return self._json(
                    self.provider.get_queue(project, location, queue_id).to_dict()
                )
            if method == "DELETE":
                self.provider.delete_queue(project, location, queue_id)
                return self._json({})
            raise GcpInvalidRequest(f"method {method} not allowed on queue")

        if parts[5] != "tasks":
            raise GcpNotFound(f"unknown segment: {parts[5]}")

        if len(parts) == 6:
            if method == "POST":
                body = parse_json_body(request.get_data())
                task = body.get("task", {}) or {}
                tname = task.get("name") or ""
                tid = tname.rsplit("/", 1)[-1] if tname else None
                t = self.provider.create_task(
                    project,
                    location,
                    queue_id,
                    task_id=tid,
                    http_request=task.get("httpRequest"),
                    schedule_time=task.get("scheduleTime"),
                )
                return self._json(t.to_dict())
            if method == "GET":
                tasks = self.provider.list_tasks(project, location, queue_id)
                return self._json({"tasks": [t.to_dict() for t in tasks]})
            raise GcpInvalidRequest(f"method {method} not allowed on /tasks")

        task_segment = parts[6]
        if ":" in task_segment:
            task_id, action = task_segment.split(":", 1)
            if method != "POST":
                raise GcpInvalidRequest(f"method {method} not allowed for action {action}")
            if action == "run":
                t = self.provider.run_task(project, location, queue_id, task_id)
                return self._json(t.to_dict())
            raise GcpInvalidRequest(f"unknown action: {action}")

        task_id = task_segment
        if method == "GET":
            return self._json(
                self.provider.get_task(project, location, queue_id, task_id).to_dict()
            )
        if method == "DELETE":
            self.provider.delete_task(project, location, queue_id, task_id)
            return self._json({})
        raise GcpInvalidRequest(f"method {method} not allowed on task")

    def _queue_action(
        self, method: str, project: str, location: str, queue_id: str, action: str
    ) -> Response:
        if method != "POST":
            raise GcpInvalidRequest(f"method {method} not allowed for action {action}")
        if action == "pause":
            q = self.provider.pause_queue(project, location, queue_id)
            return self._json(q.to_dict())
        if action == "resume":
            q = self.provider.resume_queue(project, location, queue_id)
            return self._json(q.to_dict())
        raise GcpInvalidRequest(f"unknown action: {action}")

    @staticmethod
    def _json(payload: dict, status: int = 200) -> Response:
        return Response(json.dumps(payload), status=status, mimetype="application/json")
