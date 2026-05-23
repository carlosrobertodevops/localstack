# GCP Services Parity — Consolidated Implementation Plan

> Análogo a `2026-05-22-azure-services-parity.md`. Módulo `localstack-core/localstack/gcp/`, espelha layout de `azure/` e `aws/`, sem reuso de SigV4/Botocore/Moto/SDK Google.

---

## 1. Verdict de viabilidade

**SIM.** Mesmo padrão de Azure (que rendeu 209 testes verdes). GCP modela: organization → folder → **project** → location → service → resource. Diferenças críticas vs Azure:

- Auth: OAuth2 bearer + Google Service Account JWT (RS256/HS256 mock). Sem ARM-like control plane unificado.
- Resource names: `projects/{p}/locations/{l}/{type}/{id}` (path-based, não ARM ID).
- REST: predominantemente JSON via googleapis.com (path-based) + alguns endpoints especiais (GCS XML compat S3).
- Cada serviço tem seu host `*.googleapis.com` ou subdomínio dedicado (`storage.googleapis.com/{bucket}`, `pubsub.googleapis.com`, etc).

## 2. Estado alvo (mapa)

```
localstack-core/localstack/gcp/
├── __init__.py            ✅ exports públicos
├── exceptions.py          GcpError/NotFound/InvalidRequest/Unsupported/InvalidResourceName
├── resource_names.py      GcpResourceName.parse/format (projects/.../locations/.../...)
├── scope.py               GcpScope (project_id, location)
├── spec.py                GcpServiceSpec + Registry (service × resource_type × versions × locations)
├── defaults.py            create_default_registry (Storage, Pub/Sub, Firestore, Functions, IAM)
├── stores.py              GcpStores, GcpProjectStore, CaseInsensitiveDict
├── resource_manager.py    ResourceManagerProvider (Projects CRUD)
├── serializers.py         JSON serialize/deserialize (REST + LRO Operation envelope)
├── gateway.py             GcpGateway (host+path-based dispatch)
├── handlers.py            AuthHandler/RequestContextHandler/ErrorSerializerHandler/HandlerChain
├── plugins.py             GcpProviderPlugin + GcpProviderRegistry
├── state.py               GcpStateStore (pickle snapshot/restore)
└── services/
    ├── storage/           GCS — buckets + objects (JSON + XML REST)
    ├── pubsub/            Pub/Sub — topics/subscriptions/messages
    ├── firestore/         Firestore — databases/collections/documents
    ├── functions/         Cloud Functions — registry + HTTP trigger shim
    └── iam/               IAM/STS — OAuth2 token + service account JWT mint
```

Tests: `tests/unit/gcp/` (alvo ~150 testes).

## 3. Analogia AWS ↔ Azure ↔ GCP

| AWS               | Azure                      | GCP                          | Status |
| ----------------- | -------------------------- | ---------------------------- | ------ |
| `aws/api/<svc>/`  | `azure/api/<ns>/`          | `gcp/api/<svc>/` (futuro)    | ❌ |
| `aws/protocol/`   | `azure/arm_serializers.py` | `gcp/serializers.py`         | plan |
| `aws/skeleton.py` | `azure/skeleton.py`        | `gcp/skeleton.py` (defer)    | ❌ |
| `aws/handlers/`   | `azure/handlers.py`        | `gcp/handlers.py`            | plan |
| `aws/chain.py`    | (embed in handlers)        | (embed in handlers)          | plan |
| `aws/gateway.py`  | `azure/gateway.py`         | `gcp/gateway.py`             | plan |
| `aws/accounts.py` | `azure/scope.py` (sub)     | `gcp/scope.py` (project)     | plan |
| `aws/spec.py`     | `azure/spec.py`            | `gcp/spec.py`                | plan |

## 4. Tiers (MVP → completo)

**Tier 1 — Foundation MVP (alvo desta milestone):**

| Service             | Host                                    | Análogo AWS      | Análogo Azure       |
| ------------------- | --------------------------------------- | ---------------- | ------------------- |
| Resource Manager    | `cloudresourcemanager.googleapis.com`   | (none)           | Microsoft.Resources |
| Cloud Storage (GCS) | `storage.googleapis.com/{bucket}` (XML) + `storage.googleapis.com/storage/v1/...` (JSON) | S3 | Blob Storage |
| Pub/Sub             | `pubsub.googleapis.com`                 | SNS+SQS          | Service Bus + Event Grid |
| Firestore           | `firestore.googleapis.com`              | DynamoDB         | Cosmos DB           |
| Cloud Functions     | `cloudfunctions.googleapis.com` + `{region}-{project}.cloudfunctions.net` (invoke) | Lambda | Functions |
| IAM/STS             | `iam.googleapis.com` + `oauth2.googleapis.com/token` | STS | Microsoft Entra ID |

**Tier 2 — Extensão (✅ implementado):** BigQuery, Cloud Run, Secret Manager, Cloud Tasks, Cloud KMS, Cloud Logging. **Restante:** Cloud SQL, Cloud Scheduler, Cloud DNS.

