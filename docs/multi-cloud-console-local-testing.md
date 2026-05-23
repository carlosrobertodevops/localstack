# Multi-cloud Console — Manual de Testes e Execução Local

Guia único para subir, testar e operar o LocalStack fork + console multi-cloud
**usando a imagem que construímos a partir deste repositório**
(`localstack/localstack-custom`), **não a imagem oficial `localstack/localstack`**.

Combina visão conceitual + cheatsheet comando-a-comando.

---

## 0. Diferença em relação ao LocalStack upstream

| Item                              | Upstream (`localstack/localstack`) | Este fork (`localstack/localstack-custom`)                     |
| --------------------------------- | ---------------------------------- | -------------------------------------------------------------- |
| Provider AWS                      | Padrão                             | Padrão                                                         |
| Provider Azure                    | —                                  | Experimental (`localstack/azure/**`)                           |
| Provider GCP (registry)           | —                                  | `CloudRegistry` + GCP skin no console                          |
| Endpoints `_localstack/console/*` | —                                  | `cli`, `iac`, `iac/preview`, `sessions/<id>/log`               |
| Endpoint `_localstack/clouds`     | —                                  | Lista clouds registradas + health                              |
| Bridge CLI host (`:4578`)         | —                                  | `bin/console-cli-bridge` (aiohttp)                             |
| Console SPA                       | —                                  | `localstack-ui/console/` (React 19 + Vite + Tailwind + shadcn) |

**Nunca use `image: localstack/localstack` no `docker-compose.yml`** — você
perde os endpoints do console e o registry multi-cloud. O compose já vem
apontado para `${LOCALSTACK_IMAGE:-localstack/localstack-custom}`.

---

## 1. Atalho — do zero ao console em 5 passos

```bash
make install                                                       # 1. venv + deps Python
make entrypoints                                                   # 2. plux.ini
IMAGE_NAME=localstack/localstack-custom make docker-build          # 3. imagem do fork
make console-install && make console-build                         # 4. SPA (bun)
docker compose up -d localstack localstack-ui                      # 5. stack
open http://localhost:4577
```

---

## 2. Pré-requisitos

| Ferramenta     | Versão mínima    | Verificar                |
| -------------- | ---------------- | ------------------------ |
| Python         | 3.10+            | `python3 --version`      |
| Bun            | 1.3+             | `bun -v`                 |
| Docker         | 24+              | `docker -v`              |
| Docker Compose | v2+              | `docker compose version` |
| AWS CLI        | 2.x (opcional)   | `aws --version`          |
| Azure CLI      | 2.55+ (opcional) | `az version`             |
| gcloud CLI     | 460+ (opcional)  | `gcloud --version`       |
| Terraform      | 1.6+ (opcional)  | `terraform -v`           |

Bun em falta:

```bash
curl -fsSL https://bun.sh/install | bash
```

---

## 3. Setup de ambiente Python

```bash
make install                # cria .venv + instala localstack-core[dev]
source .venv/bin/activate
make entrypoints            # regenera plux.ini (obrigatório p/ providers serem descobertos)

# Lint / format
make lint                   # ruff + ruff format --check + mypy + deptry
make format                 # ruff check --fix + ruff format
make lint-modified          # scoped p/ git-modified .py
make format-modified
```

> Pular `make entrypoints` é a fonte #1 de "endpoint X 404" — o Plux registry
> não enxerga providers novos sem `plux.ini` atualizado.

---

## 4. Build da imagem do fork

A imagem é construída a partir do `Dockerfile` na raiz via
`bin/docker-helper.sh`. Empacota `localstack-core` atual + entrypoints +
providers do fork.

```bash
# Build padrão (tag: localstack/localstack:latest)
make docker-build

# Build com a tag que o docker-compose espera por default
IMAGE_NAME=localstack/localstack-custom make docker-build

# Tag custom (ex.: :dev) — exporte LOCALSTACK_IMAGE depois
IMAGE_NAME=localstack/localstack-custom DEFAULT_TAG=dev make docker-build
export LOCALSTACK_IMAGE=localstack/localstack-custom:dev

# Build linux/amd64 em Apple Silicon (parity com CI)
IMAGE_NAME=localstack/localstack-custom PLATFORM=linux/amd64 make docker-build

# Listar imagens construídas
docker image ls localstack/localstack-custom

# Remover imagem
docker image rm localstack/localstack-custom:latest
```

