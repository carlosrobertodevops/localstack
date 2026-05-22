# Azure Services Parity — Consolidated Implementation Plan

> Consolida e estende: `2026-05-21-azure-services-platform.md` (audit/CI/coverage) e `2026-05-22-azure-core-foundation.md` (primitivos core).
> Foco: módulo `localstack-core/localstack/azure/` análogo a `localstack-core/localstack/aws/`, sem reuso de SigV4/Botocore/Moto.

---

## 1. Verdict de viabilidade

**SIM, viável e em andamento.** Core primitives (errors, IDs, scope, spec registry, stores, ARM resource manager, ARM serializers, HTTP router) já implementados (56 testes passando). Faltam: data-plane routers (Blob/Queue/Table), Functions trigger shim, Cosmos item CRUD, integração ao edge HTTP gateway, plugin discovery via Plux, persistência, marker convention.

**Restrição arquitetural:** Azure ≠ cópia de `aws/`. Não reuso botocore service catalogs, SigV4, ARNs, CloudFormation `ResourceProvider`, Moto fallback, fixtures `tests/aws/`. Azure modela: tenant → subscription → resource group → provider namespace → resource type → resource (+ child).

## 2. Estado atual (mapa)

```
localstack-core/localstack/azure/
├── __init__.py            ✅ exports públicos
├── exceptions.py          ✅ AzureError/NotFound/InvalidRequest/UnsupportedOperation/InvalidResourceId
├── ids.py                 ✅ AzureResourceId.parse/format + child segments
├── scope.py               ✅ AzureScope (sub/rg/location)
├── spec.py                ✅ AzureServiceSpec + Registry (namespace × type × api_versions × locations)
├── defaults.py            ✅ create_default_registry (Resources, Storage, Web, DocumentDB)
├── stores.py              ✅ AzureStores, AzureSubscriptionStore, AzureResourceGroup, AzureGenericResource, CaseInsensitiveDict
├── resource_manager.py    ✅ ResourceManagerProvider (RG + generic resource CRUD)
├── arm_serializers.py     ✅ serialize/deserialize ARM JSON (RG, resource, list)
├── arm_router.py          ✅ WSGI router p/ /subscriptions/.../resourceGroups/...
└── services/
    ├── storage/           🟡 MicrosoftStorageProvider (Blob containers/blobs/Queues in-memory) — sem REST adapter
    ├── functions/         🟡 MicrosoftWebProvider (Function App metadata only) — sem trigger shim
    └── cosmos/            🟡 MicrosoftDocumentDBProvider (accounts/db/containers metadata) — sem item CRUD
```

Testes: `tests/unit/azure/` (56/56 passando).

## 3. Analogia AWS ↔ Azure

| AWS módulo                    | Azure módulo (alvo)                         | Status |
| ----------------------------- | ------------------------------------------- | ------ |
| `aws/api/<svc>/`              | `azure/api/<provider>/` (gerado de OpenAPI/ARM specs, fase 3) | ❌ |
| `aws/protocol/`               | `azure/protocol/` (REST JSON ARM + REST XML para Storage)     | ❌ |
| `aws/skeleton.py`             | `azure/skeleton.py` (dispatch ARM/data-plane)                 | ❌ |
| `aws/forwarder.py`            | `azure/forwarder.py`                                          | ❌ |
| `aws/handlers/`               | `azure/handlers/` (auth `Authorization: Bearer`, region/RG validation, request_context) | ❌ |
| `aws/chain.py`                | `azure/chain.py` (handler chain)                              | ❌ |
| `aws/gateway.py`              | `azure/gateway.py` (mount `arm_router` + service routers)     | ❌ |
| `aws/accounts.py`             | `azure/accounts.py` (subscription/tenant ID provider)         | ❌ |
| `aws/connect.py`              | `azure/connect.py` (internal SDK client → azure SDK)          | ❌ |
| `aws/spec.py`                 | `azure/spec.py`                                               | ✅ |
| `aws/serving/`                | `azure/serving/` (edge mount + DNS hostname resolution)       | ❌ |
| `services/<svc>/provider.py`  | `azure/services/<svc>/provider.py`                            | 🟡 (3 stubs) |
| `services/stores.py`          | `azure/stores.py`                                             | ✅ |
| `services/<svc>/models.py`    | `azure/services/<svc>/models.py`                              | 🟡 |
| `services/plugins.py` (Plux)  | `azure/services/plugins.py`                                   | ❌ |

