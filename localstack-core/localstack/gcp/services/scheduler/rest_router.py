from __future__ import annotations

import json

from werkzeug.wrappers import Request, Response

from localstack.gcp.exceptions import GcpError, GcpInvalidRequest, GcpNotFound
from localstack.gcp.serializers import parse_json_body, serialize_error
from localstack.gcp.services.scheduler.provider import SchedulerProvider, _infer_target


class SchedulerRouter:
    def __init__(self, *, provider: SchedulerProvider) -> None:
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
        if len(parts) < 4 or parts[1] != "locations" or parts[3] != "jobs":
            raise GcpNotFound(f"unknown path: {path}")
        project, location = parts[0], parts[2]

        if len(parts) == 4:
            if method == "POST":
                body = parse_json_body(request.get_data())
                name = body.get("name") or ""
                job_id = name.rsplit("/", 1)[-1] if name else None
                if not job_id:
                    raise GcpInvalidRequest("job name required")
                target_type, target = _infer_target(body)
                job = self.provider.create_job(
                    project,
                    location,
                    job_id,
                    schedule=body.get("schedule", ""),
                    time_zone=body.get("timeZone", "Etc/UTC"),
                    target_type=target_type,
                    target=target,
                    description=body.get("description", ""),
                )
                return self._json(job.to_dict())
            if method == "GET":
                jobs = self.provider.list_jobs(project, location)
                return self._json({"jobs": [j.to_dict() for j in jobs]})
            raise GcpInvalidRequest(f"method {method} not allowed on /jobs")

        job_segment = parts[4]
        if ":" in job_segment:
            job_id, action = job_segment.split(":", 1)
            return self._job_action(method, project, location, job_id, action)

        job_id = job_segment
        if len(parts) == 5:
            if method == "GET":
                return self._json(
                    self.provider.get_job(project, location, job_id).to_dict()
                )
            if method == "DELETE":
                self.provider.delete_job(project, location, job_id)
                return self._json({})
            if method == "PATCH":
                body = parse_json_body(request.get_data()) if request.get_data() else {}
                job = self.provider.patch_job(
                    project,
                    location,
                    job_id,
                    schedule=body.get("schedule"),
                    description=body.get("description"),
                )
                return self._json(job.to_dict())
            raise GcpInvalidRequest(f"method {method} not allowed on job")

        raise GcpNotFound(f"unknown path: {path}")

    def _job_action(
        self, method: str, project: str, location: str, job_id: str, action: str
    ) -> Response:
        if method != "POST":
            raise GcpInvalidRequest(f"method {method} not allowed for action {action}")
        if action == "pause":
            return self._json(self.provider.pause_job(project, location, job_id).to_dict())
        if action == "resume":
            return self._json(self.provider.resume_job(project, location, job_id).to_dict())
        if action == "run":
            return self._json(self.provider.run_job(project, location, job_id).to_dict())
        raise GcpInvalidRequest(f"unknown action: {action}")

    @staticmethod
    def _json(payload: dict, status: int = 200) -> Response:
        return Response(json.dumps(payload), status=status, mimetype="application/json")
