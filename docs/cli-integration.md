# CLI Integration — AWS · Azure · GCP

Como apontar os CLIs oficiais (`aws`, `az`, `gcloud`) para o emulador local
deste fork. Em todos os casos, o endpoint padrão é `http://localhost:4566`.

Os wrappers vivem em `bin/`:

| Cloud | Wrapper           | CLI exigido | Notas                                              |
|-------|-------------------|-------------|----------------------------------------------------|
| AWS   | `bin/awslocal-dev`| `aws`       | Equivalente leve a `awslocal` (sem pip)            |
| Azure | `bin/azurelocal`  | `az`        | Registra perfil `LocalStack` em `az cloud`         |
| GCP   | `bin/gcloudlocal` | `gcloud`    | Exporta `CLOUDSDK_API_ENDPOINT_OVERRIDES_*`        |

> Pré-requisito comum: o container deve estar de pé
> (`docker compose up -d`) e respondendo em `http://localhost:4566`.

---

## AWS

O CLI da AWS aceita `--endpoint-url` ou `AWS_ENDPOINT_URL` nativamente.

```bash
# Wrapper
bin/awslocal-dev s3 ls
bin/awslocal-dev s3 mb s3://demo
bin/awslocal-dev sqs list-queues
bin/awslocal-dev lambda list-functions

# Equivalente manual
export AWS_ENDPOINT_URL=http://localhost:4566
export AWS_ACCESS_KEY_ID=test AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION=us-east-1
aws s3 ls
```

Cobertura: todos os serviços listados em `localstack/aws/services/`
(35 hoje) + fallback Moto para serviços não cobertos nativamente.

---

## Azure

O `az` não tem `--endpoint-url`. A integração depende do mecanismo
**custom cloud** (`az cloud register`). O wrapper faz isso uma vez.

```bash
bin/azurelocal cloud show --name LocalStack
bin/azurelocal account list
bin/azurelocal storage account list
bin/azurelocal group list
```

O que o wrapper configura ao detectar primeira execução:

- `az cloud register --name LocalStack`
  - `--endpoint-resource-manager  http://localhost:4566`
  - `--endpoint-active-directory  http://localhost:4566`
  - `--endpoint-active-directory-graph-resource-id http://localhost:4566`
  - `--endpoint-active-directory-resource-id      http://localhost:4566`
  - `--suffix-storage-endpoint    core.windows.net`
  - `--suffix-keyvault-dns        .vault.azure.net`
- `az cloud set --name LocalStack`
- Desliga validação TLS via `AZURE_CLI_DISABLE_CONNECTION_VERIFICATION=1`

Trocar de volta para Azure real:

```bash
az cloud set --name AzureCloud
```

Cobertura atual (`localstack/azure/services/`): Resource Manager,
Storage (Blob/Queue), Web/Functions, Cosmos (SQL API), KeyVault, Entra
(token). Comandos fora desse conjunto retornam 404.

Variáveis para customizar:
- `LOCALSTACK_AZURE_CLOUD_NAME` (nome do perfil — default `LocalStack`)
- `LOCALSTACK_AZURE_TENANT`     (default `localstack-tenant`)
- `LOCALSTACK_AZURE_SUB`        (default `00000000-...0000`)

---

## GCP

O `gcloud` lê overrides por API via env
`CLOUDSDK_API_ENDPOINT_OVERRIDES_<API>`. O wrapper exporta todos os
serviços hoje implementados.

```bash
bin/gcloudlocal storage buckets list
bin/gcloudlocal pubsub topics list
bin/gcloudlocal functions list
bin/gcloudlocal iam service-accounts list
```

O que o wrapper define:

- `CLOUDSDK_AUTH_DISABLE_CREDENTIALS=true`
- `CLOUDSDK_CORE_PROJECT=localstack-project`
- `CLOUDSDK_API_ENDPOINT_OVERRIDES_STORAGE=http://localhost:4566/`
- `..._PUBSUB`, `..._FIRESTORE`, `..._CLOUDFUNCTIONS`, `..._IAM`,
  `..._BIGQUERY`, `..._SECRETMANAGER`, `..._CLOUDKMS`,
  `..._CLOUDTASKS`, `..._RUN`, `..._LOGGING`, `..._SQLADMIN`,
  `..._CLOUDSCHEDULER`, `..._DNS`, `..._SPANNER`, `..._REDIS`,
  `..._CLOUDRESOURCEMANAGER` → mesmo endpoint
- `CLOUDSDK_CORE_DISABLE_SSL_VALIDATION=true`

Trocar de volta para o GCP real: rode `gcloud` sem o wrapper (env
some quando o shell pai termina) ou explicitamente
`unset CLOUDSDK_API_ENDPOINT_OVERRIDES_STORAGE ...`.