## 4. Tiers de serviço (MVP → completo)

**Tier 1 — Foundation MVP (alvo desta milestone):**

| Serviço            | Namespace                              | Análogo AWS    | Escopo                             |
| ------------------ | -------------------------------------- | -------------- | ---------------------------------- |
| Resource Manager   | `Microsoft.Resources`                  | CloudFormation (parcial) | RG + generic resource CRUD ✅ |
| Storage Account    | `Microsoft.Storage/storageAccounts`    | S3 (control plane) | metadata ARM ✅              |
| Blob Storage       | data plane `*.blob.core.windows.net`   | S3 (data plane) | containers + blob CRUD     |
| Queue Storage      | data plane `*.queue.core.windows.net`  | SQS            | queue + msg CRUD            |
| Function Apps      | `Microsoft.Web/sites`                  | Lambda         | metadata ✅ + HTTP trigger invoke |
| Cosmos DB          | `Microsoft.DocumentDB/databaseAccounts`| DynamoDB       | account/db/container ✅ + item CRUD |
| Microsoft Entra ID | `Microsoft.Graph` (auth tokens)        | IAM/STS        | mock OAuth2 token endpoint  |

**Tier 2 — Extensão:** Key Vault, Service Bus, Event Grid, Table Storage, Container Registry, App Service Plan, Log Analytics, Managed Identity.

**Tier 3 — Nice-to-have:** API Management, Application Insights, SQL Database, Virtual Network, Front Door, Private DNS, Container Instances.

## 5. Architecture

```
Client (azure SDK / azlocal / Terraform)
  │ HTTPS
  ▼
Edge Gateway (localstack edge) :4566
  │ host-based / path-based dispatch
  ▼
azure/gateway.py
  ├─ ARM control plane (/subscriptions/...)         → azure/arm_router.py    ✅
  ├─ Storage Blob   (Host: *.blob.core.windows.net) → azure/services/storage/blob_router.py
  ├─ Storage Queue  (Host: *.queue.core.windows.net)→ azure/services/storage/queue_router.py
  ├─ Function HTTP  (Host: *.azurewebsites.net)     → azure/services/functions/http_router.py
  ├─ Cosmos REST    (Host: *.documents.azure.com)   → azure/services/cosmos/sql_router.py
  └─ OAuth2 token   (/{tenant}/oauth2/v2.0/token)   → azure/services/entra/token_router.py
```

Plux entry-point group: `localstack.azure.providers`. Each provider plugin exposes `(namespace, resource_type) → provider class`.

## 6. Roadmap (sprints)

### Sprint A — Data plane Tier 1 (esta milestone)
1. [x] Blob REST adapter (`azure/services/storage/blob_router.py`, 14 testes).
2. [x] Queue REST adapter (`azure/services/storage/queue_router.py`, 12 testes).
3. [x] Function HTTP trigger shim (`azure/services/functions/http_router.py` + `registry.py`, 9 testes).
4. [x] Cosmos SQL API item CRUD (`azure/services/cosmos/sql_router.py` + item ops no provider, 12 testes).

### Sprint B — Auth + edge integration
5. [x] Microsoft Entra ID mock token endpoint (`azure/services/entra/token_router.py`, 6 testes).
6. [x] `azure/handlers.py` chain: `AuthHandler`, `RequestContextHandler`, `ErrorSerializerHandler`, `HandlerChain`, `AzureRequestContext` (14 testes).
7. [x] `azure/gateway.py` WSGI dispatcher + host-based routing (7 testes).
8. [ ] Mount sob edge gateway (porta 4566 paralela à AWS).

### Sprint C — Plugin discovery + persistence
9. [x] Plugin registry `azure/plugins.py` — `AzureProviderPlugin` + `AzureProviderRegistry` + `iter_builtin_plugins()` (7 testes). Plux entry-point group adiar até houver carregamento dinâmico real.
10. [x] `azure/state.py` persistência pickle (snapshot/restore por gateway, 4 testes).
11. [ ] `azlocal` smoke tests reaproveitados do plan 05-21.

