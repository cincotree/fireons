#!/bin/bash
set -euo pipefail

SERVER_IP="172.105.48.221"
SERVER_USER="root"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/linode_key}"
DOMAIN="stage.fireons.com"
APP_DIR="/opt/fireons"

echo "==> Connecting to server and running setup..."

ssh -i "$SSH_KEY" "$SERVER_USER@$SERVER_IP" bash << 'REMOTE_SCRIPT'
set -euo pipefail

echo "==> Updating system packages..."
apt-get update
apt-get upgrade -y

echo "==> Installing Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
    systemctl enable docker
    systemctl start docker
fi

echo "==> Installing Docker Compose plugin..."
apt-get install -y docker-compose-plugin

echo "==> Installing Certbot..."
apt-get install -y certbot

echo "==> Creating application directory structure..."
mkdir -p /opt/fireons/data/postgres
mkdir -p /opt/fireons/certs

echo "==> Docker version:"
docker --version
docker compose version

echo "==> Server setup complete!"
REMOTE_SCRIPT

echo ""
echo "==> Server setup complete!"
echo ""
echo "Next steps:"
echo "1. Point DNS A record for $DOMAIN to $SERVER_IP"
echo "2. Run the following command to generate SSL certificate:"
echo "   ssh -i $SSH_KEY $SERVER_USER@$SERVER_IP 'certbot certonly --standalone -d $DOMAIN'"
echo "3. Run ./deploy.sh to deploy the application"
