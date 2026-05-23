"""Meta-types shared by every cloud module under `localstack-core/localstack/<cloud>/`."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

# Each cloud advertises a small contract: a WSGI gateway factory, a state-store factory,
# and a provider-plugin registry factory. Imports stay lazy so registering a cloud is cheap.

GatewayFactory = Callable[[], Any]
StateStoreFactory = Callable[[], Any]
PluginRegistryFactory = Callable[[], Any]


@dataclass(frozen=True)
class CloudProvider:
    """Metadata + lazy factories describing a registered cloud implementation."""

    name: str  # canonical short name: "aws", "azure", "gcp", ...
    display_name: str  # human label: "Amazon Web Services", "Microsoft Azure"
    package: str  # python import path of the cloud module ("localstack.aws", "localstack.azure")
    gateway_factory: GatewayFactory
    state_store_factory: StateStoreFactory | None = None
    plugin_registry_factory: PluginRegistryFactory | None = None
    edge_hosts: tuple[str, ...] = ()  # host suffix patterns this cloud serves
    metadata: dict[str, Any] = field(default_factory=dict)

    def build_gateway(self) -> Any:
        return self.gateway_factory()

    def build_state_store(self) -> Any | None:
        return self.state_store_factory() if self.state_store_factory else None

    def build_plugin_registry(self) -> Any | None:
        return self.plugin_registry_factory() if self.plugin_registry_factory else None

    def list_services(self) -> dict[str, str]:
        reg = self.build_plugin_registry()
        if reg is None:
            return {}
        if hasattr(reg, "namespaces"):
            names = reg.namespaces()
        elif hasattr(reg, "services"):
            names = reg.services()
        else:
            return {}
        return dict.fromkeys(names, "available")
