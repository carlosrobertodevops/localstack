# Master Roadmap — Multi-Cloud LocalStack

> Consolida pendências de:
> - `2026-05-22-azure-core-foundation.md` (core Azure)
> - `2026-05-22-azure-services-parity.md` (Sprint A/B/C/D Azure)
> - `2026-05-22-gcp-services-parity.md` (GCP Tier-1)
> - `2026-05-22-multi-cloud-organization.md` (meta-cloud registry)
> - reorg pendente `platform/` + `tooling/` (deste prompt)
>
> Ordenado por dependência e risco. Cada item tem critério de "done" verificável.

---

## Status atual (snapshot)

| Suite | Testes | Status |
| --- | --- | --- |
| `tests/unit/azure/` | 154 | ✅ green |
| `tests/unit/cloud/` | 16 | ✅ green |
| `tests/unit/gcp/` | 123 | ✅ green (Tier-1 completo) |
| Combined `azure+cloud+gcp` | 332 | ✅ green em 0.40s |
| `tests/unit/` (AWS pós-refactor `services/→aws/services/`) | 16119 | ✅ green (smoke 6 arquivos, 54s) — full run trava em 1 fixture do test ~ final (`...FF` 97%) |

## Dirty state Git

- Refactor `services/* → aws/services/*`: ~1144 arquivos staged+untracked (git mv + sed). **Não validado** até AWS suite completar.
- Novos módulos Azure (handlers, state, plugins, services/entra, services/keyvault).
- Novo módulo `localstack/cloud/` + `tests/unit/cloud/`.
- Plans novos em `docs/superpowers/plans/`.

---

## Roadmap (ordem de execução)

### Phase 0 — Validação (em curso)

- [ ] **P0.1** AWS unit suite full green pós-refactor `services/→aws/services/`. **Gate p/ Phase 1.**
  - Comando: `python -m pytest tests/unit --ignore=tests/unit/azure --ignore=tests/unit/cloud --ignore=tests/unit/aws/test_mocking.py -q --tb=no`
  - Pid bg: 14936 (output `/tmp/.../bqu9cax90.output`)
  - Critério: 0 failures (warnings OK).

### Phase 1 — Reorg `platform/` + `tooling/` (alto risco)

Pré-requisito: P0.1 verde.

- [ ] **P1.1** `git mv runtime/ platform/runtime/` + análogos para `state/ dns/ http/ logging/`.
- [ ] **P1.2** `git mv` arquivos top-level (`config.py constants.py deprecations.py plugins.py version.py openapi.yaml py.typed`) para `platform/`.
- [ ] **P1.3** `git mv cli/ tooling/cli/` + `dev/ extensions/ testing/ packages/` análogos.
- [ ] **P1.4** Bulk `sed -i ''` em todo `*.py *.ini *.toml *.md *.cfg *.yaml`:
  - `localstack.runtime` → `localstack.platform.runtime`
  - `localstack.state` → `localstack.platform.state`
  - `localstack.dns` → `localstack.platform.dns`
  - `localstack.http` → `localstack.platform.http`
  - `localstack.logging` → `localstack.platform.logging`
  - `localstack.config` → `localstack.platform.config`
  - `localstack.constants` → `localstack.platform.constants`
  - `localstack.deprecations` → `localstack.platform.deprecations`
  - `localstack.plugins` → `localstack.platform.plugins`
  - `localstack.version` → `localstack.platform.version`
  - `localstack.cli` → `localstack.tooling.cli`
  - `localstack.dev` → `localstack.tooling.dev`
  - `localstack.extensions` → `localstack.tooling.extensions`
  - `localstack.testing` → `localstack.tooling.testing`
  - `localstack.packages` → `localstack.tooling.packages`
