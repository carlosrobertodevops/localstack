from __future__ import annotations

from collections import UserDict
from dataclasses import dataclass, field
from typing import Any


class CaseInsensitiveDict(UserDict):
    def __contains__(self, key: object) -> bool:
        return super().__contains__(self._normalize(key))

    def __getitem__(self, key: str) -> Any:
        return super().__getitem__(self._normalize(key))

    def __setitem__(self, key: str, value: Any) -> None:
        super().__setitem__(self._normalize(key), value)

    def __delitem__(self, key: str) -> None:
        super().__delitem__(self._normalize(key))

    def get(self, key: str, default: Any = None) -> Any:
        return super().get(self._normalize(key), default)

    def pop(self, key: str, default: Any = None) -> Any:
        return super().pop(self._normalize(key), default)

    @staticmethod
    def _normalize(key: object) -> object:
        return key.lower() if isinstance(key, str) else key


@dataclass
class GcpProject:
    project_id: str
    name: str = ""
    project_number: str = ""
    state: str = "ACTIVE"
    labels: dict[str, str] = field(default_factory=dict)
    create_time: str = ""


@dataclass
class GcpGenericResource:
    name: str  # full resource name "projects/.../..."
    resource_type: str
    location: str | None = None
    labels: dict[str, str] = field(default_factory=dict)
    properties: dict[str, Any] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class GcpProjectStore:
    project: GcpProject | None = None
    resources: CaseInsensitiveDict = field(default_factory=CaseInsensitiveDict)


class GcpStores:
    def __init__(self) -> None:
        self._projects: CaseInsensitiveDict = CaseInsensitiveDict()

    def get_project(self, project_id: str) -> GcpProjectStore:
        store = self._projects.get(project_id)
        if store is None:
            store = GcpProjectStore()
            self._projects[project_id] = store
        return store

    def has_project(self, project_id: str) -> bool:
        return project_id in self._projects

    def clear(self) -> None:
        self._projects.clear()
