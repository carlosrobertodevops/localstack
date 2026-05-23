# console-cli-bridge

Host-side worker that lets the multi-cloud console SPA (served by the
`localstack-ui` nginx sidecar at `http://localhost:4577`, or by the Vite
dev server at `http://localhost:5173`) execute the locally-installed
`aws` / `az` / `gcloud` CLIs.

This avoids shipping multi-GB CLI tarballs inside the LocalStack
container. See `docs/multi-cloud-console-plan.md` §3.5 and §4.

## Install

```bash
pip install -r bin/console-cli-bridge.requirements.txt
```

## Run

```bash
./bin/console-cli-bridge                 # 127.0.0.1:4578
./bin/console-cli-bridge --verbose       # debug logging
./bin/console-cli-bridge --allow-origin http://my-host:8080
```

## Endpoints

| Method | Path           | Description                                 |
| ------ | -------------- | ------------------------------------------- |
| GET    | `/health`      | Status + CLI availability map               |
| POST   | `/exec`        | One-shot exec, JSON response                |
| POST   | `/exec/stream` | Server-sent events for stdout/stderr/exit   |

Body for `/exec` and `/exec/stream`:

```jsonc
{ "cli": "aws|az|gcloud", "args": ["s3", "ls"], "env": { "AWS_REGION": "us-east-1" } }
```

## Security

- Binds to `127.0.0.1` only by default.
- Allowlists `cli` field; rejects shell metachars in `args` and env values.
- Logs every invocation (cli + arg count + duration + exit code) but never
  the env values.
- Delegates to the sibling wrappers `bin/awslocal-dev` / `bin/azurelocal`
  / `bin/gcloudlocal` so credentials and endpoints stay pointed at the
  local LocalStack instance.

## Why a separate process

LocalStack runs inside Docker. The host CLIs live outside the container.
A small loopback HTTP bridge keeps the container image lean and the dev's
CLI install always current.
