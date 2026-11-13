#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEPLOY_ENV="${DEPLOY_ENV:-production}"
REGION="${AWS_REGION:-$(aws configure get region)}"

if [ -z "${JOBS_ECR_REPOSITORY_URL:-}" ]; then
  ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
  JOBS_ECR_REPOSITORY_URL="$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/fireons-$DEPLOY_ENV-jobs"
fi
REGISTRY="${JOBS_ECR_REPOSITORY_URL%%/*}"

COMMIT="$(git -C "$ROOT" rev-parse HEAD)"
if [ -n "$(git -C "$ROOT" status --porcelain)" ]; then
  COMMIT="$COMMIT-dirty"
fi

aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin "$REGISTRY"

docker buildx build \
  --platform linux/arm64 \
  --file "$ROOT/backend/Dockerfile.worker" \
  --tag "$JOBS_ECR_REPOSITORY_URL:latest" \
  --tag "$JOBS_ECR_REPOSITORY_URL:$COMMIT" \
  --push \
  "$ROOT/backend"

echo "Pushed $JOBS_ECR_REPOSITORY_URL:latest and :$COMMIT for $DEPLOY_ENV"