- [ ] **P1.5** `pyproject.toml`: ajustar `package-dir`/`packages.find` se necessário.
- [ ] **P1.6** Regenerar `plux.ini` via `python -m plux entrypoints`.
- [ ] **P1.7** Re-run Azure + Cloud + AWS unit suites. Gate p/ Phase 2.
- [ ] **P1.8** Atualizar `CLAUDE.md` + `TESTING_LOCAL.md` para refletir novos paths.

### Phase 2 — Azure Sprint B finalização

- [ ] **P2.1** Mount `AzureGateway` sob edge real (porta 4566 paralela à AWS). Depende de `platform/runtime/` (ex-`runtime/`) e `platform/http/` (ex-`http/`). Testes integração leves.
- [ ] **P2.2** Validar smoke: `curl -H Host:acct1.blob.core.windows.net localhost:4566/c1?restype=container -X PUT`.

### Phase 3 — Azure Sprint C completar

- [ ] **P3.1** `azlocal` smoke tests (do plan 05-21). Marca `pytest.mark.azure` + skip default.
- [ ] **P3.2** Documentar fluxo `LS_LOG=trace AZURE_PERSIST=1 localstack start` em `TESTING_LOCAL.md`.

### Phase 4 — Azure Sprint D (Tier-2)

- [ ] **P4.1** ARM spec ingest stub (`azure/api/<ns>/types.py` gerado de mock spec).
- [x] **P4.2** Service Bus — `azure/services/servicebus/` (9 testes).
- [x] **P4.3** Event Grid — `azure/services/eventgrid/` (12 testes).
- [x] **P4.4** Table Storage — `azure/services/tablestorage/` (14 testes).

### Phase 5 — Cross-cloud edge unification

- [x] **P5.1** `cloud/edge.py` — `MultiCloudEdge` WSGI dispatcher (5 testes). Host-pattern matching via `CloudProvider.edge_hosts`, fallback opcional via `default_cloud`, cache de gateway por nome.
- [ ] **P5.2** Smoke E2E: pingar AWS S3 + Azure Blob no mesmo port 4566 — depende de Phase 2 (mount real edge).

### Phase 7 — GCP Tier-1 (deste prompt) ✅

- [x] **P7.1** Plan doc `2026-05-22-gcp-services-parity.md` (Sprints A/B/C/D + guardrails).
- [x] **P7.2** Core primitives `gcp/` (exceptions, resource_names, scope, stores, spec, defaults, resource_manager, serializers).
- [x] **P7.3** Handlers chain (AuthHandler/RequestContextHandler/ErrorSerializerHandler/HandlerChain/GcpRequestContext).
- [x] **P7.4** Gateway `gcp/gateway.py` (host+path-based dispatch p/ storage/pubsub/firestore/functions/iam).
- [x] **P7.5** Plugin registry `gcp/plugins.py` + state `gcp/state.py` (snapshot/restore).
- [x] **P7.6** Tier-1 services completos:
  - Cloud Storage (GCS) — JSON + XML routers (S3-compat), 18 testes
  - Pub/Sub — topics+subs+publish+pull+ack, 9 testes
  - Firestore — databases+collections+documents CRUD, 10 testes
  - Cloud Functions — control plane + HTTP invoke + registry, 8 testes
  - IAM/STS — OAuth2 token mint (HS256 JWT mock) + service accounts CRUD, 11 testes
- [x] **P7.7** Registrar `gcp` em `cloud/builtin.py` + 9 edge_hosts.
- [x] **P7.8** Suite `tests/unit/gcp/` — 123/123 green; combined `azure+cloud+gcp` = 332/332.

### Phase 7B — GCP Tier-2 ✅

