# LocalStack Multi-cloud Console

SPA that clones the AWS Console / Azure Portal / GCP Cloud Console for the
services this fork emulates. Runs against the LocalStack edge gateway at
`http://localhost:4566` and the TLS sidecar at `https://localhost:4569`.

See `docs/multi-cloud-console-plan.md` for the full design.

## Stack

- React 19 + TypeScript + Vite 5
- Tailwind 3.4 + shadcn/ui primitives (Radix)
- TanStack Router · Query · Table
- AWS SDK v3 (`@aws-sdk/client-{s3,sqs,dynamodb,lambda}`)
- Monaco editor (IaC inline snippets)
- xterm (Cloud Shell drawer)
- react-hook-form + zod (forms)
- sonner (toasts)

## Quickstart

```bash
# 1. install
make console-install                # cd console && bun install

# 2. dev (Vite proxy to :4566)
make console-dev                    # http://localhost:5173

# 3. production build (consumed by nginx sidecar at :4577)
make console-build                  # writes dist/

# 4. CLI bridge (host-side aws|az|gcloud exec)
make console-bridge-install
make console-bridge                 # http://127.0.0.1:4578
```

Then bring up the stack and open `http://localhost:4577`:

```bash
docker compose up -d localstack localstack-ui localstack-tls
```

## Routes

| Path                              | View                          |
| --------------------------------- | ----------------------------- |
| `/`                               | Home (current cloud overview) |
| `/aws/s3`                         | S3 buckets                    |
| `/aws/sqs`                        | SQS queues                    |
| `/aws/dynamodb`                   | DynamoDB tables               |
| `/aws/lambda`                     | Lambda functions              |
| `/azure/resource-groups`          | Azure Resource Groups         |
| `/azure/storage-accounts`         | Azure Storage Accounts        |
| `/gcp/storage`                    | GCP Cloud Storage             |
| `/gcp/pubsub`                     | GCP Pub/Sub topics            |

Detail routes follow `/aws/<svc>/<id>`.

## Backend endpoints used

| Endpoint                                                    | Purpose                            |
| ----------------------------------------------------------- | ---------------------------------- |
| `GET  /_localstack/clouds`                                  | List registered clouds             |
| `GET  /_localstack/clouds/{cloud}/health`                   | Service states per cloud           |
| `GET  /_localstack/clouds/{cloud}/info`                     | Edge hosts + metadata              |
| `POST /_localstack/console/cli`                             | In-container CLI passthrough       |
| `POST /_localstack/console/iac`                             | Run terraform/serverless snippet   |
| `POST /_localstack/console/iac/preview`                     | Render provider.tf + main.tf       |
| `GET  /_localstack/console/sessions/<session_id>/log`       | Read IaC exec log                  |

## CLI bridge

`bin/console-cli-bridge` listens on `127.0.0.1:4578` and exposes
`/exec` + `/exec/stream`. The SPA tries the bridge first and falls back
to the in-container `/_localstack/console/cli` endpoint if the bridge is
not running. Bridge security: cli allowlist (`aws`, `az`, `gcloud`),
shell-metachar rejection on `args` and `env` values, loopback bind.

## Skins (`docs/multi-cloud-console-plan.md` §6)

CSS variables set by `src/lib/skins.ts` on the document root. Tailwind
config consumes them via `skin-bg-top`, `skin-accent`, `skin-sidebar`,
`font-skin`, `shadow-skin`. Switching the cloud picker reapplies the skin
and persists the choice to localStorage.

## Legacy painel

The original `localstack-ui/index.html` lives at
`localstack-ui/console/legacy.html` and is mounted into the nginx sidecar
at `http://localhost:4577/legacy.html`.