> Tag default do compose: `localstack/localstack-custom:latest`.
> Para outra tag, exporte `LOCALSTACK_IMAGE=localstack/localstack-custom:dev`.

---

## 5. Subir / derrubar a stack

```bash
# Subir só o LocalStack
docker compose up -d localstack

# Subir LocalStack + nginx sidecar (SPA em :4577)
docker compose up -d localstack localstack-ui

# Subir tudo
docker compose up -d

# Status + logs
docker compose ps
docker compose logs -f localstack
docker compose logs -f localstack-ui

# Restart sem rebuild
docker compose restart localstack

# Force recreate (depois de alterar env/compose)
docker compose up -d --force-recreate localstack

# Down (preserva volume)
docker compose down

# Down + volumes (estado limpo)
docker compose down -v
```

---

## 6. Verificar que está rodando o fork

```bash
# Health geral
curl -s http://localhost:4566/_localstack/health | jq

# Clouds registradas (só existe no fork)
curl -s http://localhost:4566/_localstack/clouds | jq
# Esperado: { "clouds": [ { "name": "aws", ... }, { "name": "azure", ... } ] }

# Imagem que o container está usando
docker inspect localstack-main --format '{{.Config.Image}}'

# Versão do localstack-core dentro do container
docker exec localstack-main localstack --version
```

Se `/clouds` retornar 404 → está rodando upstream. Rebuild com
`IMAGE_NAME=localstack/localstack-custom make docker-build` e recreate
o container.

---

## 7. Console SPA (bun + Vite + Tailwind + shadcn)

### 7.1. Via make targets

```bash
make console-install        # bun install
make console-dev            # vite dev server em :5173
make console-build          # tsc -b && vite build → dist/
make console-lint           # eslint + tsc --noEmit
make console-test           # vitest run
make console-test-e2e       # playwright (requer stack)
```

### 7.2. Direto pelo bun (sem make)

```bash
cd localstack-ui/console
bun install
bun run dev
bun run build
bun run typecheck
bun run lint
bun run test
bun run test:e2e
```

### 7.3. Reinstalar do zero

```bash
rm -rf localstack-ui/console/{node_modules,bun.lock,dist}
make console-install
```

Vite proxy: `/_localstack/*` → `:4566`; `/_bridge/*` → `:4578`.

---

## 8. Bridge CLI host-side (`:4578`)

Executa `aws`, `az`, `gcloud` na **sua máquina** com credenciais reais
quando o Cloud Shell drawer precisa de algo fora do escopo do container.
Bridge offline → SPA cai automaticamente para `/_localstack/console/cli`
(in-container).

```bash
# Instalar deps do bridge (cria .venv-bridge)
make console-bridge-install

# Foreground em :4578
make console-bridge

# Background (sem make)
nohup bin/console-cli-bridge --host 127.0.0.1 --port 4578 > bridge.log 2>&1 &
echo $! > bridge.pid

# Healthcheck
curl -s http://127.0.0.1:4578/health | jq

# Parar
kill "$(cat bridge.pid)" && rm bridge.pid
```

Allowlist (enforced no bridge **e** no in-container endpoint):
`aws`, `az`, `gcloud`. Outros → 400 unsupported cli.

---

## 9. Endpoints internos do console (curl direto)

