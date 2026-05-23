from __future__ import annotations

from typing import Callable

from localstack.gcp.exceptions import GcpNotFound


class FunctionsRegistry:
    """Map ``(region, project, function)`` to a Python callable simulating the runtime."""

    def __init__(self) -> None:
        self._handlers: dict[tuple[str, str, str], Callable] = {}

    def register(self, region: str, project: str, function: str, handler: Callable[[dict, dict], tuple[int, dict, bytes]]) -> None:
        self._handlers[(region.lower(), project.lower(), function.lower())] = handler

    def get(self, region: str, project: str, function: str) -> Callable[[dict, dict], tuple[int, dict, bytes]]:
        key = (region.lower(), project.lower(), function.lower())
        h = self._handlers.get(key)
        if h is None:
            raise GcpNotFound(f"function not registered: {region}/{project}/{function}")
        return h

    def has(self, region: str, project: str, function: str) -> bool:
        return (region.lower(), project.lower(), function.lower()) in self._handlers
