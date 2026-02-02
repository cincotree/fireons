#!/bin/bash
set -euo pipefail

SERVER_IP="172.105.48.221"
SERVER_USER="${SERVER_USER:-deploy}"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/linode_key}"
DOMAIN="stage.fireons.com"
APP_DIR="/opt/fireons"

echo "==> Connecting to server and running setup..."

ssh -i "$SSH_KEY" "$SERVER_USER@$SERVER_IP" bash << 'REMOTE_SCRIPT'
set -euo pipefail
export PATH="/usr/bin:/usr/local/bin:/usr/sbin:/sbin:$PATH"

echo "==> Updating system packages..."
sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get upgrade -y

echo "==> Installing Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    rm get-docker.sh
    sudo systemctl enable docker
    sudo systemctl start docker
fi

echo "==> Adding user to docker group..."
sudo groupadd -f docker
sudo usermod -aG docker $USER

echo "==> Installing Docker Compose plugin..."
sudo apt-get install -y docker-compose-plugin

echo "==> Installing Certbot..."
sudo apt-get install -y certbot

echo "==> Creating application directory structure..."
sudo mkdir -p /opt/fireons/data/postgres
sudo mkdir -p /opt/fireons/certs
sudo chown -R $USER:$USER /opt/fireons

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