```bash
# Render preview (provider.tf + main.tf)
curl -s -X POST http://localhost:4566/_localstack/console/iac/preview \
  -H 'content-type: application/json' \
  -d '{"tool":"terraform","snippet":"resource \"aws_s3_bucket\" \"x\" { bucket = \"x\" }"}' \
  | jq

# Aplicar IaC
curl -s -X POST http://localhost:4566/_localstack/console/iac \
  -H 'content-type: application/json' \
  -d '{"tool":"terraform","snippet":"resource \"aws_s3_bucket\" \"y\" { bucket = \"y\" }","action":"apply"}' \
  | jq

# Ler log de uma sessão IaC
SESSION_ID=<id-retornado-acima>
curl -s "http://localhost:4566/_localstack/console/sessions/${SESSION_ID}/log"

# CLI passthrough (in-container)
curl -s -X POST http://localhost:4566/_localstack/console/cli \
  -H 'content-type: application/json' \
  -d '{"cli":"aws","args":["s3","ls"]}' | jq

# Allowlist check (deve retornar 400)
curl -s -X POST http://localhost:4566/_localstack/console/cli \
  -H 'content-type: application/json' -d '{"cli":"evil","args":[]}'
```

---

## 10. Roteiros de teste pela UI

Abra `http://localhost:4577` (build) ou `http://localhost:5173` (dev).
Use o **cloud picker** na TopBar para alternar skin + serviços.

### 10.1. AWS · S3

1. `/aws/s3` → **Create bucket** → `demo-bucket`
2. Lista atualiza → click no bucket → detail page.
3. **Show as Terraform** → drawer abre:
   ```hcl
   resource "aws_s3_bucket" "demo_bucket" { bucket = "demo-bucket" }
   ```
4. **Preview** → `POST /_localstack/console/iac/preview` retorna
   `provider.tf` (apontando para `localhost:4566`) + `main.tf`.
5. **Apply** → cria estado real. CLI sanity check:
   ```bash
   aws --endpoint-url=http://localhost:4566 s3 ls
   ```
6. **Delete bucket** na UI; confirme via CLI.

### 10.2. AWS · SQS · DynamoDB · Lambda

| Rota            | Ação                                                                     |
| --------------- | ------------------------------------------------------------------------ |
| `/aws/sqs`      | Create queue → Send message → Receive                                    |
| `/aws/dynamodb` | Create table (PK = `id`) → Scan                                          |
| `/aws/lambda`   | Create function (Runtime `python3.12`, zip base64 default) → Invoke `{}` |

### 10.3. Azure · Resource Groups + Storage

1. Troque para **Azure**.
2. `/azure/resource-groups` → Create RG `rg-demo` (location `eastus`).
3. `/azure/storage-accounts` → Create `stdemo` no RG `rg-demo`.
4. CLI: `bin/azurelocal group list --output table` (wrapper).

### 10.4. GCP · Storage + Pub/Sub

1. Troque para **GCP**.
2. `/gcp/storage` → Create bucket `gcs-demo`.
3. `/gcp/pubsub` → Create topic `topic-demo`.
4. CLI: `gcloud --configuration=localstack storage ls`.

---

## 11. Cloud Shell drawer

1. Botão flutuante (canto inferior direito) → abre drawer com xterm.
2. Comandos: `aws s3 ls`, `az group list`, `gcloud storage ls`.
3. Histórico em `localStorage` (`localstack-console:shell-history`); ↑/↓.
4. Allowlist enforced (`aws|az|gcloud`); outros → 400.

---

## 12. IaC inline drawer (Terraform / Serverless)

Em qualquer página de recurso, clique em **Show as Terraform**:

| Botão   | Endpoint                                         | Efeito                     |
| ------- | ------------------------------------------------ | -------------------------- |
| Copy    | (client-side)                                    | Copia para clipboard       |
| Preview | `POST /_localstack/console/iac/preview`          | `provider.tf` + `main.tf`  |
| Plan    | `POST /_localstack/console/iac` (action=plan)    | `terraform plan` na sessão |
| Apply   | `POST /_localstack/console/iac` (action=apply)   | Provisiona contra `:4566`  |
| Destroy | `POST /_localstack/console/iac` (action=destroy) | Remove o recurso           |

Log da sessão: `GET /_localstack/console/sessions/<session_id>/log`.

---

## 13. CLIs e ferramentas IaC apontadas para o LocalStack

