#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEPLOY_ENV="${DEPLOY_ENV:-production}"
REPOSITORY_URL="${JOBS_ECR_REPOSITORY_URL:?Set JOBS_ECR_REPOSITORY_URL from the jobs_ecr_repository_url terraform output}"
IMAGE_TAG="${JOBS_IMAGE_TAG:-latest}"
REGISTRY="${REPOSITORY_URL%%/*}"
REGION="${AWS_REGION:-$(aws configure get region)}"

aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin "$REGISTRY"

docker buildx build \
  --platform linux/arm64 \
  --file "$ROOT/backend/Dockerfile.worker" \
  --tag "$REPOSITORY_URL:$IMAGE_TAG" \
  --push \
  "$ROOT/backend"

echo "Pushed $REPOSITORY_URL:$IMAGE_TAG for $DEPLOY_ENV"
