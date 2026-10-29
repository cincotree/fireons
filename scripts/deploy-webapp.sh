#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
: "${WEBAPP_BUCKET:?WEBAPP_BUCKET is required}"
: "${WEBAPP_DISTRIBUTION_ID:?WEBAPP_DISTRIBUTION_ID is required}"
: "${WEBAPP_URL:?WEBAPP_URL is required}"
: "${NEXT_PUBLIC_API_BASE_URL:?NEXT_PUBLIC_API_BASE_URL is required}"
: "${NEXT_PUBLIC_TURNSTILE_SITE_KEY:?NEXT_PUBLIC_TURNSTILE_SITE_KEY is required}"
export NEXT_PUBLIC_API_BASE_URL NEXT_PUBLIC_TURNSTILE_SITE_KEY

cd "$ROOT/frontend"
npm run build

OUT="$ROOT/frontend/out"
TARGET="s3://$WEBAPP_BUCKET"

aws s3 sync "$OUT/_next" "$TARGET/_next" \
  --cache-control "public,max-age=31536000,immutable"

aws s3 sync "$OUT" "$TARGET" \
  --exclude "_next/*" --exclude "*.html" --exclude "*.txt" \
  --cache-control "public,max-age=3600"

aws s3 sync "$OUT" "$TARGET" \
  --exclude "*" --include "*.html" --include "*.txt" \
  --cache-control "no-cache"

aws s3 sync "$OUT" "$TARGET" --delete --exclude "_next/*"

INVALIDATION_ID="$(aws cloudfront create-invalidation \
  --distribution-id "$WEBAPP_DISTRIBUTION_ID" \
  --paths "/*" \
  --query Invalidation.Id --output text)"
aws cloudfront wait invalidation-completed \
  --distribution-id "$WEBAPP_DISTRIBUTION_ID" \
  --id "$INVALIDATION_ID"

curl -fsS --retry 5 --retry-delay 3 -o /dev/null "${WEBAPP_URL%/}/login/"
echo "Smoke check ${WEBAPP_URL%/}/login/ ok"
