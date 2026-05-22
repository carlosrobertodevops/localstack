# TESTING_LOCAL.md — Testando o LocalStack como AWS, Azure e GCP em desenvolvimento

Guia prático para subir e exercitar o LocalStack localmente nos três clouds suportados (AWS estável, Azure e GCP experimentais), durante o ciclo de desenvolvimento neste repositório.

Estrutura do runtime (pós-reorganização multi-cloud):

```
localstack-core/localstack/
├── aws/         # cloud AWS (gateway + handlers + services/ + api/)
├── azure/       # cloud Azure (experimental)
├── cloud/       # meta-registry (CloudProvider, CloudRegistry, MultiCloudEdge)
├── gcp/         # cloud GCP (experimental)
├── platform/    # runtime, state, dns, http, logging, config.py, constants.py, plugins.py, version.py
├── tooling/     # cli, dev, extensions, testing, packages
└── utils/       # utilitários transversais
```

---

## 1. Pré-requisitos

| Item              | Valor                                | Origem               |
| ----------------- | ------------------------------------ | -------------------- |
| Python            | `>=3.10`                             | `pyproject.toml:13`  |
| boto3 / botocore  | `==1.42.59` (pin para o gerador ASF) | `CLAUDE.md`          |
| Docker (opcional) | qualquer versão recente              | `docker-compose.yml` |
| Make              | GNU make 3.81+                       | `Makefile`           |

Setup inicial (cria `.venv/` automaticamente):

```bash
make install            # full dev install (= install-dev)
make entrypoints        # gera plux.ini (re-execute após adicionar/remover plugins)
```

---

## 2. Subindo o runtime

### 2.1. Via `make start` (recomendado para dev)

```bash
make start
# = python3 -m localstack.platform.runtime.main
```

- Porta padrão: **`:4566`** (gateway de edge, ver `localstack-core/localstack/platform/runtime/runtime.py:115`).
- Sobrescrita: `GATEWAY_LISTEN=0.0.0.0:4566`.

### 2.2. Via docker-compose (caminho de imagem)

```bash
docker compose up
```

- Mapeia `127.0.0.1:4566` + faixa `4510-4559` para serviços externos (ver `docker-compose.yml`).
- Use quando precisar testar a imagem `localstack/localstack` empacotada.

### 2.3. Variáveis úteis

| Var                                               | Efeito                                            |
| ------------------------------------------------- | ------------------------------------------------- |
| `DEBUG=1`                                         | logs verbosos do runtime                          |
| `GATEWAY_LISTEN=0.0.0.0:4566`                     | host/porta do edge                                |
| `SERVICES=s3,sqs`                                 | restringe providers ativos (acelera startup)      |
| `PERSISTENCE=1`                                   | habilita state snapshots em `/var/lib/localstack` |
| `LOCALSTACK_HOST=localhost.localstack.cloud:4566` | hostname canônico para SDKs                       |

---

## 3. AWS — fluxo padrão

### 3.1. Smoke test

```bash
# Credenciais dummy aceitas
export AWS_ACCESS_KEY_ID=test AWS_SECRET_ACCESS_KEY=test AWS_DEFAULT_REGION=us-east-1

aws --endpoint-url=http://localhost:4566 s3 mb s3://teste
aws --endpoint-url=http://localhost:4566 s3 ls
aws --endpoint-url=http://localhost:4566 sqs create-queue --queue-name fila-dev
```

Ou via boto3:

```python
import boto3
s3 = boto3.client("s3", endpoint_url="http://localhost:4566",
                  aws_access_key_id="test", aws_secret_access_key="test", region_name="us-east-1")
s3.create_bucket(Bucket="teste")
print(s3.list_buckets()["Buckets"])
```

### 3.2. Testes unitários

```bash
pytest tests/unit/aws/ -q
pytest tests/unit/utils/ -q
```

### 3.3. Testes de paridade (integração)

