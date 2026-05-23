from __future__ import annotations

import datetime
from typing import Any

from localstack.gcp.exceptions import GcpAlreadyExists, GcpInvalidRequest, GcpNotFound
from localstack.gcp.resource_manager import ResourceManagerProvider
from localstack.gcp.services.scheduler.models import SchedulerDataStore, SchedulerJob
from localstack.gcp.stores import GcpStores


def _now() -> str:
    return datetime.datetime.now(datetime.UTC).isoformat()


def _infer_target(body: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    if "httpTarget" in body:
        return "http", dict(body["httpTarget"])
    if "pubsubTarget" in body:
        return "pubsub", dict(body["pubsubTarget"])
    if "appEngineHttpTarget" in body:
        return "appengine", dict(body["appEngineHttpTarget"])
    return "http", {}


class SchedulerProvider:
    def __init__(
        self,
        *,
        resource_manager: ResourceManagerProvider | None = None,
        stores: GcpStores | None = None,
    ) -> None:
        self.stores = stores or GcpStores()
        self.resource_manager = resource_manager or ResourceManagerProvider(stores=self.stores)
        self.data = SchedulerDataStore()

    def create_job(
        self,
        project: str,
        location: str,
        job_id: str,
        *,
        schedule: str,
        time_zone: str = "Etc/UTC",
        target_type: str = "http",
        target: dict | None = None,
        description: str = "",
    ) -> SchedulerJob:
        if not schedule:
            raise GcpInvalidRequest("schedule (cron) required")
        full = f"projects/{project}/locations/{location}/jobs/{job_id}"
        if full in self.data.jobs:
            raise GcpAlreadyExists(f"job '{full}' already exists")
        self.resource_manager.ensure_project(project)
        job = SchedulerJob(
            name=full,
            schedule=schedule,
            time_zone=time_zone,
            target_type=target_type,
            target=dict(target or {}),
            description=description,
            create_time=_now(),
        )
        self.data.jobs[full] = job
        return job

    def get_job(self, project: str, location: str, job_id: str) -> SchedulerJob:
        full = f"projects/{project}/locations/{location}/jobs/{job_id}"
        job = self.data.jobs.get(full)
        if job is None:
            raise GcpNotFound(f"job '{full}' not found")
        return job

    def list_jobs(self, project: str, location: str) -> list[SchedulerJob]:
        prefix = f"projects/{project}/locations/{location}/jobs/"
        return [j for j in self.data.jobs.values() if j.name.startswith(prefix)]

    def delete_job(self, project: str, location: str, job_id: str) -> None:
        full = f"projects/{project}/locations/{location}/jobs/{job_id}"
        if full not in self.data.jobs:
            raise GcpNotFound(f"job '{full}' not found")
        del self.data.jobs[full]

    def pause_job(self, project: str, location: str, job_id: str) -> SchedulerJob:
        job = self.get_job(project, location, job_id)
        job.state = "PAUSED"
        return job

    def resume_job(self, project: str, location: str, job_id: str) -> SchedulerJob:
        job = self.get_job(project, location, job_id)
        job.state = "ENABLED"
        return job

    def run_job(self, project: str, location: str, job_id: str) -> SchedulerJob:
        job = self.get_job(project, location, job_id)
        if job.state != "ENABLED":
            raise GcpInvalidRequest(f"job '{job.name}' is not enabled (state={job.state})")
        job.attempt_count += 1
        job.last_attempt_time = _now()
        return job

    def patch_job(
        self,
        project: str,
        location: str,
        job_id: str,
        *,
        schedule: str | None = None,
        description: str | None = None,
    ) -> SchedulerJob:
        job = self.get_job(project, location, job_id)
        if schedule is not None:
            job.schedule = schedule
        if description is not None:
            job.description = description
        return job
