from __future__ import annotations

import datetime
import uuid
from typing import Any

from localstack.gcp.exceptions import GcpAlreadyExists, GcpInvalidRequest, GcpNotFound
from localstack.gcp.resource_manager import ResourceManagerProvider
from localstack.gcp.services.cloudtasks.models import (
    CloudTask,
    CloudTasksDataStore,
    Queue,
)
from localstack.gcp.stores import GcpStores


def _now() -> str:
    return datetime.datetime.now(datetime.UTC).isoformat()


class CloudTasksProvider:
    def __init__(
        self,
        *,
        resource_manager: ResourceManagerProvider | None = None,
        stores: GcpStores | None = None,
    ) -> None:
        self.stores = stores or GcpStores()
        self.resource_manager = resource_manager or ResourceManagerProvider(stores=self.stores)
        self.data = CloudTasksDataStore()

    def create_queue(self, project: str, location: str, queue_id: str) -> Queue:
        full = f"projects/{project}/locations/{location}/queues/{queue_id}"
        if full in self.data.queues:
            raise GcpAlreadyExists(f"queue '{full}' already exists")
        self.resource_manager.ensure_project(project)
        q = Queue(name=full)
        self.data.queues[full] = q
        return q

    def get_queue(self, project: str, location: str, queue_id: str) -> Queue:
        full = f"projects/{project}/locations/{location}/queues/{queue_id}"
        q = self.data.queues.get(full)
        if q is None:
            raise GcpNotFound(f"queue '{full}' not found")
        return q

    def list_queues(self, project: str, location: str) -> list[Queue]:
        prefix = f"projects/{project}/locations/{location}/queues/"
        return [q for q in self.data.queues.values() if q.name.startswith(prefix)]

    def delete_queue(self, project: str, location: str, queue_id: str) -> None:
        full = f"projects/{project}/locations/{location}/queues/{queue_id}"
        if full not in self.data.queues:
            raise GcpNotFound(f"queue '{full}' not found")
        del self.data.queues[full]

    def pause_queue(self, project: str, location: str, queue_id: str) -> Queue:
        q = self.get_queue(project, location, queue_id)
        q.state = "PAUSED"
        return q

    def resume_queue(self, project: str, location: str, queue_id: str) -> Queue:
        q = self.get_queue(project, location, queue_id)
        q.state = "RUNNING"
        return q

    def create_task(
        self,
        project: str,
        location: str,
        queue_id: str,
        *,
        task_id: str | None = None,
        http_request: dict[str, Any] | None = None,
        schedule_time: str | None = None,
    ) -> CloudTask:
        q = self.get_queue(project, location, queue_id)
        tid = task_id or uuid.uuid4().hex
        full = f"{q.name}/tasks/{tid}"
        if full in q.tasks:
            raise GcpAlreadyExists(f"task '{full}' already exists")
        task = CloudTask(
            name=full,
            http_request=http_request or {},
            schedule_time=schedule_time or _now(),
        )
        q.tasks[full] = task
        return task

    def get_task(
        self, project: str, location: str, queue_id: str, task_id: str
    ) -> CloudTask:
        q = self.get_queue(project, location, queue_id)
        full = f"{q.name}/tasks/{task_id}"
        task = q.tasks.get(full)
        if task is None:
            raise GcpNotFound(f"task '{full}' not found")
        return task

    def list_tasks(
        self, project: str, location: str, queue_id: str
    ) -> list[CloudTask]:
        q = self.get_queue(project, location, queue_id)
        return list(q.tasks.values())

    def delete_task(
        self, project: str, location: str, queue_id: str, task_id: str
    ) -> None:
        q = self.get_queue(project, location, queue_id)
        full = f"{q.name}/tasks/{task_id}"
        if full not in q.tasks:
            raise GcpNotFound(f"task '{full}' not found")
        del q.tasks[full]

    def run_task(
        self, project: str, location: str, queue_id: str, task_id: str
    ) -> CloudTask:
        task = self.get_task(project, location, queue_id, task_id)
        task.dispatch_count += 1
        task.state = "DISPATCHED"
        return task
