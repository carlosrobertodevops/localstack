# Serverless Framework — AWS · Azure · GCP via LocalStack

## Prereqs

```bash
# 1. Stack up
docker compose up -d

# 2. Install the framework
npm install -g serverless@3
```

## AWS

```bash
cd aws
npm install serverless-localstack
serverless deploy --stage dev
serverless invoke --function hello --stage dev
```

The `serverless-localstack` plugin rewrites all AWS SDK calls to
`http://localhost:4566`.

## Azure

```bash
cd azure
npm install serverless-azure-functions

source env.sh   # see comments in serverless.yml
serverless deploy --stage dev
```

Working scope today: HTTP-trigger functions, storage account ARM
resource provisioning. Other triggers (queue, blob, eventhub) require
LocalStack Azure provider extensions not yet wired.

## GCP

```bash
cd gcp
npm install serverless-google-cloudfunctions

export CLOUDSDK_API_ENDPOINT_OVERRIDES_CLOUDFUNCTIONS=http://localhost:4566/
export GOOGLE_OAUTH_ACCESS_TOKEN=dummy
serverless deploy --stage dev
```

Working scope: HTTP-trigger Cloud Functions Gen 1. Pub/Sub triggers
work after declaring the topic via `gcloudlocal pubsub topics create`.

## Caveats

- AWS path is the most polished — every IaC abstraction LocalStack
  documents officially.
- Azure path depends on the in-repo `azure/services/functions/`
  provider implementing enough of `Microsoft.Web/sites` to satisfy SF.
- GCP path requires our GCP gateway to accept the `gcloud functions
  deploy`-style upload flow. Verify with
  `gcloudlocal functions deploy hello --runtime python311 --trigger-http`
  first.
