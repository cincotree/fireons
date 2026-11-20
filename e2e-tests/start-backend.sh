#!/bin/bash

set -e

cd ../backend

export TESTING=true
export JOBS_RUN_LOCALLY=true
export PUBLIC_READ_LIMIT_PER_MINUTE=100000
export FRONTEND_URL=http://localhost:3020
export OAUTH_REDIRECT_BASE_URL=http://localhost:8020
export GOOGLE_OAUTH_CLIENT_ID=e2e-google-client
export GOOGLE_OAUTH_CLIENT_SECRET=e2e-google-secret
export REDDIT_OAUTH_CLIENT_ID=e2e-reddit-client
export REDDIT_OAUTH_CLIENT_SECRET=e2e-reddit-secret

echo "Migrating test database..."
uv run alembic upgrade head

echo "Starting backend server on port 8020..."
uv run uvicorn app:app --port 8020
