"""Multi-cloud meta-registry for LocalStack.

Each cloud lives under `localstack-core/localstack/<cloud>/` following the canonical
layout documented in `docs/superpowers/plans/2026-05-22-multi-cloud-organization.md`.
"""

from localstack.cloud.base import CloudProvider
from localstack.cloud.builtin import register_builtins
from localstack.cloud.edge import MultiCloudEdge
from localstack.cloud.registry import CloudRegistry, registry

__all__ = ["CloudProvider", "CloudRegistry", "MultiCloudEdge", "register_builtins", "registry"]
