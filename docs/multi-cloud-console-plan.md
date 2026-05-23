# Plano — Console multi-cloud (AWS / Azure / GCP) no nosso fork

Status: **proposta**, não implementado. Implementação solicitada para o
dia seguinte.

> Objetivo: replicar localmente as principais janelas dos consoles oficiais
> (AWS Console, Azure Portal, Google Cloud Console) para os serviços que o
> nosso fork já emula. Cada tela deve permitir gerenciar recursos **via
> formulários da própria UI**, **via IaC (Terraform / Serverless Framework)**
> e **via CLI (`aws` / `az` / `gcloud`)** — todos apontando para o emulador.

---

## 1 · Contexto e premissas

O fork já entrega:

- Gateway multi-cloud (`localstack/aws`, `localstack/azure`, `localstack/gcp`)
- Painel mínimo em `http://localhost:4577` (abas AWS/Azure/GCP, lista de
  serviços com pills de status) — `localstack-ui/index.html`
- Endpoints meta `/_localstack/clouds`, `/_localstack/clouds/<cloud>/health`,
  `/_localstack/clouds/<cloud>/info`
- Roteamento path-based p/ Azure/GCP dentro do AWS gateway
  (`aws/handlers/multi_cloud.py`)
- TLS sidecar `localstack-tls` (https://localhost:4569) p/ clients que
  exigem HTTPS (Azure CLI / azurerm Terraform)
- Wrappers `bin/{awslocal-dev,azurelocal,gcloudlocal}`
- Exemplos Terraform + Serverless por cloud em `examples/`

Falta: **interface visual por serviço**. Hoje o painel só mostra
"available/running/disabled". Não permite criar bucket, ler mensagem
da fila, ver itens de tabela, deployar função, etc.

Restrições herdadas (CLAUDE.md):

- NÃO editar `localstack-core/localstack/aws/api/**`
- NÃO adicionar `google-cloud-*` SDKs como dep core
- NÃO usar Moto fallback p/ GCP
- Testes GCP fora de `tests/aws/**` e `tests/unit/azure/**`

---

## 2 · Inventário de telas por console oficial

### AWS Console (`console.aws.amazon.com`)

Tela canônica = **service home + list/detail/create** por recurso.
Mapeamento p/ serviços que emulamos hoje:

| Serviço         | Telas relevantes                                                                            |
| --------------- | ------------------------------------------------------------------------------------------- |
| S3              | Buckets list · Bucket detail (Objects, Properties, Permissions, Versioning) · Object viewer |
| SQS             | Queues list · Queue detail (Messages, Send, Receive, Attributes, DLQ)                       |
| SNS             | Topics list · Topic detail (Subscriptions, Publish)                                         |
| DynamoDB        | Tables list · Table detail (Items, Indexes, Streams, Capacity)                              |
| Lambda          | Functions list · Function detail (Code, Triggers, Env, Layers, Test event)                  |
| IAM             | Users · Roles · Policies · Identity providers                                               |
| CloudWatch      | Logs · Metrics · Alarms · Dashboards                                                        |
| API Gateway     | APIs list · API detail (Resources, Methods, Stages, Deployments)                            |
| Secrets Manager | Secrets list · Secret detail (Versions, Rotation, Replication)                              |
| KMS             | Keys list · Key detail (Policy, Rotation, Aliases)                                          |
| EventBridge     | Buses · Rules · Targets · Schedules                                                         |
| Kinesis         | Streams · Shards · Consumers · Firehose                                                     |
| Step Functions  | State machines · Executions · Visual workflow                                               |
| CloudFormation  | Stacks · Stack detail (Events, Resources, Outputs, Template)                                |

Pattern visual AWS: header laranja com região, sidebar de serviços,
tabelas-densas com filtro/coluna, breadcrumbs.

### Azure Portal (`portal.azure.com`)

Tela canônica = **Resource Group → Resources** + **Service Blade**.
Mapeamento:

| Provider Azure       | Telas relevantes                                                                                |
| -------------------- | ----------------------------------------------------------------------------------------------- |
| Microsoft.Resources  | Subscriptions list · Resource Groups list · Group detail (Resources, Deployments, Activity log) |
| Microsoft.Storage    | Storage Accounts list · Account detail (Containers, Queues, Tables, Files, Access keys)         |
| Microsoft.Web        | App Services list · App detail (Configuration, Deployment, Logs, Scale)                         |
| Microsoft.DocumentDB | Cosmos accounts list · Account detail (Containers/Databases, Data Explorer)                     |
| Microsoft.KeyVault   | Vaults list · Vault detail (Secrets, Keys, Certificates, Access policies)                       |
| Entra                | Tenants · Users · App registrations · Service principals · Tokens (debug)                       |

Pattern visual Azure: header azul Microsoft, navegação por blade (slide-in
panels), forms hierárquicos, "Create" wizard step-by-step.

### Google Cloud Console (`console.cloud.google.com`)

Tela canônica = **Project picker → Service**. Mapeamento p/ nossos
GCP services:

| Serviço          | Telas relevantes                                                          |
| ---------------- | ------------------------------------------------------------------------- |
| Resource Manager | Project picker · Project settings                                         |
| Cloud Storage    | Buckets list · Bucket detail (Objects, Permissions, Lifecycle, Retention) |
| Pub/Sub          | Topics · Subscriptions · Snapshots · Schemas                              |
| Firestore        | Database picker · Collections · Documents · Indexes · Rules               |
| Cloud Functions  | Functions list · Function detail (Source, Trigger, Logs)                  |
| IAM & Admin      | Principals · Roles · Service accounts · Workload identity                 |
| BigQuery         | Datasets · Tables · Queries · Job history                                 |
| Secret Manager   | Secrets · Versions · Rotation                                             |
| Cloud KMS        | Key rings · Keys · Versions                                               |
| Cloud Tasks      | Queues · Tasks                                                            |
| Cloud Run        | Services · Revisions · Domain mappings                                    |
| Cloud Logging    | Log explorer · Logs router · Metrics-based logs                           |
| Cloud SQL        | Instances · Databases · Users · Connections                               |
| Cloud Scheduler  | Jobs · Executions                                                         |
| Cloud DNS        | Zones · Records · Policies                                                |
| Spanner          | Instances · Databases · Tables                                            |
| Memorystore      | Instances · Connections                                                   |

Pattern visual GCP: header escuro, sidebar denso ("≡"), Material Design,
cards Material-elevation, FAB de criação, breadcrumbs em projeto/região.

---

## 3 · Arquitetura proposta

### 3.1 Frontend

| Decisão             | Escolha                          | Por quê                                                     |
| ------------------- | -------------------------------- | ----------------------------------------------------------- |
| Framework           | **React 19 + TypeScript + Vite** | SPA leve, dev server rápido, ecossistema                    |
| Routing             | `react-router` v7                | Browser history, nested routes (cloud → service → resource) |
| Estado              | `@tanstack/react-query`          | Cache HTTP, refetch on focus, sem boilerplate Redux         |
| Component library   | `shadcn/ui` (Radix + Tailwind)   | Customizável por cloud-skin                                 |
| Tabelas             | `@tanstack/react-table`          | Filter/sort/paginate sem markup pesado                      |
| Forms               | `react-hook-form` + `zod`        | Validação tipada                                            |
| Editor JSON/YAML    | `@monaco-editor/react`           | IaC inline (policy, template, manifest)                     |
| Toast/notifications | `sonner`                         | API simples                                                 |
| Charts              | `recharts`                       | Métricas CloudWatch/StackDriver                             |
| Auth (UI-local)     | nenhum hoje                      | Tudo é dev local; cookie de "user-stub" se necessário       |

Build target: `localstack-ui/console/` (substitui o `index.html` simples
atual, mas mantém o `/_localstack/clouds*` como API). Servido pelo
sidecar nginx existente.

### 3.2 Backend (sem novo serviço — reutiliza handlers existentes)

| Operação            | Endpoint                                                                   |
| ------------------- | -------------------------------------------------------------------------- |
| Lista de clouds     | `GET /_localstack/clouds`                                                  |
| Health por cloud    | `GET /_localstack/clouds/{cloud}/health`                                   |
| Info por cloud      | `GET /_localstack/clouds/{cloud}/info`                                     |
| Operação de serviço | API nativa (S3, SQS, ARM, GCP REST) via fetch direto                       |
| **CLI passthrough** | **novo** `POST /_localstack/console/cli` (executa wrapper, retorna stdout) |
| **IaC passthrough** | **novo** `POST /_localstack/console/iac` (gera/aplica `.tf` snippet)       |

Endpoints novos vivem em `aws/services/internal.py` (mesmo pattern dos
`CloudHealthResource`).

### 3.3 Layout geral

```
┌─────────────────────────────────────────────────────────────┐
│ Top bar  │ logo · cloud picker (AWS/Azure/GCP) · region · ⚡ │
├──────────┼──────────────────────────────────────────────────┤
│          │  Breadcrumbs: AWS › S3 › my-bucket                │
│ Sidebar  ├──────────────────────────────────────────────────┤
│ por      │                                                   │
│ cloud    │   Service view (list/detail/create)              │
│          │                                                   │
│          ├──────────────────────────────────────────────────┤
│          │  Cloud shell drawer (CLI passthrough)            │
└──────────┴──────────────────────────────────────────────────┘
```

Cloud picker no topo determina:

- Skin (cor + tipografia que imita o console oficial)
- Sidebar com serviços daquele cloud
- Base URL para chamadas API (`http://localhost:4566` ou
  `https://localhost:4569`)

Cada serviço tem 3 views padronizadas:

1. **List**: tabela com filtro, paginação, ação "Create"
2. **Detail**: tabs (Overview, Items, Permissions, Logs, JSON view)
3. **Create wizard**: form multi-step com preview do payload SDK

### 3.4 Modo IaC inline ("Show as Terraform")

Cada tela tem botão `< /> Show as Terraform`. Abre drawer com:

- Bloco `resource "..." "..." { ... }` correspondente
- Botão "Copy"
- Botão "Apply via console" → invoca `/_localstack/console/iac`
  - Backend grava arquivo temp em `.localstack/console-iac/<session>/`
  - Executa `terraform apply -auto-approve`
  - Stream stdout via SSE/WS

Equivalente "Show as Serverless YAML" para Lambda + Azure Functions +
Cloud Functions.

### 3.5 Cloud shell drawer (CLI passthrough)

Drawer inferior expansível com prompt:

```
$ aws s3 ls
```

Editor tipo xterm.js. Backend:

- `POST /_localstack/console/cli {"cli":"aws","args":["s3","ls"]}`
- Service handler executa `bin/awslocal-dev s3 ls` no host onde o
  console roda (tipicamente o container localstack-main, então
  precisa bind-mount dos wrappers + binários `aws`/`az`/`gcloud` —
  ver §4)
- Stream de stdout/stderr via SSE
- Histórico persistido em `localStorage`

---

## 4 · Embalagem (Docker)

Decisão: **NÃO** subir os CLIs oficiais dentro do container LocalStack.
Eles são gordos (`az` ~1.2GB, `gcloud` ~1.5GB). Em vez disso:

- Console roda no nginx sidecar (`localstack-ui`)
- CLI passthrough → execução **no host do dev** via WebSocket-bridge:
  - Um worker `bin/console-cli-bridge` (Node ou Python) escuta em
    `localhost:4578` e expõe `POST /exec`
  - O console SPA chama `:4578/exec` (CORS allow-list)
  - O bridge roda os wrappers no PATH local do dev

Trade-off: precisa o dev rodar o bridge (`make console`) — mas evita
container gigante e mantém o CLI sempre na versão mais nova que o dev
tem instalada.

Alternativa: container `localstack-console-cli` com CLIs pre-baked.
Decidir no início da implementação (questão aberta §10).

---

## 5 · Matriz de cobertura ("MVP → completo")

Phase 1 — MVP (sem IaC inline / sem cloud-shell):

| Cloud | Service         | List | Detail | Create | Delete |
| ----- | --------------- | ---- | ------ | ------ | ------ |
| AWS   | S3              | ✓    | ✓      | ✓      | ✓      |
| AWS   | SQS             | ✓    | ✓      | ✓      | ✓      |
| AWS   | DynamoDB        | ✓    | ✓      | ✓      | ✓      |
| AWS   | Lambda          | ✓    | ✓      | ✓      | ✓      |
| Azure | Resource Groups | ✓    | ✓      | ✓      | ✓      |
| Azure | Storage Acct    | ✓    | ✓      | ✓      | ✓      |
| GCP   | Cloud Storage   | ✓    | ✓      | ✓      | ✓      |
| GCP   | Pub/Sub         | ✓    | ✓      | ✓      | ✓      |

Phase 2 — IaC inline + cloud shell.

Phase 3 — restante dos serviços listados na §2.

---

## 6 · Skins por cloud (visual fidelity)

Tokens CSS por skin (Tailwind config + CSS vars):

| Token       | AWS            | Azure             | GCP                |
| ----------- | -------------- | ----------------- | ------------------ |
| `--bg-top`  | `#232f3e`      | `#0078d4`         | `#1a73e8`          |
| `--accent`  | `#ff9900`      | `#50e6ff`         | `#34a853`          |
| `--sidebar` | `#1b2330`      | `#e6e6e6` (light) | `#202124`          |
| `--font`    | `Amazon Ember` | `Segoe UI`        | `Google Sans`      |
| `--shadow`  | flat           | drop-shadow       | material-elevation |

Componentes neutros (table, form) usam Radix sem skin — apenas tokens
mudam por cloud-context.

Não copiar logo/marca oficial — usar "AWS · Azure · GCP" em texto + ícone
de cloud genérico. Mantém o projeto fora de claim de trademark.

---

## 7 · API surface a expor (novo)

Em `aws/services/internal.py`:

```python
self.add(Resource("/_localstack/console/cli", CliPassthroughResource()))
self.add(Resource("/_localstack/console/iac", IacApplyResource()))
self.add(Resource("/_localstack/console/iac/preview", IacPreviewResource()))
self.add(Resource("/_localstack/console/sessions/<id>/log", SessionLogResource()))
```

Schema (resumido):

```jsonc
// POST /_localstack/console/cli
{ "cli": "aws|az|gcloud", "args": ["s3", "ls"], "env": { "AWS_REGION": "us-east-1" } }
// -> 200
{ "session_id": "abc", "exit_code": 0, "stdout": "...", "stderr": "" }

// POST /_localstack/console/iac
{ "tool": "terraform|serverless", "snippet": "resource ... { ... }", "action": "plan|apply|destroy" }
// -> 200 (stream via SSE)
```

CORS: já permite `localhost:4577`. Adicionar `localhost:5173`
(Vite dev server) durante desenvolvimento via
`EXTRA_CORS_ALLOWED_ORIGINS`.

---

## 8 · Layout de arquivos proposto

```
localstack-ui/
├── console/                     # NEW — substitui index.html simples
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   ├── index.html
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── routes/
│   │   │   ├── aws/
│   │   │   │   ├── s3/{List,Detail,Create}.tsx
│   │   │   │   ├── sqs/...
│   │   │   │   └── ...
│   │   │   ├── azure/...
│   │   │   └── gcp/...
│   │   ├── components/
│   │   │   ├── shell/{TopBar,Sidebar,Breadcrumbs}.tsx
│   │   │   ├── cloud-shell/CloudShellDrawer.tsx
│   │   │   ├── iac/IacInlineDrawer.tsx
│   │   │   ├── ui/* (shadcn)
│   │   │   └── skins/{aws,azure,gcp}.ts
│   │   ├── lib/
│   │   │   ├── api/{aws,azure,gcp}.ts
│   │   │   ├── auth.ts
│   │   │   └── iac/{terraform,serverless}.ts
│   │   └── styles/
│   └── public/
└── (index.html original move p/ console/legacy.html)
```

Build target → `dist/`. Sidecar nginx serve `dist/` em
`http://localhost:4577`.

Toolchain: `pnpm` (lock-file determinístico, melhor monorepo se um dia
splitar pkgs). Justificativa em §10 caso o time prefira npm.

---

## 9 · Plano de implementação (8 milestones)

| #   | Milestone                                             | Output esperado                                                    | Tempo bruto |
| --- | ----------------------------------------------------- | ------------------------------------------------------------------ | ----------- |
| 1   | Scaffolding SPA + skin AWS + roteamento               | `pnpm dev` abre console, troca cloud, sidebar carrega              | 0.5d        |
| 2   | API client + tabelas list (S3, SQS, Storage, Pub/Sub) | 4 telas list funcionais consumindo gateway                         | 1d          |
| 3   | Detail + Create wizard (S3 + Pub/Sub)                 | criar bucket pela UI → terraform shows mesmo resource              | 1d          |
| 4   | Skins Azure + GCP + cloud picker                      | troca de skin visualmente convincente                              | 0.5d        |
| 5   | IaC inline drawer (Show as Terraform / Apply)         | snippet por recurso + `terraform apply` real                       | 1.5d        |
| 6   | Cloud shell drawer + bridge worker                    | `aws s3 ls` na UI retorna mesmo output do terminal                 | 1d          |
| 7   | Resto dos serviços phase 1 (DynamoDB, Lambda, RG)     | matriz §5 completa                                                 | 1d          |
| 8   | Tests + lint + CI                                     | playwright smokes p/ list/create/delete por cloud; vitest p/ utils | 0.5d        |

Total estimado: **~7 dias úteis** (1 dev). Critério de done por
milestone definido na issue/checklist correspondente.

---

## 10 · Questões abertas (decidir na kickoff de amanhã)

1. **Bridge CLI no host vs container gordo**?
   Recomendação: bridge no host (§4). Decisão final do time.
2. **pnpm vs npm vs yarn**? Repo já usa npm em outros lugares? Verificar.
3. **Trademark/branding**: nomes "AWS"/"Azure"/"GCP" em texto livre ok;
   logos oficiais — bloqueado. Usar ícones genéricos (Lucide).
4. **Persistência**: o console mostra estado do emulador (volátil por
   default). Habilitar `PERSISTENCE=1` deve ser opt-in no docker-compose?
5. **Auth opcional**: time quer cookie-stub p/ multi-tenant fake
   (account_id), ou tudo single-tenant?
6. **Mobile / responsive**: scope p/ MVP? Recomendação: **não**, console
   é tool de dev.
7. **i18n**: PT-BR + EN? Decidir cedo p/ não retrofitar.
8. **Integração com `app.localstack.cloud`**: link no header já existe
   no painel atual. Manter como "Open in official cloud" deeplink? Útil
   ou ruído?

---

## 11 · Referências externas (estudo prévio)

- AWS Console UX guidelines — `https://aws.amazon.com/console/`
- Azure Portal: blade pattern — `https://learn.microsoft.com/azure/azure-portal/`
- GCP Console Material — `https://cloud.google.com/cloud-console`
- shadcn/ui — `https://ui.shadcn.com/`
- TanStack Query + Table + Router — `https://tanstack.com/`
- React 19 (atual: Jan 2026)
- Monaco editor (VS Code core) — `https://microsoft.github.io/monaco-editor/`

---

## 12 · Riscos e mitigações

| Risco                                         | Mitigação                                                                                              |
| --------------------------------------------- | ------------------------------------------------------------------------------------------------------ | --- | ------------------------------------------------ |
| Service surface diverge do real AWS/Azure/GCP | Skin só. Forms validam contra payload SDK gerado pelos próprios providers Python (snapshot-driven)     |
| Bridge CLI vira vetor de RCE                  | Bind only `127.0.0.1`, allowlist comandos (`aws                                                        | az  | gcloud`), reject shell metachars, log everything |
| Performance com refetch agressivo             | TanStack Query staleTime + window-focus refetch off-by-default; SSE streams para listas grandes        |
| Self-signed TLS quebra fetch do navegador     | Console SPA → HTTP :4566 direto (gateway AWS); Azure-only screens podem usar :4569 com user-side trust |
| Drift entre IaC inline e estado real          | Botão "Refresh from state" lê via API e regera snippet                                                 |
| Tradução das blades Azure (UX denso)          | MVP usa só blade master/detail; multi-blade fica para phase 3                                          |

---

## 13 · Critério de done global

- `docker compose up -d` + `cd localstack-ui/console && pnpm install && pnpm build` produz
  `dist/` consumido pelo nginx sidecar
- `http://localhost:4577` carrega console multi-cloud
- Phase-1 matrix §5 toda navegável e operacional (CRUD)
- IaC inline + cloud-shell funcionando (phase 2)
- 1 playwright spec por cloud passa em CI
- `make lint-modified` clean, sem novos arquivos sob `localstack/aws/api/**`

---

## 14 · Não-objetivos (NÃO faremos)

- Cobertura 100% do AWS/Azure/GCP console (impossível — milhares de
  serviços)
- Substituir `app.localstack.cloud` (UI oficial Pro)
- Suporte production / multi-user / RBAC
- Mobile / tablet
- Plug-in marketplace
- LLM integration ("ask AI to provision X") — fora de scope desta iteração
