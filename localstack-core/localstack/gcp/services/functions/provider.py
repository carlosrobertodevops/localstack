from __future__ import annotations

from typing import Any, Callable

from localstack.gcp.exceptions import GcpAlreadyExists, GcpInvalidRequest, GcpNotFound
from localstack.gcp.resource_manager import ResourceManagerProvider
from localstack.gcp.services.functions.models import CloudFunction, FunctionsDataStore
from localstack.gcp.services.functions.registry import FunctionsRegistry
from localstack.gcp.stores import GcpStores


class CloudFunctionsProvider:
    def __init__(
        self,
        *,
        resource_manager: ResourceManagerProvider | None = None,
        stores: GcpStores | None = None,
        registry: FunctionsRegistry | None = None,
    ) -> None:
        self.stores = stores or GcpStores()
        self.resource_manager = resource_manager or ResourceManagerProvider(stores=self.stores)
        self.data = FunctionsDataStore()
        self.registry = registry or FunctionsRegistry()

    def create_function(self, full_name: str, *, runtime: str = "python313", entry_point: str = "main", environment: dict[str, str] | None = None, labels: dict[str, str] | None = None) -> CloudFunction:
        parts = full_name.split("/")
        if len(parts) != 6 or parts[0] != "projects" or parts[2] != "locations" or parts[4] != "functions":
            raise GcpInvalidRequest(f"invalid function name: {full_name}")
        if full_name in self.data.functions:
            raise GcpAlreadyExists(f"function '{full_name}' already exists")
        self.resource_manager.ensure_project(parts[1])
        fn = CloudFunction(
            name=full_name,
            runtime=runtime,
            entry_point=entry_point,
            environment=dict(environment or {}),
            labels=dict(labels or {}),
            update_time=self.data.now_iso(),
        )
        self.data.functions[full_name] = fn
        return fn

    def get_function(self, full_name: str) -> CloudFunction:
        fn = self.data.functions.get(full_name)
        if fn is None:
            raise GcpNotFound(f"function '{full_name}' not found")
        return fn

    def list_functions(self, project: str, location: str) -> list[CloudFunction]:
        prefix = f"projects/{project}/locations/{location}/functions/"
        return [f for f in self.data.functions.values() if f.name.startswith(prefix)]

    def delete_function(self, full_name: str) -> None:
        if full_name not in self.data.functions:
            raise GcpNotFound(f"function '{full_name}' not found")
        del self.data.functions[full_name]

    def attach_handler(self, full_name: str, handler: Callable[[dict, dict], tuple[int, dict, bytes]]) -> None:
        fn = self.get_function(full_name)
        parts = fn.name.split("/")
        project, location, function = parts[1], parts[3], parts[5]
        self.registry.register(location, project, function, handler)

    def invoke(self, *, region: str, project: str, function: str, request_env: dict[str, Any], body: bytes) -> tuple[int, dict[str, str], bytes]:
        handler = self.registry.get(region, project, function)
        return handler(request_env, {"body": body})
