# Multi-Cloud Organization Plan

> Objetivo: organizar `localstack-core/localstack/` para suportar AWS, Azure e clouds futuras (GCP, OCI, AliCloud) sob padrão único de pastas, com contexto/comandos isolados por cloud.

---

## 1. Princípio

Cada cloud é um **módulo top-level** sob `localstack-core/localstack/<cloud>/` com a mesma forma estrutural. Comportamento específico fica dentro do módulo; nada vaza para fora.

## 2. Layout canônico (contrato)

Todo módulo cloud DEVE conter (ou expor através de `__init__.py`):

```
localstack-core/localstack/<cloud>/
├── __init__.py             # exports públicos
├── exceptions.py           # erros base da cloud (status_code + code)
├── ids.py                  # parsing/formatting de identificadores nativos (ARN, ResourceId, FullResourceName, ...)
├── scope.py                # contexto de chamada (account/subscription/project + region/location/zone)
├── stores.py               # estruturas de estado in-memory (bundles por escopo)
├── state.py                # snapshot/restore (pickle, JSON, etc)
├── spec.py                 # registry de specs (api versions × resource types × locations)
├── plugins.py              # registry de providers + iter_builtin_plugins()
├── handlers.py (ou handlers/)  # middleware chain (auth, context, error serializer)
├── gateway.py              # WSGI/HTTP dispatcher para edge
├── services/               # implementações por serviço
│   └── <service>/
│       ├── __init__.py
│       ├── provider.py     # API control plane + data plane direto Python
│       ├── models.py       # dataclasses de estado
│       └── *_router.py     # adaptadores REST/HTTP (opcional)
└── api/ (opcional)         # tipos gerados de specs oficiais (não editar à mão)
```

**Convenções por cloud:**

| Conceito | AWS | Azure | GCP (futuro) |
| --- | --- | --- | --- |
| Conta tenant | account id | tenant + subscription | project |
| Região | region | location | region (+ zone) |
| ID recurso | ARN | Azure Resource ID | FullResourceName |
| Auth | SigV4 / IAM | OAuth2 Bearer (Entra ID) | OAuth2 Bearer + ADC |
| Path edge | `*.amazonaws.com` | `*.core.windows.net`, `*.azure.com` | `*.googleapis.com` |
| Spec catalog | botocore | resource-manager-schemas / ARM | discovery docs |

## 3. Meta-registry `cloud/`

Novo namespace `localstack-core/localstack/cloud/` agrega clouds:

```
localstack-core/localstack/cloud/
├── __init__.py
├── base.py      # CloudProvider dataclass (nome, gateway_factory, state_factory, plugin_registry_factory)
├── registry.py  # CloudRegistry singleton + register/get/list
└── builtin.py   # register('aws', ...) + register('azure', ...) — lazy imports
```

Permite descobrir clouds disponíveis (`from localstack.cloud import registry; registry.list()`) e instanciar gateway por nome.

## 4. Tasks

- [x] Plan criado.
- [x] `cloud/base.py` — `CloudProvider` dataclass com factories lazy.
- [x] `cloud/registry.py` — `CloudRegistry` + singleton.
- [x] `cloud/builtin.py` — registra AWS + Azure com factories lazy.
- [x] `tests/unit/cloud/test_cloud_registry.py` — 8 testes.
- [x] `tests/unit/cloud/test_cloud_builtin.py` — 7 testes.
- [ ] Atualizar `CLAUDE.md` referenciando este padrão (opcional).

## 5. Como adicionar uma cloud nova (ex: GCP)

1. Criar `localstack-core/localstack/gcp/` com layout canônico (seção 2).
2. Implementar mínimo: `exceptions`, `ids`, `scope`, `stores`, `spec`, `plugins`, `gateway`, `services/<primeiro-svc>/provider`.
3. Adicionar entrada em `localstack/cloud/builtin.py`: `register("gcp", gateway_factory=lambda: GcpGateway(), state_factory=GcpStateStore, ...)`.
4. Testes em `tests/unit/gcp/` espelhando `tests/unit/azure/`.
5. Não tocar em `aws/` ou `azure/`.

## 6. Guardrails

- ❌ NÃO compartilhar `stores.py` ou `state.py` entre clouds — cada cloud isola seu schema.
- ❌ NÃO referenciar AWS dentro de `azure/` ou `gcp/` (e vice-versa). Comunicação cross-cloud, se necessária, vai via `cloud/` ou ports.
- ❌ NÃO impor uma classe base abstrata Python em todos os providers — padrão é estrutural (ducktype), validado por testes de existência de atributos/métodos no `__init__.py` de cada cloud.
- ❌ NÃO mover ou renomear o módulo `aws/` legado.
