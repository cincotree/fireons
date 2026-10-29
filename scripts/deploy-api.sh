#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEPLOY_ENV="${DEPLOY_ENV:-production}"
FUNCTION_NAME="${API_FUNCTION_NAME:-fireons-$DEPLOY_ENV-api}"
ALIAS_NAME="${API_ALIAS_NAME:-live}"
SECRET_ID="${SECRET_ID:-fireons/$DEPLOY_ENV}"

"$ROOT/backend/scripts/build_lambda.sh"

DATABASE_URL="$(aws secretsmanager get-secret-value --secret-id "$SECRET_ID" --query SecretString --output text \
  | python3 -c '
import json, sys
values = json.load(sys.stdin)
if "DATABASE_URL" not in values:
    sys.exit("Secret has no DATABASE_URL key. Keys found: " + ", ".join(sorted(values)))
print(values["DATABASE_URL"])
')"
if [ -n "${GITHUB_ACTIONS:-}" ]; then
  echo "::add-mask::$DATABASE_URL"
fi
export DATABASE_URL

echo "Applying migrations"
(cd "$ROOT/backend" && uv run alembic upgrade head)

echo "Publishing new version of $FUNCTION_NAME"
VERSION="$(aws lambda update-function-code \
  --function-name "$FUNCTION_NAME" \
  --zip-file "fileb://$ROOT/backend/build/api.zip" \
  --publish \
  --query Version --output text)"
aws lambda wait function-updated --function-name "$FUNCTION_NAME" --qualifier "$VERSION"

smoke_test() {
  local path="$1"
  local out
  out="$(mktemp)"
  local log_tail
  log_tail="$(aws lambda invoke \
    --function-name "$FUNCTION_NAME" \
    --qualifier "$VERSION" \
    --cli-binary-format raw-in-base64-out \
    --log-type Tail \
    --payload "{\"version\":\"2.0\",\"rawPath\":\"$path\",\"rawQueryString\":\"\",\"headers\":{\"host\":\"localhost\"},\"isBase64Encoded\":false,\"requestContext\":{\"http\":{\"method\":\"GET\",\"path\":\"$path\"}}}" \
    --query LogResult --output text \
    "$out")"
  local status
  status="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("statusCode"))' "$out")"
  if [ "$status" != "200" ]; then
    echo "Smoke test $path returned $status on version $VERSION; alias $ALIAS_NAME unchanged" >&2
    echo "Response:" >&2
    head -c 2000 "$out" >&2
    echo >&2
    echo "Last log lines:" >&2
    echo "$log_tail" | base64 --decode >&2 || true
    rm -f "$out"
    exit 1
  fi
  rm -f "$out"
  echo "Smoke test $path ok"
}

smoke_test /health
smoke_test /health/ready

aws lambda update-alias --function-name "$FUNCTION_NAME" --name "$ALIAS_NAME" --function-version "$VERSION" > /dev/null
echo "Alias $ALIAS_NAME now points to version $VERSION"
