from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from localstack.gcp.stores import CaseInsensitiveDict


@dataclass
class BigQueryDataset:
    name: str  # projects/{p}/datasets/{id}
    project: str = ""
    dataset_id: str = ""
    location: str = "US"
    labels: dict[str, str] = field(default_factory=dict)
    create_time: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": "bigquery#dataset",
            "id": f"{self.project}:{self.dataset_id}",
            "datasetReference": {
                "datasetId": self.dataset_id,
                "projectId": self.project,
            },
            "location": self.location,
            "labels": self.labels,
            "creationTime": self.create_time,
        }


@dataclass
class BigQueryTable:
    name: str  # projects/{p}/datasets/{ds}/tables/{id}
    project: str = ""
    dataset_id: str = ""
    table_id: str = ""
    schema: dict[str, Any] = field(default_factory=dict)
    num_rows: int = 0
    create_time: str = ""
    rows: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": "bigquery#table",
            "id": f"{self.project}:{self.dataset_id}.{self.table_id}",
            "tableReference": {
                "projectId": self.project,
                "datasetId": self.dataset_id,
                "tableId": self.table_id,
            },
            "schema": self.schema,
            "numRows": str(self.num_rows),
            "creationTime": self.create_time,
        }


@dataclass
class BigQueryJob:
    name: str  # projects/{p}/jobs/{id}
    project: str = ""
    job_id: str = ""
    state: str = "DONE"
    query: str = ""
    statistics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "kind": "bigquery#job",
            "id": f"{self.project}:{self.job_id}",
            "jobReference": {"projectId": self.project, "jobId": self.job_id},
            "status": {"state": self.state},
            "statistics": self.statistics,
        }
        if self.query:
            out["configuration"] = {"query": {"query": self.query}}
        return out


class BigQueryDataStore:
    def __init__(self) -> None:
        self.datasets: CaseInsensitiveDict = CaseInsensitiveDict()
        self.tables: CaseInsensitiveDict = CaseInsensitiveDict()
        self.jobs: CaseInsensitiveDict = CaseInsensitiveDict()
