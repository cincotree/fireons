#!/bin/bash

cd ../backend

export TESTING=true

echo "Migrating test database..."
uv run alembic upgrade head

echo "Starting backend server on port 8020..."
uv run uvicorn app:app --port 8020
