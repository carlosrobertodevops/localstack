from __future__ import annotations

import datetime
import uuid
from typing import Any

from localstack.gcp.exceptions import GcpAlreadyExists, GcpInvalidRequest, GcpNotFound
from localstack.gcp.resource_manager import ResourceManagerProvider
from localstack.gcp.services.bigquery.models import (
    BigQueryDataset,
    BigQueryDataStore,
    BigQueryJob,
    BigQueryTable,
)
from localstack.gcp.stores import GcpStores


def _now() -> str:
    return datetime.datetime.now(datetime.UTC).isoformat()


class BigQueryProvider:
    def __init__(
        self,
        *,
        resource_manager: ResourceManagerProvider | None = None,
        stores: GcpStores | None = None,
    ) -> None:
        self.stores = stores or GcpStores()
        self.resource_manager = resource_manager or ResourceManagerProvider(stores=self.stores)
        self.data = BigQueryDataStore()

    def create_dataset(
        self,
        project: str,
        dataset_id: str,
        *,
        location: str = "US",
        labels: dict[str, str] | None = None,
    ) -> BigQueryDataset:
        full = f"projects/{project}/datasets/{dataset_id}"
        if full in self.data.datasets:
            raise GcpAlreadyExists(f"dataset '{full}' already exists")
        self.resource_manager.ensure_project(project)
        ds = BigQueryDataset(
            name=full,
            project=project,
            dataset_id=dataset_id,
            location=location,
            labels=dict(labels or {}),
            create_time=_now(),
        )
        self.data.datasets[full] = ds
        return ds

    def get_dataset(self, project: str, dataset_id: str) -> BigQueryDataset:
        full = f"projects/{project}/datasets/{dataset_id}"
        ds = self.data.datasets.get(full)
        if ds is None:
            raise GcpNotFound(f"dataset '{full}' not found")
        return ds

    def list_datasets(self, project: str) -> list[BigQueryDataset]:
        prefix = f"projects/{project}/datasets/"
        return [d for d in self.data.datasets.values() if d.name.startswith(prefix)]

    def delete_dataset(self, project: str, dataset_id: str) -> None:
        full = f"projects/{project}/datasets/{dataset_id}"
        if full not in self.data.datasets:
            raise GcpNotFound(f"dataset '{full}' not found")
        del self.data.datasets[full]
        # also delete tables under it
        prefix = f"{full}/tables/"
        for key in list(self.data.tables):
            if self.data.tables[key].name.startswith(prefix):
                del self.data.tables[key]

    def create_table(
        self,
        project: str,
        dataset_id: str,
        table_id: str,
        *,
        schema: dict[str, Any] | None = None,
    ) -> BigQueryTable:
        self.get_dataset(project, dataset_id)
        full = f"projects/{project}/datasets/{dataset_id}/tables/{table_id}"
        if full in self.data.tables:
            raise GcpAlreadyExists(f"table '{full}' already exists")
        tbl = BigQueryTable(
            name=full,
            project=project,
            dataset_id=dataset_id,
            table_id=table_id,
            schema=schema or {},
            create_time=_now(),
        )
        self.data.tables[full] = tbl
        return tbl

    def get_table(
        self, project: str, dataset_id: str, table_id: str
    ) -> BigQueryTable:
        full = f"projects/{project}/datasets/{dataset_id}/tables/{table_id}"
        tbl = self.data.tables.get(full)
        if tbl is None:
            raise GcpNotFound(f"table '{full}' not found")
        return tbl

    def list_tables(self, project: str, dataset_id: str) -> list[BigQueryTable]:
        self.get_dataset(project, dataset_id)
        prefix = f"projects/{project}/datasets/{dataset_id}/tables/"
        return [t for t in self.data.tables.values() if t.name.startswith(prefix)]

    def delete_table(self, project: str, dataset_id: str, table_id: str) -> None:
        full = f"projects/{project}/datasets/{dataset_id}/tables/{table_id}"
        if full not in self.data.tables:
            raise GcpNotFound(f"table '{full}' not found")
        del self.data.tables[full]

    def insert_table_data(
        self,
        project: str,
        dataset_id: str,
        table_id: str,
        rows: list[dict[str, Any]],
    ) -> int:
        tbl = self.get_table(project, dataset_id, table_id)
        tbl.rows.extend(rows)
        tbl.num_rows += len(rows)
        return len(rows)

    def run_query(self, project: str, query: str) -> BigQueryJob:
        if not query:
            raise GcpInvalidRequest("query must not be empty")
        self.resource_manager.ensure_project(project)
        job_id = uuid.uuid4().hex[:16]
        full = f"projects/{project}/jobs/{job_id}"
        job = BigQueryJob(
            name=full,
            project=project,
            job_id=job_id,
            state="DONE",
            query=query,
            statistics={"query": {"totalRows": "0"}},
        )
        self.data.jobs[full] = job
        return job

    def create_stub_job(self, project: str) -> BigQueryJob:
        self.resource_manager.ensure_project(project)
        job_id = uuid.uuid4().hex[:16]
        full = f"projects/{project}/jobs/{job_id}"
        job = BigQueryJob(name=full, project=project, job_id=job_id, state="DONE")
        self.data.jobs[full] = job
        return job

    def get_job(self, project: str, job_id: str) -> BigQueryJob:
        full = f"projects/{project}/jobs/{job_id}"
        job = self.data.jobs.get(full)
        if job is None:
            raise GcpNotFound(f"job '{full}' not found")
        return job
