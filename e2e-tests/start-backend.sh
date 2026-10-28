#!/bin/bash

set -e

cd ../backend

export TESTING=true
export PUBLIC_READ_LIMIT_PER_MINUTE=100000

echo "Migrating test database..."
uv run alembic upgrade head

echo "Starting backend server on port 8020..."
uv run uvicorn app:app --port 8020