Cobertura atual (`localstack/gcp/services/`): Cloud Storage, Pub/Sub,
Firestore, Cloud Functions, IAM, BigQuery, Secret Manager, Cloud KMS,
Cloud Tasks, Cloud Run, Cloud Logging, Cloud SQL Admin, Cloud
Scheduler, Cloud DNS, Spanner, Memorystore (Redis), Resource Manager.
Outros (Compute Engine, GKE, BigTable...) ainda não são roteados.

---

## Roteamento interno

O edge gateway em `:4566` (`AWS Gateway`) tem prioridade no path
`/_localstack/*` e em rotas SigV4. O `MultiCloudEdge`
(`localstack/cloud/edge.py`) seleciona o cloud por padrão de Host:

- `*.amazonaws.com`, `*.s3.amazonaws.com` → AWS
- `*.blob.core.windows.net`, `*.queue.core.windows.net`,
  `*.documents.azure.com`, `*.azurewebsites.net`, `*.vault.azure.net`,
  `login.microsoftonline.com` → Azure
- `storage.googleapis.com`, `pubsub.googleapis.com`,
  `firestore.googleapis.com`, ... → GCP

Por isso `azurelocal storage account list` (que monta
`management.azure.com/subscriptions/...`) funciona via fallback
path-based no `AzureGateway` (`/subscriptions/...` → ARM router) — não
exige DNS rewrite.

## Painel multi-cloud

`http://localhost:4577` mostra abas AWS/Azure/GCP com status de cada
serviço registrado. Endpoints subjacentes:

- `GET /_localstack/clouds`
- `GET /_localstack/clouds/<cloud>/health`
- `GET /_localstack/clouds/<cloud>/info`

## TLS sidecar (`localstack-tls`)

`docker compose up -d localstack-tls` sobe nginx em
`https://localhost:4569` com cert auto-assinado (SAN: `localhost`,
`login.microsoftonline.com`, `management.azure.com`, `127.0.0.1`).

O wrapper `azurelocal` aponta o perfil de cloud para esse endpoint e
exporta `REQUESTS_CA_BUNDLE` apontando p/ `localstack-tls/certs/cert.pem`.

Regenerar o cert (1 ano de validade):

```bash
cd localstack-tls/certs
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout key.pem -out cert.pem \
  -subj "/CN=localhost" \
  -addext "subjectAltName=DNS:localhost,DNS:login.microsoftonline.com,DNS:management.azure.com,IP:127.0.0.1"
docker compose restart localstack-tls
```

## Infrastructure-as-Code

### Terraform

Exemplos em [`examples/terraform/`](../examples/terraform/) — um
`main.tf` por cloud, mostrando provider config + recursos básicos.

| Cloud | Mecanismo de override                                  |
|-------|---------------------------------------------------------|
| AWS   | `provider "aws" { endpoints { s3 = ... }`               |
| Azure | `provider "azurerm" { metadata_host = "localhost:4569" }` + env `ARM_*` |
| GCP   | `provider "google" { storage_custom_endpoint = ... }`   |

Variáveis necessárias por cloud — ver
[`examples/terraform/README.md`](../examples/terraform/README.md).

### Serverless Framework

Exemplos em [`examples/serverless/`](../examples/serverless/). Plugins
exigidos:

- AWS → `serverless-localstack`
- Azure → `serverless-azure-functions`
- GCP → `serverless-google-cloudfunctions`

Funcional 100% hoje: stack AWS (Lambda + API GW + DynamoDB + S3 + SQS).
Azure e GCP cobrem só HTTP-trigger functions — outros triggers
dependem de extensões do provider.

## Limitações conhecidas

1. **`az login` end-to-end**: MSAL valida a authority chamando
   `https://login.microsoftonline.com:443/common/discovery/instance`
   (hardcoded). Para forçar redirect, opte-in:

   ```bash
   # /etc/hosts (requer root)
   127.0.0.1 login.microsoftonline.com management.azure.com

   # nginx sidecar precisa escutar também em :443 — editar
   # localstack-tls/nginx.conf adicionando `listen 443 ssl;`
   ```

   Workaround padrão (recomendado para CI/CD): use o fluxo
   service-principal direto via env vars — Terraform `azurerm` e
   Serverless Azure funcionam sem `az login`.

2. **`gcloud auth login`**: idem — fluxo OAuth interativo precisa
   redirect via /etc/hosts. Use `CLOUDSDK_AUTH_DISABLE_CREDENTIALS=true`
   + `GOOGLE_OAUTH_ACCESS_TOKEN=dummy` para pular auth real.

3. **Comandos não-implementados**: o gateway retorna 404 JSON
   `{"error":{"code":"RouteNotFound",...}}`. Cobertura por cloud
   conforme listada nas seções acima.
4. **Comandos não-implementados** retornam 404 JSON
   `{"error":{"code":"RouteNotFound",...}}`. Isso é esperado — ver
   listas de cobertura por cloud acima.
