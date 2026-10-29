#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEPLOY_ENV="${DEPLOY_ENV:-production}"
SECRET_ID="${SECRET_ID:-fireons/$DEPLOY_ENV}"

DATABASE_URL="$(aws secretsmanager get-secret-value --secret-id "$SECRET_ID" --query SecretString --output text \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["DATABASE_URL"])')"
export DATABASE_URL

cd "$ROOT/backend"
uv run python -m scripts.create_superadmin "$@"
