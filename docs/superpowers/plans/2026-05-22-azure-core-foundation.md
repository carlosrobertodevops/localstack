# Azure Core Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an isolated, experimental Microsoft Azure foundation under `localstack-core/localstack/azure` without changing AWS runtime behavior.

**Architecture:** Azure starts as a parallel domain, not a copy of `localstack.aws.*`. The first milestone implements dependency-free core primitives: Azure errors, Azure Resource ID parsing/formatting, and a resource-provider spec registry for future ARM/resource-manager work.

**Tech Stack:** Python, pytest, LocalStack package layout, Azure ARM concepts: subscriptions, resource groups, provider namespaces, resource types, API versions, locations.

---

## Feasibility Verdict

Creating `localstack-core/localstack/azure` is feasible if it stays isolated. Do not reuse AWS botocore service catalogs, SigV4 request context, ARNs, CloudFormation `ResourceProvider`, Moto fallback, or AWS pytest fixtures for Azure. Azure should model subscriptions, resource groups, locations, provider namespaces, resource IDs, and ARM-style APIs.

## Files

- Create: `localstack-core/localstack/azure/__init__.py`
- Create: `localstack-core/localstack/azure/exceptions.py`
- Create: `localstack-core/localstack/azure/ids.py`
- Create: `localstack-core/localstack/azure/spec.py`
- Create: `tests/unit/azure/test_imports.py`
- Create: `tests/unit/azure/test_resource_ids.py`
- Create: `tests/unit/azure/test_spec_registry.py`

## Task 1: Importable Azure Package

**Files:**
- Test: `tests/unit/azure/test_imports.py`
- Create: `localstack-core/localstack/azure/__init__.py`
- Create: `localstack-core/localstack/azure/exceptions.py`

- [ ] **Step 1: Write failing import test**

```python
def test_localstack_azure_imports_without_optional_azure_dependencies():
    import localstack.azure
    from localstack.azure.exceptions import AzureUnsupportedOperation
    from localstack.azure.ids import AzureResourceId
    from localstack.azure.spec import AzureServiceSpec, AzureServiceSpecRegistry

    assert localstack.azure.__all__
    assert AzureUnsupportedOperation
    assert AzureResourceId
    assert AzureServiceSpec
    assert AzureServiceSpecRegistry
```

- [ ] **Step 2: Run RED test**

Run: `.venv/bin/python -m pytest tests/unit/azure -q`

Expected: FAIL with `ModuleNotFoundError: No module named 'localstack.azure.exceptions'`.

- [ ] **Step 3: Add package exports and base errors**

```python
class AzureError(Exception):
    status_code = 500
    code = "AzureError"


class AzureUnsupportedOperation(AzureError):
    status_code = 501
    code = "UnsupportedAzureOperation"


class AzureInvalidResourceId(ValueError):
    pass
```

- [ ] **Step 4: Run GREEN import test**

Run: `.venv/bin/python -m pytest tests/unit/azure/test_imports.py -q`

Expected: PASS.

## Task 2: Azure Resource IDs

**Files:**
- Test: `tests/unit/azure/test_resource_ids.py`
- Create: `localstack-core/localstack/azure/ids.py`

- [ ] **Step 1: Write failing Resource ID tests**

```python
resource_id = AzureResourceId.parse(
    "/subscriptions/sub-123/resourceGroups/rg-dev/providers/Microsoft.Storage/storageAccounts/store1"
)
assert resource_id.subscription_id == "sub-123"
assert resource_id.resource_group == "rg-dev"
assert resource_id.namespace == "Microsoft.Storage"
assert resource_id.resource_type == "storageAccounts"
assert resource_id.name == "store1"
```

- [ ] **Step 2: Run RED test**

Run: `.venv/bin/python -m pytest tests/unit/azure/test_resource_ids.py -q`

Expected: FAIL until `AzureResourceId` exists.

- [ ] **Step 3: Implement parser/formatter**

```python
@dataclass(frozen=True)
class AzureResourceId:
    subscription_id: str
    resource_group: str
    namespace: str
    resource_type: str
    name: str
    child_resources: tuple[tuple[str, str], ...] = ()
```

- [ ] **Step 4: Run GREEN Resource ID test**

Run: `.venv/bin/python -m pytest tests/unit/azure/test_resource_ids.py -q`

Expected: PASS.

## Task 3: Azure Service Spec Registry

**Files:**
- Test: `tests/unit/azure/test_spec_registry.py`
- Create: `localstack-core/localstack/azure/spec.py`

- [ ] **Step 1: Write failing registry tests**

