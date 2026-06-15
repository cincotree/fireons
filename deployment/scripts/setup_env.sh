#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOYMENT_DIR="$(dirname "$SCRIPT_DIR")"

echo "Setting up environment on EC2..."

# Fetch Pulumi stack outputs and config
INFRA_DIR="$DEPLOYMENT_DIR/infra"
STACK="prod"

# Fetch outputs
eval "$(pulumi stack output --stack "$STACK" --cwd "$INFRA_DIR" --shell 2>/dev/null)"

# Fetch config values
DB_PASSWORD=$(pulumi config get --stack "$STACK" --cwd "$INFRA_DIR" fireons-infra:db_password 2>/dev/null || echo "")
JWT_SECRET=$(pulumi config get --stack "$STACK" --cwd "$INFRA_DIR" fireons-infra:jwt_secret 2>/dev/null || echo "")
SECRET_KEY=$(pulumi config get --stack "$STACK" --cwd "$INFRA_DIR" fireons-infra:secret_key 2>/dev/null || echo "")
DOMAIN=$(pulumi config get --stack "$STACK" --cwd "$INFRA_DIR" fireons-infra:domain 2>/dev/null || echo "app.fireons.com")
CADDY_HOST="${DOMAIN}"

# Validate required variables
REQUIRED_VARS=(RDS_HOST DB_PASSWORD JWT_SECRET SECRET_KEY ECR_BACKEND ECR_FRONTEND ECR_CADDY ELASTIC_IP)
for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var:-}" ]; then
        echo "Error: $var is not set. Run 'pulumi up' in deployment/infra first."
        exit 1
    fi
done

# Save SSH key if not present
if [ ! -f ~/.ssh/fireons-key.pem ]; then
    echo "$SSH_PRIVATE_KEY" > ~/.ssh/fireons-key.pem
    chmod 600 ~/.ssh/fireons-key.pem
fi

SSH_CMD="ssh -o StrictHostKeyChecking=no -i ~/.ssh/fireons-key.pem ubuntu@$ELASTIC_IP"

# Install Docker and AWS CLI on EC2 if not present
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

# Ensure database exists on RDS
echo "Ensuring database exists..."
$SSH_CMD << 'EOF'
    sudo apt-get install -y postgresql-client 2>/dev/null || true
    PGPASSWORD="$DB_PASSWORD" psql -h "$RDS_HOST" -U fireons -d postgres -tc \
        "SELECT 1 FROM pg_database WHERE datname = 'fireons_prod'" | grep -q 1 || \
    PGPASSWORD="$DB_PASSWORD" psql -h "$RDS_HOST" -U fireons -d postgres -c \
        "CREATE DATABASE fireons_prod;"
EOF

# Create app directory
echo "Creating /srv/app directory..."
$SSH_CMD "sudo mkdir -p /srv/app && sudo chown ubuntu:ubuntu /srv/app"

# Write .env file
echo "Writing .env file..."
ssh -o StrictHostKeyChecking=no -i ~/.ssh/fireons-key.pem ubuntu@"$ELASTIC_IP" \
    "cat > /srv/app/.env" << ENVEOF
POSTGRES_USER=fireons
POSTGRES_PASSWORD=${DB_PASSWORD}
POSTGRES_HOST=${RDS_HOST}
POSTGRES_PORT=5432
POSTGRES_DB=fireons_prod
SECRET_KEY=${SECRET_KEY}
JWT_SECRET=${JWT_SECRET}
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
BACKEND_HOST=backend:8000
ECR_BACKEND=${ECR_BACKEND}
ECR_FRONTEND=${ECR_FRONTEND}
ECR_CADDY=${ECR_CADDY}
ENVEOF

# Copy Caddyfile
echo "Copying Caddyfile..."
scp -o StrictHostKeyChecking=no -i ~/.ssh/fireons-key.pem \
    "$DEPLOYMENT_DIR/Caddyfile" \
    ubuntu@"$ELASTIC_IP":/srv/app/Caddyfile

echo "Environment setup complete."
