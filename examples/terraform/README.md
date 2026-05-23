# Terraform examples — AWS · Azure · GCP via LocalStack

Three single-file Terraform configs that exercise the LocalStack
multi-cloud emulator. Each runs the matching `terraform init/plan/apply`
against the local edge.

## Prereqs

```bash
# 1. Start LocalStack + TLS sidecar
docker compose up -d localstack localstack-tls localstack-ui

# 2. Install terraform >= 1.5
brew install terraform   # or https://developer.hashicorp.com/terraform/install
```

## AWS

```bash
cd aws
terraform init
terraform apply -auto-approve
terraform destroy -auto-approve
```

Uses `http://localhost:4566` and the standard
`access_key = "test", secret_key = "test"` LocalStack credentials.

## Azure

```bash
cd azure
export ARM_CLIENT_ID=00000000-0000-0000-0000-000000000001
export ARM_CLIENT_SECRET=test-secret
export ARM_TENANT_ID=localstack-tenant
export ARM_SUBSCRIPTION_ID=00000000-0000-0000-0000-000000000000
export ARM_METADATA_HOST=localhost:4569
export SSL_CERT_FILE="$PWD/../../../localstack-tls/certs/cert.pem"

terraform init
terraform apply -auto-approve
```

`SSL_CERT_FILE` trusts the self-signed cert that the TLS sidecar
serves. Without it, the Go-based azurerm provider rejects the
connection.

## GCP

```bash
cd gcp
export GOOGLE_OAUTH_ACCESS_TOKEN=dummy-token
export GOOGLE_PROJECT=localstack-project

terraform init
terraform apply -auto-approve
```

No TLS needed for GCP — gcloud SDKs accept HTTP when endpoints are
overridden explicitly.

## Notes

- The `terraform destroy` plans rebuild the same resources on the next
  `apply`. State lives in `terraform.tfstate` in each example directory.
- LocalStack data is volatile by default; set `PERSISTENCE=1` in
  `docker-compose.yml` to persist between container restarts.
- Only services listed under `localstack/{aws,azure,gcp}/services/` are
  emulated — exotic resources (Azure AKS, GCP GKE, AWS Macie) will fail
  with 404 from the gateway.
