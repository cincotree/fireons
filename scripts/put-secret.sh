#!/usr/bin/env bash
set -euo pipefail

KEY="${1:?usage: put-secret.sh KEY_NAME}"
DEPLOY_ENV="${DEPLOY_ENV:-production}"
SECRET_ID="${SECRET_ID:-fireons/$DEPLOY_ENV}"

read -rsp "Value for $KEY: " VALUE
echo

aws secretsmanager get-secret-value --secret-id "$SECRET_ID" --query SecretString --output text \
  | python3 -c '
import json, sys
values = json.load(sys.stdin)
values[sys.argv[1]] = sys.argv[2]
print(json.dumps(values))
' "$KEY" "$VALUE" \
  | aws secretsmanager put-secret-value --secret-id "$SECRET_ID" --secret-string file:///dev/stdin > /dev/null

echo "Set $KEY in $SECRET_ID"
