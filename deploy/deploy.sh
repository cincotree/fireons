#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/config.sh"
SERVER_USER="${SERVER_USER:-deploy}"
APP_DIR="/opt/fireons"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

SECRET_KEY="${SECRET_KEY:-$(openssl rand -hex 32)}"

echo "==> Building Docker images for linux/amd64..."

echo "Building backend..."
docker build --platform=linux/amd64 -t fireons/backend:latest "$PROJECT_DIR/backend"

echo "Building frontend..."
docker build --platform=linux/amd64 -t fireons/frontend:latest "$PROJECT_DIR/frontend"

echo "==> Saving Docker images..."
mkdir -p "$SCRIPT_DIR/tmp"
docker save fireons/backend:latest | gzip > "$SCRIPT_DIR/tmp/backend.tar.gz"
docker save fireons/frontend:latest | gzip > "$SCRIPT_DIR/tmp/frontend.tar.gz"

echo "==> Ensuring app directory exists on server..."
ssh -i "$SSH_KEY" "$SERVER_USER@$SERVER_IP" "sudo mkdir -p $APP_DIR && sudo chown -R \$USER:\$USER $APP_DIR"

echo "==> Transferring images to server..."
scp -i "$SSH_KEY" "$SCRIPT_DIR/tmp/backend.tar.gz" "$SERVER_USER@$SERVER_IP:$APP_DIR/"
scp -i "$SSH_KEY" "$SCRIPT_DIR/tmp/frontend.tar.gz" "$SERVER_USER@$SERVER_IP:$APP_DIR/"

echo "==> Transferring configuration files..."
scp -i "$SSH_KEY" "$SCRIPT_DIR/docker-compose.yml" "$SERVER_USER@$SERVER_IP:$APP_DIR/"
scp -i "$SSH_KEY" "$SCRIPT_DIR/nginx.conf" "$SERVER_USER@$SERVER_IP:$APP_DIR/"

echo "==> Creating .env file on server..."
ssh -i "$SSH_KEY" "$SERVER_USER@$SERVER_IP" "cat > $APP_DIR/.env" << ENVFILE
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=fireons_stage
SECRET_KEY=$SECRET_KEY
CORS_ORIGINS=https://stage.fireons.com
ENVFILE

echo "==> Loading images and deploying on server..."
ssh -i "$SSH_KEY" "$SERVER_USER@$SERVER_IP" bash << 'REMOTE_SCRIPT'
set -euo pipefail
export PATH="/usr/bin:/usr/local/bin:/usr/sbin:/sbin:$PATH"
cd /opt/fireons

echo "Loading backend image..."
gunzip -c backend.tar.gz | docker load

echo "Loading frontend image..."
gunzip -c frontend.tar.gz | docker load

echo "Cleaning up image archives..."
rm -f backend.tar.gz frontend.tar.gz

echo "Starting database for migrations..."
docker compose up -d db
sleep 5

echo "Running database migrations..."
docker compose run --rm backend uv run alembic upgrade head

echo "Starting all services..."
docker compose up -d

echo "Waiting for services to start..."
sleep 10

echo "Service status:"
docker compose ps

echo "Deployment complete!"
REMOTE_SCRIPT

echo ""
echo "==> Cleaning up local temp files..."
rm -rf "$SCRIPT_DIR/tmp"

echo ""
echo "==> Deployment complete!"
echo "    Frontend: https://stage.fireons.com"
echo "    Backend:  https://stage.fireons.com/api"