```bash
# Contra LocalStack local (default)
pytest tests/aws/services/s3/ -q

# Contra AWS real + refresh de snapshots
AWS_PROFILE=<perfil> TEST_TARGET=AWS_CLOUD SNAPSHOT_UPDATE=1 \
  pytest tests/aws/services/s3/test_s3.py -k test_basic_upload
```

> Todo teste em `tests/aws/` exige marker de compatibilidade. Valide com:
>
> ```bash
> make check-aws-markers
> ```

### 3.4. Onde o código vive

| Camada                  | Caminho                                                     |
| ----------------------- | ----------------------------------------------------------- |
| Providers (editáveis)   | `localstack-core/localstack/aws/services/<svc>/provider.py` |
| API gerada (NÃO EDITAR) | `localstack-core/localstack/aws/api/<svc>/`                 |
| Registry de providers   | `localstack-core/localstack/aws/services/providers.py`      |
| Gateway                 | `localstack-core/localstack/aws/gateway.py`                 |

---

## 4. Azure — fluxo experimental

### 4.1. Status

Implementação **experimental**. O `AzureGateway` existe em `localstack-core/localstack/azure/gateway.py:49` e é registrado no meta-registry (`localstack-core/localstack/cloud/builtin.py:62`), mas **ainda não está montado na porta de edge :4566** — isso é Phase 2 do roteiro multi-cloud (ver `docs/superpowers/plans/2026-05-22-multi-cloud-organization.md`).

Hoje você exercita o Azure por:

- testes unitários em `tests/unit/azure/`;
- WSGI in-process via `MultiCloudEdge` (`localstack-core/localstack/cloud/edge.py`);
- chamadas diretas ao `AzureGateway()` em REPL.

### 4.2. Subindo o gateway em REPL

```python
from werkzeug.serving import run_simple
from localstack.cloud import register_builtins, registry

register_builtins()                       # registra aws, azure, gcp no registry default
azure = registry.get("azure")
gateway = azure.build_gateway()           # instancia AzureGateway()
run_simple("127.0.0.1", 4571, gateway, use_reloader=False)
```

### 4.3. Smoke test (porta dedicada do REPL acima)

```bash
# Health-check direto na rota ARM
curl -i http://127.0.0.1:4571/subscriptions
```

Cliente Azure (após o gateway responder):

```bash
pip install azure-storage-blob
```

```python
from azure.storage.blob import BlobServiceClient
client = BlobServiceClient(
    account_url="http://127.0.0.1:4571",
    credential={"account_name": "devstoreaccount1", "account_key": "Eby8..."},
)
print([c.name for c in client.list_containers()])
```

### 4.4. Testes unitários

```bash
pytest tests/unit/azure/ -q
pytest tests/unit/azure/services/test_blob_router.py -q
```

### 4.5. Onde o código vive

| Item        | Caminho                                            |
| ----------- | -------------------------------------------------- |
| Gateway     | `localstack-core/localstack/azure/gateway.py`      |
| Routers ARM | `localstack-core/localstack/azure/arm_router.py`   |
| Providers   | `localstack-core/localstack/azure/services/<svc>/` |
| Plugins     | `localstack-core/localstack/azure/plugins.py`      |
| Testes      | `tests/unit/azure/`                                |

---

## 5. GCP — fluxo experimental

### 5.1. Status

Implementação **experimental**. `GcpGateway` em `localstack-core/localstack/gcp/gateway.py:72`, registrado em `localstack-core/localstack/cloud/builtin.py:128`. Também não montado em :4566 (Phase 2).

**Restrições não-negociáveis** (mantenha durante dev):

- ❌ SDKs `google-cloud-*` **não** entram no core, **apenas** em test extras.
- ❌ Testes GCP **não** vão para `tests/aws/**` nem `tests/unit/azure/**`.
- ❌ GCP **não** reutiliza fallback do Moto.
- ❌ Não usar markers AWS/Azure em testes GCP.

### 5.2. Subindo o gateway em REPL

