"""In-memory registry of HTTP-triggered Azure Functions."""

from __future__ import annotations

from typing import Callable

from localstack.azure.stores import CaseInsensitiveDict

FunctionHandler = Callable  # (werkzeug.Request) -> dict | bytes | str


class FunctionsRegistry:
    """Maps `(function_app, function_name)` to a Python handler."""

    def __init__(self) -> None:
        self._apps: CaseInsensitiveDict = CaseInsensitiveDict()

    def register(self, app_name: str, function_name: str, handler: FunctionHandler) -> None:
        functions = self._apps.get(app_name)
        if functions is None:
            functions = CaseInsensitiveDict()
            self._apps[app_name] = functions
        functions[function_name] = handler

    def unregister(self, app_name: str, function_name: str) -> None:
        functions = self._apps.get(app_name)
        if functions is None:
            return
        functions.pop(function_name, None)

    def get(self, app_name: str, function_name: str) -> FunctionHandler | None:
        functions = self._apps.get(app_name)
        if functions is None:
            return None
        return functions.get(function_name)

    def list_functions(self, app_name: str) -> tuple[str, ...]:
        functions = self._apps.get(app_name)
        if functions is None:
            return ()
        return tuple(sorted(functions.keys()))

    def clear(self) -> None:
        self._apps.clear()
