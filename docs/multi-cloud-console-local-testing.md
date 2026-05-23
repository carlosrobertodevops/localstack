# Multi-cloud Console — Manual de Testes Locais

Guia para subir e testar localmente o LocalStack fork + console multi-cloud
**usando a imagem que construímos a partir deste repositório**
(`localstack/localstack-custom`), **não a imagem oficial `localstack/localstack`**.

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

## 1. Pré-requisitos

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

## 2. Build da nossa imagem

A imagem é construída a partir do `Dockerfile` na raiz, via
`bin/docker-helper.sh`. O target `make docker-build` empacota o
`localstack-core` atual + entrypoints + providers do fork.

### 2.1. Build padrão

```bash
# Tag default: localstack/localstack:latest
make docker-build
```

### 2.2. Build com tag custom (recomendado para evitar colisão com upstream)

```bash
# Use a mesma tag que o docker-compose espera por default
IMAGE_NAME=localstack/localstack-custom DEFAULT_TAG=dev make docker-build
docker image ls localstack/localstack-custom
```

### 2.3. Build multiplataforma (Apple Silicon → linux/amd64 p/ CI parity)

```bash
IMAGE_NAME=localstack/localstack-custom PLATFORM=linux/amd64 make docker-build
```

### 2.4. Rebuild rápido após mudança só em `localstack-core/`

```bash
# Reaproveita as camadas anteriores
DOCKER_BUILDKIT=1 IMAGE_NAME=localstack/localstack-custom make docker-build
```

> Tag default do compose: `localstack/localstack-custom:latest`.
> Se você usou outra tag (ex.: `:dev`), exporte:
>
> ```bash
> export LOCALSTACK_IMAGE=localstack/localstack-custom:dev
> ```

---

## 3. Backend (LocalStack fork) via docker-compose

### 3.1. Venv local + entrypoints (necessário antes de `make docker-build`)

```bash
make install            # cria .venv + instala deps
source .venv/bin/activate
make entrypoints        # regenera plux.ini (obrigatório p/ providers serem descobertos)
```

> Pular `make entrypoints` é a fonte #1 de "endpoint X 404" — o Plux registry
> não enxerga providers novos sem `plux.ini` atualizado.

### 3.2. Subir só o LocalStack

```bash
LOCALSTACK_IMAGE=localstack/localstack-custom:latest docker compose up -d localstack
docker compose ps                                # esperar 'healthy'
docker compose logs -f localstack | head -40     # verificar boot
```

### 3.3. Confirmar que é o nosso fork (não o upstream)

```bash
# /clouds só existe no fork
curl -s http://localhost:4566/_localstack/clouds | jq

# Esperado:
# { "clouds": [ { "name": "aws", ... }, { "name": "azure", ... } ] }

# Se voltar 404 → você está rodando upstream. Confira:
docker compose images localstack
docker inspect localstack-main --format '{{.Config.Image}}'
```

### 3.4. Endpoints do console (só existem no fork)

```bash
# Render de provider.tf + main.tf
curl -s -X POST http://localhost:4566/_localstack/console/iac/preview \
  -H 'content-type: application/json' \
  -d '{"tool":"terraform","snippet":"resource \"aws_s3_bucket\" \"x\" { bucket = \"x\" }"}' \
  | jq

# CLI passthrough (in-container) — rejeita cli fora da allowlist
curl -s -X POST http://localhost:4566/_localstack/console/cli \
  -H 'content-type: application/json' -d '{"cli":"evil","args":[]}'
# → 400 unsupported cli
```

---

## 4. Console SPA

### 4.1. Dev (Vite, hot-reload em `:5173`)

```bash
make console-install        # bun install
make console-dev            # http://localhost:5173
```

Proxy do Vite: `/_localstack/*` → `:4566`; `/_bridge/*` → `:4578`.

### 4.2. Build de produção + servir via nginx sidecar (`:4577`)

```bash
make console-build                          # gera localstack-ui/console/dist/
docker compose up -d localstack-ui          # nginx monta dist/ em :4577
open http://localhost:4577
```

---

## 5. Bridge CLI host-side (`:4578`)

Executa `aws`, `az`, `gcloud` na **sua máquina** com credenciais reais
quando o Cloud Shell drawer precisa de algo fora do escopo do container.

```bash
make console-bridge-install     # cria .venv-bridge e instala aiohttp
make console-bridge             # listen em 127.0.0.1:4578
```

Healthcheck (outra aba):

```bash
curl -s http://127.0.0.1:4578/health | jq
```

Bridge offline → SPA cai automaticamente para `/_localstack/console/cli`
(in-container, com PATH limitado).

---

## 6. Roteiros de teste pela UI

Abra `http://localhost:4577` (build) ou `http://localhost:5173` (dev).
Use o **cloud picker** na TopBar para alternar skin + serviços.

### 6.1. AWS · S3

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

### 6.2. AWS · SQS · DynamoDB · Lambda

| Rota            | Ação                                                                     |
| --------------- | ------------------------------------------------------------------------ |
| `/aws/sqs`      | Create queue → Send message → Receive                                    |
| `/aws/dynamodb` | Create table (PK = `id`) → Scan                                          |
| `/aws/lambda`   | Create function (Runtime `python3.12`, zip base64 default) → Invoke `{}` |

### 6.3. Azure · Resource Groups + Storage

