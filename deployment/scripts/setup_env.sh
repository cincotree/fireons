#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOYMENT_DIR="$(dirname "$SCRIPT_DIR")"

echo "Setting up environment on EC2..."

INFRA_DIR="$DEPLOYMENT_DIR/infra"
STACK="prod"

eval "$(pulumi stack output --stack "$STACK" --cwd "$INFRA_DIR" --shell 2>/dev/null)"

SUPABASE_DB_URL=$(pulumi config get --stack "$STACK" --cwd "$INFRA_DIR" fireons-infra:supabase_db_url 2>/dev/null || echo "")
JWT_SECRET=$(pulumi config get --stack "$STACK" --cwd "$INFRA_DIR" fireons-infra:jwt_secret 2>/dev/null || echo "")
SECRET_KEY=$(pulumi config get --stack "$STACK" --cwd "$INFRA_DIR" fireons-infra:secret_key 2>/dev/null || echo "")

REQUIRED_VARS=(SUPABASE_DB_URL JWT_SECRET SECRET_KEY ECR_BACKEND ECR_FRONTEND ECR_CADDY ELASTIC_IP)
for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var:-}" ]; then
        echo "Error: $var is not set. Run 'pulumi up' in deployment/infra first."
        exit 1
    fi
done

if [ ! -f ~/.ssh/fireons-key.pem ]; then
    echo "$SSH_PRIVATE_KEY" > ~/.ssh/fireons-key.pem
    chmod 600 ~/.ssh/fireons-key.pem
fi

SSH_CMD="ssh -o StrictHostKeyChecking=no -i ~/.ssh/fireons-key.pem ubuntu@$ELASTIC_IP"

echo "Ensuring prerequisites on EC2..."
$SSH_CMD << 'EOF'
    set -euo pipefail
    if ! command -v docker &>/dev/null; then
        sudo apt-get update
        sudo apt-get install -y ca-certificates curl
        sudo install -m 0755 -d /etc/apt/keyrings
        sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
        sudo chmod a+r /etc/apt/keyrings/docker.asc
        echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
        sudo apt-get update
        sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
        sudo usermod -aG docker ubuntu
        newgrp docker
    fi
    if ! command -v aws &>/dev/null; then
        sudo apt-get install -y unzip
        curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
        unzip -q awscliv2.zip
        sudo ./aws/install
        rm -rf aws awscliv2.zip
    fi
EOF

echo "Creating /srv/app directory..."
$SSH_CMD "sudo mkdir -p /srv/app && sudo chown ubuntu:ubuntu /srv/app"

echo "Writing .env file..."
ssh -o StrictHostKeyChecking=no -i ~/.ssh/fireons-key.pem ubuntu@"$ELASTIC_IP" \
    "cat > /srv/app/.env" << ENVEOF
DATABASE_URL=${SUPABASE_DB_URL}
SECRET_KEY=${SECRET_KEY}
JWT_SECRET=${JWT_SECRET}
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
BACKEND_HOST=backend:8000
ECR_BACKEND=${ECR_BACKEND}
ECR_FRONTEND=${ECR_FRONTEND}
ECR_CADDY=${ECR_CADDY}
ENVEOF

echo "Copying Caddyfile..."
scp -o StrictHostKeyChecking=no -i ~/.ssh/fireons-key.pem \
    "$DEPLOYMENT_DIR/Caddyfile" \
    ubuntu@"$ELASTIC_IP":/srv/app/Caddyfile

echo "Environment setup complete."