```python
from werkzeug.serving import run_simple
from localstack.cloud import register_builtins, registry

register_builtins()
gcp = registry.get("gcp")
gateway = gcp.build_gateway()             # instancia GcpGateway()
run_simple("127.0.0.1", 4572, gateway, use_reloader=False)
```

### 5.3. Smoke test

```bash
curl -i http://127.0.0.1:4572/v1/projects/local-dev/topics
```

Com `gcloud` (sobrescrevendo o endpoint de uma API específica):

```bash
gcloud config set api_endpoint_overrides/storage http://127.0.0.1:4572/
gcloud storage buckets list --project=local-dev
```

Cliente Python (instale como **extra de teste**, jamais no core):

```bash
pip install 'google-cloud-storage' 'google-cloud-pubsub'    # somente para o seu ambiente de dev
```

```python
import os
os.environ["STORAGE_EMULATOR_HOST"] = "http://127.0.0.1:4572"
from google.cloud import storage
client = storage.Client(project="local-dev")
print([b.name for b in client.list_buckets()])
```

### 5.4. Testes unitários

```bash
pytest tests/unit/gcp/ -q
pytest tests/unit/gcp/services/test_pubsub.py -q
```

### 5.5. Onde o código vive

| Item                | Caminho                                                                     |
| ------------------- | --------------------------------------------------------------------------- |
| Gateway             | `localstack-core/localstack/gcp/gateway.py`                                 |
| Routers/Serializers | `localstack-core/localstack/gcp/{handlers,serializers,resource_manager}.py` |
| Providers           | `localstack-core/localstack/gcp/services/<svc>/`                            |
| Plugins             | `localstack-core/localstack/gcp/plugins.py`                                 |
| Testes              | `tests/unit/gcp/`                                                           |

---

## 6. Multi-cloud — registry e edge unificado

### 6.1. Como o registry liga as clouds

`localstack-core/localstack/cloud/base.py:17` define o dataclass `CloudProvider` (campos: `name`, `display_name`, `package`, `gateway_factory`, `state_store_factory`, `plugin_registry_factory`, `edge_hosts`, `metadata`). `localstack-core/localstack/cloud/builtin.py:56` (`register_builtins`) registra `aws`, `azure`, `gcp` no `CloudRegistry` default. É idempotente.

### 6.2. Enumerar clouds disponíveis

```python
from localstack.cloud import register_builtins, registry
register_builtins()
print([c.name for c in registry])           # ['azure', 'aws', 'gcp']
print(registry.get("gcp").display_name)     # 'Google Cloud Platform'
```

### 6.3. Edge unificado por host (`MultiCloudEdge`)

`localstack-core/localstack/cloud/edge.py` expõe um WSGI app que roteia por sufixo de host para o gateway correto, usando `edge_hosts` declarados por cada cloud. Útil para um único listener atender AWS + Azure + GCP por nome de host:

```python
from werkzeug.serving import run_simple
from localstack.cloud import register_builtins
from localstack.cloud.edge import MultiCloudEdge

register_builtins()
run_simple("0.0.0.0", 4566, MultiCloudEdge(default_cloud="aws"))
```

Com isso, requisições para `*.amazonaws.com` vão para AWS, `*.blob.core.windows.net` para Azure, `*.googleapis.com` para GCP, e o fallback é AWS.

### 6.4. Plugins / entry points

Plugins ASF + multi-cloud são descobertos via Plux. Sempre que adicionar/renomear plugin ou cloud, regenere:

```bash
make entrypoints
```

Sem isso, o registry silenciosamente não encontra o provider novo.

---

## 7. Comandos do dia-a-dia

| Comando                          | Função                                                  |
| -------------------------------- | ------------------------------------------------------- |
| `make install`                   | venv + deps de dev                                      |
| `make entrypoints`               | regenera `plux.ini`                                     |
| `make start`                     | sobe o runtime AWS local em :4566                       |
| `make lint`                      | ruff + format check + openapi validator + mypy + deptry |
| `make lint-modified`             | mesmo, só arquivos modificados                          |
| `make format`                    | aplica `ruff check --fix` + `ruff format`               |
| `make format-modified`           | só arquivos modificados                                 |
| `make check-aws-markers`         | valida markers em `tests/aws/`                          |
| `make test TEST_PATH=tests/unit` | pytest com wrapper Make                                 |
| `make docker-run-tests`          | suíte dentro do container `localstack` (usa `dist/`)    |