- [x] **P7B.1** BigQuery — datasets+tables+jobs+insertAll+query stub, 14 testes
- [x] **P7B.2** Secret Manager — secrets+versions+access+disable/enable/destroy, 14 testes
- [x] **P7B.3** Cloud KMS — keyRings+cryptoKeys+versions+encrypt/decrypt(XOR mock), 13 testes
- [x] **P7B.4** Cloud Tasks — queues+pause/resume+tasks+run, 13 testes
- [x] **P7B.5** Cloud Run — services+revisions+generation+updateTraffic, 13 testes
- [x] **P7B.6** Cloud Logging — entries:write/list+filter(severity/logName/AND)+sinks+10k cap, 13 testes
- [x] **P7B.7** Gateway hosts adicionados: bigquery/secretmanager/cloudkms/cloudtasks/run/logging .googleapis.com + path fallbacks.
- [x] **P7B.8** `cloud/builtin.py` edge_hosts expandido (+6 hosts).
- [x] **P7B.9** `gcp/__init__.py`, `plugins.py`, `defaults.py` registram providers Tier-2.
- [x] **P7B.10** Suite `tests/unit/gcp/` — 203/203 green; combined `azure+cloud+gcp` = 412/412 em 0.63s.

### Phase 7C — GCP Tier-3 ✅

- [x] **P7C.1** Cloud SQL — instances+databases+users+patch, 15 testes
- [x] **P7C.2** Cloud Scheduler — jobs+pause/resume/run+http/pubsub targets, 13 testes
- [x] **P7C.3** Cloud DNS — managedZones+rrsets+changes(add/delete)+SOA/NS defaults, 14 testes
- [x] **P7C.4** Spanner — instances+databases+sessions+executeSql stub+ddl, 15 testes
- [x] **P7C.5** Memorystore (Redis) — instances+patch+failover(STANDARD_HA only), 13 testes
- [x] **P7C.6** Gateway hosts: sqladmin/cloudscheduler/dns/spanner/redis .googleapis.com + path fallbacks (incl. disambiguation Spanner vs Memorystore por `/locations/`).
- [x] **P7C.7** `cloud/builtin.py` edge_hosts +5 hosts (total 20).
- [x] **P7C.8** `gcp/__init__.py`, `plugins.py`, `defaults.py` registram providers Tier-3 (17 plugins total).
- [x] **P7C.9** `test_multi_cloud_edge_gcp.py` ampliado: 17/17 green incl. todos hosts Tier-2/Tier-3.
- [x] **P7C.10** Suite `tests/unit/gcp/` — 287/287 green; combined `azure+cloud+gcp` = **494/494 em 0.60s**.

### Phase 6 — Docs + commits

- [ ] **P6.1** Atualizar `README.md` mencionando suporte multi-cloud experimental Azure.
- [ ] **P6.2** Splittar trabalho em PRs lógicos:
  - PR 1: `services/→aws/services/` (refactor mecânico).
  - PR 2: Azure core + Sprint A (data plane).
  - PR 3: Azure Sprint B + cloud/ meta-registry.
  - PR 4: Azure Sprint C/D.
  - PR 5: Reorg `platform/`+`tooling/`.

---

## Bloqueios técnicos conhecidos

1. **Subagents indisponíveis**: 12 tentativas, "Prompt is too long" mesmo com payload `ls`/`echo ok`. Sessão herda system prompt > budget subagent. Toda execução paralela vira sequencial.
2. **Context-mode MCP offline**: tools `ctx_*` indisponíveis nesta sessão.
3. **AWS suite custo**: ~8+ minutos por run. Iteração lenta entre refactors.
4. **Pré-condições Python**: env conda c/ python 3.13 + `cbor2<6` + `setuptools_scm`. Doc em `TESTING_LOCAL.md`.

## Critérios de "feito" (cada phase)

- Phase 0: AWS suite ≥ 90% pass rate (alguns testes podem precisar deps opcionais).
- Phase 1: 3 suites verdes (AWS unit + Azure + Cloud).
- Phase 2: smoke E2E via curl OK contra edge real.
- Phase 3-4: novos testes unit verde + plan checkboxes `[x]`.
- Phase 5: dois clouds respondendo no mesmo edge.
- Phase 6: PRs revisados + merged.