### 13.1. Matriz de suporte

| Ferramenta           | Versão mínima | Bridge `/exec` | Endpoint `/_localstack/console/iac` | Wrapper repo       |
| -------------------- | ------------- | -------------- | ----------------------------------- | ------------------ |
| AWS CLI (`aws`)      | 2.15+         | ✅ allowlist   | n/a                                 | `bin/awslocal-dev` |
| Azure CLI (`az`)     | 2.60+         | ✅ allowlist   | n/a                                 | `bin/azurelocal`   |
| gcloud               | 470.0+        | ✅ allowlist   | n/a                                 | `bin/gcloudlocal`  |
| Terraform            | 1.6+          | n/a            | ✅ `tool: "terraform"`              | —                  |
| Serverless Framework | 3.38+         | n/a            | ✅ `tool: "serverless"`             | —                  |

Allowlists no código:

- Bridge host: `localstack-core/localstack/tooling/dev/console_bridge.py:35` → `CLI_ALLOWLIST = ("aws", "az", "gcloud")`
- IaC backend: `localstack-core/localstack/aws/services/internal.py:409` → `_IAC_TOOL_ALLOWLIST = ("terraform", "serverless")`
- Ações IaC: `("plan", "apply", "destroy")` (Terraform) · `("deploy", "remove", "package")` (Serverless)

### 13.2. AWS CLI

```bash
# Explícito
aws --endpoint-url=http://localhost:4566 s3 ls
aws --endpoint-url=http://localhost:4566 sqs list-queues
aws --endpoint-url=http://localhost:4566 dynamodb list-tables
aws --endpoint-url=http://localhost:4566 lambda list-functions

# Via env (evita repetir --endpoint-url)
export AWS_ENDPOINT_URL=http://localhost:4566
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION=us-east-1
aws s3 ls
```

### 13.3. Azure CLI

```bash
bin/azurelocal group list --output table
bin/azurelocal storage account list
```

### 13.4. gcloud

```bash
# Configuration 'localstack' apontando para o gateway
gcloud --configuration=localstack storage ls
gcloud --configuration=localstack pubsub topics list
```

### 13.5. Terraform

```bash
cat > /tmp/main.tf <<'EOF'
terraform {
  required_providers { aws = { source = "hashicorp/aws" } }
}
provider "aws" {
  region                      = "us-east-1"
  access_key                  = "test"
  secret_key                  = "test"
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true
  s3_use_path_style           = true
  endpoints { s3 = "http://localhost:4566" }
}
resource "aws_s3_bucket" "demo" { bucket = "demo-bucket" }
EOF
cd /tmp && terraform init && terraform apply -auto-approve
```

Via console (drawer IaC):

```bash
curl -s -X POST http://localhost:4566/_localstack/console/iac \
  -H 'content-type: application/json' \
  -d '{"tool":"terraform","action":"apply","snippet":"resource \"aws_s3_bucket\" \"demo\" { bucket = \"demo\" }"}'
```

### 13.6. Serverless Framework

Instalação host (uma vez):

```bash
npm install -g serverless@3
# ou via bun
bun add -g serverless@3
serverless --version   # >= 3.38
```

Plugin recomendado para LocalStack:

```bash
npm install -g serverless-localstack
```

Snippet mínimo `serverless.yml`:

```yaml
service: demo-fork
frameworkVersion: "3"
provider:
  name: aws
  runtime: python3.11
  region: us-east-1
plugins:
  - serverless-localstack
custom:
  localstack:
    stages: [local]
    host: http://localhost
    edgePort: 4566
functions:
  hello:
    handler: handler.hello
```

Deploy local (stage `local`, hardcoded pelo backend do console):

```bash
serverless deploy --stage local
serverless invoke --stage local -f hello
serverless remove --stage local
```

Via console (mesmo endpoint, `tool: "serverless"`):

```bash
SNIPPET=$(cat serverless.yml | jq -Rs .)
curl -s -X POST http://localhost:4566/_localstack/console/iac \
  -H 'content-type: application/json' \
  -d "{\"tool\":\"serverless\",\"action\":\"deploy\",\"snippet\":${SNIPPET}}"
```