---

## 8. Snapshot / parity testing — regras de ouro

1. Sempre **antes** do `snapshot.match()`, registre transformers para valores não-determinísticos.
2. Prefira `snapshot.add_transformer(snapshot.transform.key_value("FooArn"))`. Use `snapshot.transform.regex(value, "<placeholder>")` apenas se a chave não basta.
3. Ordenação determinística:
   ```python
   from localstack.tooling.testing.snapshots.transformer import SortingTransformer
   snapshot.add_transformer(SortingTransformer("Items", lambda x: x["Key"]))
   ```
4. Refresh contra AWS real:
   ```bash
   AWS_PROFILE=<perfil> TEST_TARGET=AWS_CLOUD SNAPSHOT_UPDATE=1 pytest <path>
   ```

---

## 9. Troubleshooting

| Sintoma                                                                                                               | Causa                                                            | Correção                                                                                                                                        |
| --------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- | ------- | --------- | ----------------------------------------- | ---------------------------------------------------------------- |
| `ModuleNotFoundError: No module named 'localstack.config'`                                                            | Imports antigos pré-reorganização (módulo foi para `platform/`). | Ajuste para `from localstack.platform import config` ou `from localstack.platform.config import ...`.                                           |
| `cannot import name 'X' from 'localstack'` (X ∈ runtime, state, dns, http, logging, constants, deprecations, plugins) | Mesmo caso acima.                                                | Reescreva para `localstack.platform.X`.                                                                                                         |
| `ModuleNotFoundError` para `localstack.cli                                                                            | dev                                                              | extensions                                                                                                                                      | testing | packages` | Esses subpacotes mudaram para `tooling/`. | Use `localstack.tooling.cli`, `localstack.tooling.testing`, etc. |
| `plux entrypoints` falha com `localstack-pro does not exist`                                                          | Plugin externo opcional ausente.                                 | Ignorar — não bloqueia o dev.                                                                                                                   |
| `setuptools_scm` reclama de `version.py`                                                                              | Arquivo foi para `platform/version.py` (gitignored).             | Confirme em `pyproject.toml` que `version_file = "localstack-core/localstack/platform/version.py"` e em `.gitignore` que a linha está presente. |
| `make check-aws-markers` falhando após adicionar teste em `tests/aws/`                                                | Faltou marker.                                                   | Adicione `@pytest.mark.aws_validated` (ou `aws_only` / `aws_needs_fixing`) conforme o caso.                                                     |
| `Port 4566 in use` ao rodar `make start`                                                                              | Container `localstack-main` antigo segurando a porta.            | `docker rm -f localstack-main` ou ajuste `GATEWAY_LISTEN=0.0.0.0:4567`.                                                                         |
| `make lint` reclama de `localstack-core/localstack/__init__.py` existir                                               | Esse arquivo **não** pode existir (quebra namespace package).    | `rm localstack-core/localstack/__init__.py`.                                                                                                    |
| Provider novo não é descoberto                                                                                        | `plux.ini` desatualizado.                                        | `make entrypoints`.                                                                                                                             |
| Teste GCP demanda marker AWS                                                                                          | Marker errado no decorator.                                      | Use markers específicos do escopo GCP (ou nenhum); ver constraints da §5.1.                                                                     |

---

## 10. Referências

- Visão geral da arquitetura: `docs/localstack-concepts/README.md`
- Testes (parity, snapshot, integração): `docs/testing/`
- Roteiro multi-cloud: `docs/superpowers/plans/2026-05-22-multi-cloud-organization.md`
- Notas de contribuição: `AGENTS.md`, `CLAUDE.md`
