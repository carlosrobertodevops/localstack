#!/usr/bin/env bash
# LocalStack init hook (ready.d): cria buckets default para evitar 404 NoSuchBucket
# durante dev. Edite a lista BUCKETS conforme necessidade do projeto.
set -euo pipefail

BUCKETS=("${LS_INIT_BUCKETS:-my-bucket}")

ENDPOINT="${LS_ENDPOINT:-http://localhost:4566}"
REGION="${AWS_DEFAULT_REGION:-us-east-1}"

# Prefer awslocal (incluído na image), fallback aws CLI com endpoint
if command -v awslocal >/dev/null 2>&1; then
  AWS=(awslocal)
else
  AWS=(aws --endpoint-url="$ENDPOINT" --region "$REGION")
  export AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID:-test}"
  export AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY:-test}"
fi

for b in "${BUCKETS[@]}"; do
  if "${AWS[@]}" s3api head-bucket --bucket "$b" >/dev/null 2>&1; then
    echo "[init-s3] bucket exists: $b"
  else
    echo "[init-s3] creating bucket: $b"
    "${AWS[@]}" s3 mb "s3://$b"
  fi
done
