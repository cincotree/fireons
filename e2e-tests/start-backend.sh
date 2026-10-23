#!/bin/bash

cd ../backend

echo "Applying database migrations..."
TESTING=true uv run alembic upgrade head

echo "Starting backend server on port 8020..."
PUBLIC_READ_LIMIT_PER_MINUTE=100000 TESTING=true uv run uvicorn app:app --port 8020
