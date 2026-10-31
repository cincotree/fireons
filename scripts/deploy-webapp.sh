#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
: "${WEBAPP_BUCKET:?WEBAPP_BUCKET is required}"
: "${WEBAPP_DISTRIBUTION_ID:?WEBAPP_DISTRIBUTION_ID is required}"
: "${WEBAPP_URL:?WEBAPP_URL is required}"
: "${NEXT_PUBLIC_API_BASE_URL:?NEXT_PUBLIC_API_BASE_URL is required}"
export NEXT_PUBLIC_API_BASE_URL

cd "$ROOT/frontend"
npm run build

OUT="$ROOT/frontend/out"
COMMIT="$(git -C "$ROOT" rev-parse HEAD)"
if [ -n "$(git -C "$ROOT" status --porcelain)" ]; then
  COMMIT="$COMMIT-dirty"
fi
printf '{"version": "%s", "built_at": "%s"}\n' "$COMMIT" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$OUT/version.json"
TARGET="s3://$WEBAPP_BUCKET"

aws s3 sync --only-show-errors "$OUT/_next" "$TARGET/_next" \
  --cache-control "public,max-age=31536000,immutable"

aws s3 sync --only-show-errors "$OUT" "$TARGET" \
  --exclude "_next/*" --exclude "*.html" --exclude "*.txt" --exclude "version.json" \
  --cache-control "public,max-age=3600"

aws s3 sync --only-show-errors "$OUT" "$TARGET" \
  --exclude "*" --include "*.html" --include "*.txt" --include "version.json" \
  --cache-control "no-cache"

aws s3 sync --only-show-errors "$OUT" "$TARGET" --delete --exclude "_next/*"

INVALIDATION_ID="$(aws cloudfront create-invalidation \
  --distribution-id "$WEBAPP_DISTRIBUTION_ID" \
  --paths "/*" \
  --query Invalidation.Id --output text)"
aws cloudfront wait invalidation-completed \
  --distribution-id "$WEBAPP_DISTRIBUTION_ID" \
  --id "$INVALIDATION_ID"

curl -fsS --retry 5 --retry-delay 3 -o /dev/null "${WEBAPP_URL%/}/login/"
echo "Smoke check ${WEBAPP_URL%/}/login/ ok"

curl -fsS --retry 5 --retry-delay 3 "${WEBAPP_URL%/}/version.json" | grep -q "\"$COMMIT\""
echo "Deployed version is $COMMIT"