**Tier 3 — Nice-to-have:** Compute Engine, GKE, Cloud Build, Cloud Endpoints, Spanner, Memorystore, AI Platform.

## 5. Architecture

```
Client (gcloud / google-cloud-* SDK / Terraform google provider)
  │ HTTPS
  ▼
Edge Gateway (localstack edge) :4566
  │ host-based dispatch via cloud/edge.MultiCloudEdge
  ▼
gcp/gateway.py
  ├─ Cloud Storage XML (Host: storage.googleapis.com path /{bucket}/...)   → gcp/services/storage/xml_router.py
  ├─ Cloud Storage JSON (Host: storage.googleapis.com path /storage/v1/...) → gcp/services/storage/json_router.py
  ├─ Pub/Sub REST (Host: pubsub.googleapis.com path /v1/projects/...)       → gcp/services/pubsub/rest_router.py
  ├─ Firestore (Host: firestore.googleapis.com)                             → gcp/services/firestore/rest_router.py
  ├─ Functions HTTP invoke (Host: {region}-{proj}.cloudfunctions.net)       → gcp/services/functions/http_router.py
  ├─ Functions control (Host: cloudfunctions.googleapis.com)                → gcp/services/functions/control_router.py
  ├─ IAM OAuth2 (Host: oauth2.googleapis.com path /token)                   → gcp/services/iam/token_router.py
  └─ Resource Manager (Host: cloudresourcemanager.googleapis.com)           → gcp/services/resource_manager (provider direto)
```

Plux entry-point group: `localstack.gcp.providers`. Cada provider plugin expõe `(service, resource_type) → provider class`.

## 6. Roadmap (sprints)

### Sprint A — Core primitives + Tier-1 data plane (esta milestone)
1. [ ] Exceptions, resource_names, scope, stores, spec, defaults.
2. [ ] Resource Manager Provider (Projects CRUD).
3. [ ] GCS XML + JSON routers — buckets + objects CRUD.
4. [ ] Pub/Sub REST router — topics + subs + publish + pull.
5. [ ] Firestore REST router — documents CRUD.
6. [ ] Cloud Functions HTTP trigger + control plane.
7. [ ] IAM OAuth2 token endpoint + service-account JWT mint.

### Sprint B — Gateway + handlers + multi-cloud edge
8. [ ] `gcp/handlers.py` chain: AuthHandler, RequestContextHandler, ErrorSerializerHandler, HandlerChain, GcpRequestContext.
9. [ ] `gcp/gateway.py` WSGI dispatcher + host+path-based routing.
10. [ ] Registrar em `cloud/builtin.py` (`gcp` CloudProvider) + adicionar hosts em `cloud/edge.py` se necessário.

### Sprint C — Plugin discovery + persistence
11. [ ] `gcp/plugins.py` — GcpProviderPlugin + GcpProviderRegistry + iter_builtin_plugins.
12. [ ] `gcp/state.py` persistência pickle.

### Sprint D — Spec generation + Tier-2
13. [ ] OpenAPI ingest discovery docs → `gcp/api/<service>/types.py`.
14. [x] Tier-2: BigQuery, Cloud Run, Secret Manager, Cloud Tasks, KMS, Logging (81 testes).

### Sprint E — Cross-cloud edge (já existe)
15. [x] `cloud/edge.MultiCloudEdge` já implementado — só adicionar `gcp` ao register + hosts.

## 7. Guardrails

- ❌ NÃO editar `localstack-core/localstack/aws/api/**`.
- ❌ NÃO reusar Moto fallback p/ GCP.
- ❌ NÃO adicionar `google-cloud-*` SDKs como dep core (apenas test extras).
- ❌ NÃO colocar testes GCP sob `tests/aws/**` nem `tests/unit/azure/**`.
- ❌ NÃO usar markers AWS/Azure p/ testes GCP.
- ❌ NÃO promover paridade sem testes dedicados.

## 8. Critérios de conclusão Sprint A+B+C

- Todos os 5 services Tier-1 com testes unit ≥10 cada (~50 testes mínimo).
- `tests/unit/gcp/` permanece 100% green.
- `gcp/__init__.py` exporta primitivos + routers + provider classes.
- `cloud/builtin.py` registra `gcp` CloudProvider.
- Master roadmap atualizado (Phase 7 = GCP).
- Suite combinada `tests/unit/{azure,cloud,gcp}` verde.

## 9. Referências

- Plan inventory Azure: `docs/superpowers/plans/2026-05-22-azure-services-parity.md`
- Plan multi-cloud meta: `docs/superpowers/plans/2026-05-22-multi-cloud-organization.md`
- Master roadmap: `docs/superpowers/plans/2026-05-22-master-roadmap.md`
- GCP REST docs: https://cloud.google.com/apis/docs/overview
- GCS XML API: https://cloud.google.com/storage/docs/xml-api/overview
- Pub/Sub REST: https://cloud.google.com/pubsub/docs/reference/rest