1. Troque para **Azure**.
2. `/azure/resource-groups` → Create RG `rg-demo` (location `eastus`).
3. `/azure/storage-accounts` → Create `stdemo` no RG `rg-demo`.

### 6.4. GCP · Storage + Pub/Sub

1. Troque para **GCP**.
2. `/gcp/storage` → Create bucket `gcs-demo`.
3. `/gcp/pubsub` → Create topic `topic-demo`.

---

## 7. Cloud Shell drawer

1. Botão flutuante (canto inferior direito) → abre drawer com xterm.
2. Comandos: `aws s3 ls`, `az group list`, `gcloud storage ls`.
3. Histórico em `localStorage` (`localstack-console:shell-history`); ↑/↓.
4. Allowlist enforced: `aws`, `az`, `gcloud`. Outros → 400.

---

## 8. IaC inline drawer

| Botão   | Endpoint                                         | Efeito                     |
| ------- | ------------------------------------------------ | -------------------------- |
| Copy    | (client-side)                                    | Copia para clipboard       |
| Preview | `POST /_localstack/console/iac/preview`          | `provider.tf` + `main.tf`  |
| Plan    | `POST /_localstack/console/iac` (action=plan)    | `terraform plan` na sessão |
| Apply   | `POST /_localstack/console/iac` (action=apply)   | Provisiona contra `:4566`  |
| Destroy | `POST /_localstack/console/iac` (action=destroy) | Remove o recurso           |

Log da sessão: `GET /_localstack/console/sessions/<session_id>/log`.

---

## 9. Testes automatizados

### 9.1. Unit Python (validators dos endpoints)

```bash
source .venv/bin/activate
python -m pytest tests/unit/console/ -v
```

Esperado: ~66 testes, 0 falhas.

### 9.2. Unit TypeScript (vitest)

```bash
make console-test       # bun run test → 8/8
```

### 9.3. Smoke contra LocalStack rodando (**na nossa imagem**)

```bash
docker compose up -d localstack                                # imagem custom
SKIP_CONSOLE_SMOKE=0 pytest tests/aws/test_console_endpoints_smoke.py -v
```

Falhou com "endpoint não existe"? Você está na upstream — rebuild:
`IMAGE_NAME=localstack/localstack-custom make docker-build`.

### 9.4. E2E Playwright

```bash
make console-build && docker compose up -d localstack localstack-ui
make console-test-e2e   # bun run test:e2e
```

### 9.5. Suite de testes dentro da imagem

```bash
make docker-run-tests   # roda pytest dentro do container construído
```

---

## 10. Troubleshooting

| Sintoma                                                     | Causa provável                                            | Ação                                                                                                                  |
| ----------------------------------------------------------- | --------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| `curl :4566/_localstack/clouds` retorna 404                 | Compose subiu `localstack/localstack` (upstream)          | `LOCALSTACK_IMAGE=localstack/localstack-custom make docker-build && docker compose up -d --force-recreate localstack` |
| `Endpoint /_localstack/console/iac/preview` retorna 404     | Provider novo não foi registrado pelo Plux                | Reativar venv → `make entrypoints` → `make docker-build` → recriar container                                          |
| Console em `:4577` carrega CSS mas dados vazios             | CORS bloqueando                                           | Confira `EXTRA_CORS_ALLOWED_ORIGINS` no compose (inclui `:4577` e `:5173`)                                            |
| **Apply** falha com `terraform: not found`                  | `terraform` ausente do PATH do container                  | Use a allowlist do bridge host (`make console-bridge`) ou monte um volume com terraform binário                       |
| Cloud Shell mostra "bridge unavailable"                     | Worker `:4578` desligado                                  | Em outro terminal: `make console-bridge`                                                                              |
| `make docker-build` falha em Apple Silicon                  | `PLATFORM` default não bate com runtime                   | `PLATFORM=linux/arm64 make docker-build` (ou `linux/amd64` se quiser parity com CI)                                   |
| `bun install` falha em arm64 mac                            | Bun antigo                                                | `curl -fsSL https://bun.sh/install \| bash`                                                                           |
| `vite build` → `TS2769 Runtime` em `aws.ts`                 | SDK Lambda atualizou enum                                 | Confirme `import { type Runtime } from "@aws-sdk/client-lambda"` em `src/lib/api/aws.ts`                              |
| `docker compose up -d localstack` puxa upstream do registry | `LOCALSTACK_IMAGE` não exportado e tag custom inexistente | Build primeiro: `make docker-build`, depois export `LOCALSTACK_IMAGE=...:latest`                                      |

---

## 11. Reset / limpeza

```bash
# Stack down
docker compose down

# State + volume LocalStack
docker compose down -v
rm -rf volume/

# SPA build + node_modules
rm -rf localstack-ui/console/{dist,node_modules,bun.lock}

# Imagem custom
docker image rm localstack/localstack-custom:latest

# Reconstruir tudo
make docker-build && make console-install && make console-build
docker compose up -d localstack localstack-ui
```

---

## 12. Referências

- Plano de design: `docs/multi-cloud-console-plan.md`
- Bridge CLI: `bin/console-cli-bridge.md`
- Convenções de contribuição: `localstack-ui/console/CONTRIBUTING.md`
- Endpoints internos: `localstack-core/localstack/aws/services/internal.py`
- Validadores Python (unit): `tests/unit/console/`
- Dockerfile: `Dockerfile` (raiz do repo)
- Helper de build: `bin/docker-helper.sh`