> **Nota:** o backend roda `serverless <action> --stage local` no diretório de sessão (`~/.localstack/console-iac/<session>/`). Binário tem que estar no `PATH` do host onde o LocalStack roda (ou montado no container).

---

## 14. Testes automatizados

```bash
# Unit Python (validators do console)
source .venv/bin/activate
python -m pytest tests/unit/console/ -v
# Esperado: ~66 testes, 0 falhas

# Suite completa de unit Python
make test TEST_PATH=tests/unit

# Pytest direto (qualquer caminho)
pytest tests/aws/services/s3/

# Smoke contra LocalStack rodando (na nossa imagem)
docker compose up -d localstack
SKIP_CONSOLE_SMOKE=0 pytest tests/aws/test_console_endpoints_smoke.py -v

# Markers AWS (verifica que todo teste em tests/aws/* tem marker)
make check-aws-markers

# Rodar testes dentro da imagem custom (parity CI)
make docker-run-tests

# Unit TypeScript (vitest)
make console-test                   # 8/8

# E2E Playwright (sobe stack antes)
make console-build && docker compose up -d localstack localstack-ui
make console-test-e2e
```

Parity contra a AWS real (atualizar snapshots):

```bash
AWS_PROFILE=<seu_perfil> TEST_TARGET=AWS_CLOUD SNAPSHOT_UPDATE=1 \
  pytest tests/aws/services/s3/test_s3.py -k <test_name>
```

---

## 15. Logs / debug

```bash
# Logs do container
docker compose logs -f localstack
docker compose logs --tail 100 localstack

# DEBUG=1 (mais verboso)
DEBUG=1 docker compose up -d --force-recreate localstack

# Shell dentro do container
docker exec -it localstack-main bash

# Inspecionar volume de estado
ls volume/

# Limpar log de uma sessão IaC
rm -rf volume/console-sessions/<session_id>/
```

---

## 16. Reset / limpeza total

```bash
# Stack + estado
docker compose down -v
rm -rf volume/

# SPA build + node_modules
rm -rf localstack-ui/console/{node_modules,bun.lock,dist}

# Imagem custom
docker image rm localstack/localstack-custom:latest 2>/dev/null

# Reconstruir tudo
make install && make entrypoints
IMAGE_NAME=localstack/localstack-custom make docker-build
make console-install && make console-build
docker compose up -d localstack localstack-ui
open http://localhost:4577
```

---

## 17. Variáveis de ambiente

| Variável                     | Default                        | Onde                        |
| ---------------------------- | ------------------------------ | --------------------------- |
| `LOCALSTACK_IMAGE`           | `localstack/localstack-custom` | `docker-compose.yml`        |
| `LOCALSTACK_DOCKER_NAME`     | `localstack-main`              | `docker-compose.yml`        |
| `LOCALSTACK_VOLUME_DIR`      | `./volume`                     | `docker-compose.yml`        |
| `EXTRA_CORS_ALLOWED_ORIGINS` | `:4577,:5173,:4578,orb.local`  | `docker-compose.yml`        |
| `DEBUG`                      | `0`                            | `docker-compose.yml`        |
| `PERSISTENCE`                | `0`                            | `docker-compose.yml`        |
| `IMAGE_NAME`                 | `localstack/localstack`        | `Makefile` (`docker-build`) |
| `DEFAULT_TAG`                | `latest`                       | `Makefile`                  |
| `PLATFORM`                   | host                           | `Makefile`                  |
| `SKIP_CONSOLE_SMOKE`         | `1`                            | smoke tests                 |
| `LOCALSTACK_ENDPOINT`        | `http://localhost:4566`        | smoke tests                 |
| `AWS_ENDPOINT_URL`           | —                              | AWS CLI / SDK               |

Exemplos:

```bash
PERSISTENCE=1 docker compose up -d --force-recreate localstack
LOCALSTACK_IMAGE=localstack/localstack-custom:dev docker compose up -d localstack
LOCALSTACK_VOLUME_DIR=/tmp/ls-state docker compose up -d localstack
```

---

## 18. Troubleshooting

| Sintoma                                                     | Causa provável                                            | Ação                                                                                                            |
| ----------------------------------------------------------- | --------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| `curl :4566/_localstack/clouds` retorna 404                 | Compose subiu `localstack/localstack` (upstream)          | `IMAGE_NAME=localstack/localstack-custom make docker-build && docker compose up -d --force-recreate localstack` |
| Endpoint `_localstack/console/iac/preview` retorna 404      | Provider não foi registrado pelo Plux                     | Ativar venv → `make entrypoints` → `make docker-build` → recriar container                                      |
| Console em `:4577` carrega CSS mas dados vazios             | CORS bloqueando                                           | Confirme `EXTRA_CORS_ALLOWED_ORIGINS` no compose (inclui `:4577` e `:5173`)                                     |
| **Apply** falha com `terraform: not found`                  | `terraform` ausente do PATH do container                  | Usar bridge host (`make console-bridge`) ou montar volume com binário                                           |
| Cloud Shell mostra "bridge unavailable"                     | Worker `:4578` desligado                                  | Em outro terminal: `make console-bridge`                                                                        |
| `make docker-build` falha em Apple Silicon                  | `PLATFORM` default não bate com runtime                   | `PLATFORM=linux/arm64 make docker-build` (ou `linux/amd64` p/ CI parity)                                        |
| `bun install` falha em arm64 mac                            | Bun antigo                                                | `curl -fsSL https://bun.sh/install \| bash`                                                                     |
| `vite build` → `TS2769 Runtime` em `aws.ts`                 | SDK Lambda atualizou enum                                 | Confirmar `import { type Runtime } from "@aws-sdk/client-lambda"` em `src/lib/api/aws.ts`                       |
| `docker compose up -d localstack` puxa upstream do registry | `LOCALSTACK_IMAGE` não exportado e tag custom inexistente | Build primeiro: `make docker-build`, depois export `LOCALSTACK_IMAGE=...:latest`                                |

---

## 19. Git / atalhos de dev

```bash
git status
git diff localstack-core/localstack/aws/services/internal.py
git log --oneline -10

# Arquivos modificados na branch
git diff --name-only main...HEAD
```

---

## 20. Referências

### 20.1. Repositório

- Plano de design: [`multi-cloud-console-plan.md`](./multi-cloud-console-plan.md)
- Bridge CLI: `bin/console-cli-bridge.md`
- Convenções de contribuição: `localstack-ui/console/CONTRIBUTING.md`
- Endpoints internos: `localstack-core/localstack/aws/services/internal.py`
- Bridge host (módulo): `localstack-core/localstack/tooling/dev/console_bridge.py`
- Geradores IaC (UI): `localstack-ui/console/src/lib/iac/generators.ts`
- Store do drawer IaC: `localstack-ui/console/src/lib/iac-drawer-store.ts`
- Validadores Python (unit): `tests/unit/console/`
- Dockerfile: `Dockerfile` (raiz do repo)
- Helper de build: `bin/docker-helper.sh`

### 20.2. Documentação oficial das ferramentas

| Ferramenta              | Documentação                                                      |
| ----------------------- | ----------------------------------------------------------------- |
| AWS CLI                 | https://docs.aws.amazon.com/cli/latest/userguide/                 |
| Azure CLI               | https://learn.microsoft.com/cli/azure/                            |
| gcloud CLI              | https://cloud.google.com/sdk/gcloud/reference                     |
| Terraform               | https://developer.hashicorp.com/terraform/docs                    |
| Terraform AWS Provider  | https://registry.terraform.io/providers/hashicorp/aws/latest/docs |
| Serverless Framework v3 | https://www.serverless.com/framework/docs                         |
| serverless-localstack   | https://github.com/localstack/serverless-localstack               |
| LocalStack (upstream)   | https://docs.localstack.cloud/                                    |