```python
registry = AzureServiceSpecRegistry()
spec = AzureServiceSpec(
    namespace="Microsoft.Storage",
    resource_type="storageAccounts",
    api_versions=("2023-01-01",),
    locations=("eastus", "westeurope"),
)
registry.register(spec)
assert registry.get("Microsoft.Storage", "storageAccounts") == spec
```

- [ ] **Step 2: Run RED test**

Run: `.venv/bin/python -m pytest tests/unit/azure/test_spec_registry.py -q`

Expected: FAIL until `AzureServiceSpecRegistry` exists.

- [ ] **Step 3: Implement registry**

```python
@dataclass(frozen=True)
class AzureServiceSpec:
    namespace: str
    resource_type: str
    api_versions: tuple[str, ...]
    locations: tuple[str, ...] = ()


class AzureServiceSpecRegistry:
    def register(self, spec: AzureServiceSpec) -> AzureServiceSpec: ...
    def get(self, namespace: str, resource_type: str) -> AzureServiceSpec: ...
    def namespaces(self) -> tuple[str, ...]: ...
    def resource_types(self, namespace: str) -> tuple[str, ...]: ...
```

- [ ] **Step 4: Run GREEN registry test**

Run: `.venv/bin/python -m pytest tests/unit/azure/test_spec_registry.py -q`

Expected: PASS.

## Next Milestones

- Add `localstack-core/localstack/azure/scope.py` with tenant/subscription/location/resource-group scope.
- Add `localstack-core/localstack/azure/stores.py` with subscription/resource-group/resource bundles.
- Add `localstack-core/localstack/azure/resource_manager.py` for in-memory resource groups and generic resources.
- Add Azure-specific tests under `tests/unit/azure/**` and later `tests/azure/**`; do not place Azure tests under `tests/aws/**`.
- Add real service vertical slices only after Resource Manager MVP: `Microsoft.Storage/storageAccounts`, Blob data plane, Queue data plane, Functions skeleton, Cosmos DB metadata.

## Personal ARM MVP Implemented

- `AzureScope` models subscription/resource-group/location scope for local-only use.
- `AzureStores` keeps isolated in-memory state per subscription.
- `ResourceManagerProvider` supports creating, updating, listing, getting, and deleting resource groups.
- `ResourceManagerProvider` supports creating, updating, listing, getting, and deleting generic ARM resources by Azure Resource ID.
- Generic ARM resources require an existing resource group, matching Azure Resource Manager behavior.
- Resource type support is gated by `AzureServiceSpecRegistry`.
- Location validation uses the registered `AzureServiceSpec.locations` tuple.
- `AzureNotFound` and `AzureInvalidRequest` provide deterministic local errors for missing resources and invalid scope/location input.

## Personal Next Steps

- [x] Add ARM-style JSON serializers so responses look closer to Azure REST. (`localstack-core/localstack/azure/arm_serializers.py`, `tests/unit/azure/test_arm_serializers.py`)
- [x] Add a lightweight HTTP router for `PUT/GET/DELETE /subscriptions/.../resourceGroups/...` and generic `/providers/{ns}/{type}/{name}` resources. (`localstack-core/localstack/azure/arm_router.py`, `tests/unit/azure/test_arm_router.py`)
- [x] Add Blob/Queue REST path adapters on top of the in-memory storage provider. (`azure/services/storage/blob_router.py`, `queue_router.py`)
- [x] Add Function HTTP trigger invocation shim on top of `MicrosoftWebProvider`. (`azure/services/functions/http_router.py` + `registry.py`)
- [x] Add Cosmos item CRUD on top of SQL database/container metadata. (`azure/services/cosmos/sql_router.py` + provider item ops)

## Personal Storage/Functions/Cosmos MVP Implemented

- `create_default_registry()` registers `Microsoft.Resources/resourceGroups`, `Microsoft.Storage/storageAccounts`, `Microsoft.Web/sites`, and `Microsoft.DocumentDB/databaseAccounts`.
- `MicrosoftStorageProvider` supports storage account metadata through ARM generic resources.
- `MicrosoftStorageProvider` supports Blob containers and blobs in memory.
- `MicrosoftStorageProvider` supports Storage Queues and messages in memory.
- `MicrosoftWebProvider` supports metadata-only Azure Function Apps as `Microsoft.Web/sites` resources with `kind=functionapp`.
- `MicrosoftDocumentDBProvider` supports metadata-only Cosmos DB accounts, SQL databases, and SQL containers.
- All providers remain direct Python APIs; there is still no Azure HTTP edge integration.

## Guardrails

- Do not edit `localstack-core/localstack/aws/api/**`.
- Do not edit AWS CloudFormation `ResourceProvider` to support Azure.
- Do not alter global AWS pytest fixtures for Azure.
- Do not add Azure SDK dependencies for the core primitives.
- Do not promise service parity until each Azure service has dedicated tests.