### Sprint D — Spec generation + Tier 2
12. [ ] ARM spec ingest (resource-manager-schemas → `azure/api/<namespace>/`).
13. Tier-2 services:
    - [x] Key Vault (`azure/services/keyvault/`, 13 testes).
    - [x] Service Bus (`azure/services/servicebus/`: queues + topics + subscriptions + REST, 9 testes).
    - [x] Event Grid (`azure/services/eventgrid/`: topics + subscriptions + publish/fanout + REST, 12 testes).
    - [x] Table Storage (`azure/services/tablestorage/`: tables + entity CRUD + OData REST, 14 testes).

### Sprint E — Cross-cloud edge
14. [x] `cloud/edge.py` — `MultiCloudEdge` WSGI dispatcher (host-pattern matching via `CloudProvider.edge_hosts`, 5 testes). Permite AWS + Azure no mesmo port.

## 7. Guardrails (mantidos do plan 05-21)

- ❌ NÃO editar `localstack-core/localstack/aws/api/**`.
- ❌ NÃO editar AWS CloudFormation `ResourceProvider` para Azure.
- ❌ NÃO alterar fixtures globais `tests/aws/` para Azure.
- ❌ NÃO adicionar SDK Azure como dep core (apenas test extras).
- ❌ NÃO colocar testes Azure sob `tests/aws/**`.
- ❌ NÃO usar markers AWS para testes Azure.
- ❌ NÃO promover paridade de serviço sem testes dedicados.

## 8. Próximo passo concreto: Blob REST adapter (Sprint A.1)

Implementação TDD nesta milestone.

**Files:**
- Create: `localstack-core/localstack/azure/services/storage/blob_router.py`
- Create: `tests/unit/azure/services/storage/test_blob_router.py`

**API REST Azure Blob (subconjunto MVP):**

| Método | Path                                   | Ação                          |
| ------ | -------------------------------------- | ----------------------------- |
| PUT    | `/{container}?restype=container`       | criar container               |
| GET    | `/{container}?restype=container&comp=list` | listar blobs              |
| DELETE | `/{container}?restype=container`       | deletar container             |
| PUT    | `/{container}/{blob}`                  | upload blob (block)           |
| GET    | `/{container}/{blob}`                  | download                      |
| DELETE | `/{container}/{blob}`                  | deletar blob                  |
| HEAD   | `/{container}/{blob}`                  | metadata                      |

**Auth:** ignorada nesta fase (será coberta no Sprint B).

**Conteúdo:** XML para listing (Azure usa XML para `BlobList`), binário para blob body.

**Errors:** `<Error><Code>ContainerNotFound</Code>...</Error>` (XML).

### Tasks

- [x] **Step 1:** RED tests `test_blob_router.py` cobrindo todos métodos + 404/409. (`tests/unit/azure/services/test_blob_router.py`)
- [x] **Step 2:** Implementar `BlobRouter` WSGI sobre `MicrosoftStorageProvider`. (`localstack-core/localstack/azure/services/storage/blob_router.py`)
- [x] **Step 3:** GREEN — 14/14 passed.
- [x] **Step 4:** Atualizar `azure/services/storage/__init__.py` e `azure/__init__.py` p/ exportar `BlobRouter`.

---

## 9. Critérios de conclusão da milestone (Sprint A)

- Todos os 4 data-plane routers (Blob, Queue, Function HTTP, Cosmos item) com testes unit ≥10 cada.
- Suite `tests/unit/azure/` permanece 100% green.
- `azure/__init__.py` exporta novos routers.
- Plan 05-22 (core foundation) com "Personal Next Steps" totalmente `[x]`.
- Doc deste plan atualizado com checkboxes marcados.

## 10. Referências

- Plan inventory/CI: `docs/superpowers/plans/2026-05-21-azure-services-platform.md`
- Plan core primitives: `docs/superpowers/plans/2026-05-22-azure-core-foundation.md`
- Módulo AWS análogo: `localstack-core/localstack/aws/`
- Azure REST docs: https://learn.microsoft.com/rest/api/azure/
- Azure ARM templates: https://learn.microsoft.com/azure/templates/
