#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

rm -rf build
mkdir -p build/package

uv export --frozen --no-dev --no-hashes --no-emit-project \
  | grep -v -E '^(boto3|botocore|s3transfer|jmespath)==' > build/requirements.txt

uv pip install \
  --target build/package \
  --python-platform aarch64-manylinux2014 \
  --python-version 3.12 \
  --only-binary :all: \
  --no-compile \
  -r build/requirements.txt

cp app.py app_config.py auth_utils.py secrets_source.py run.sh build/package/
cp -R api database ingestion jobs build/package/

find build/package -name '__pycache__' -type d -prune -exec rm -rf {} +
chmod +x build/package/run.sh

(cd build/package && zip -qr ../api.zip .)

echo "Built build/api.zip ($(du -h build/api.zip | cut -f1))"
