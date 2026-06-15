#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOYMENT_DIR="$(dirname "$SCRIPT_DIR")"
ROOT_DIR="$(dirname "$DEPLOYMENT_DIR")"

TAG=${1:-prod}

echo "Deploying fireons with tag: $TAG"

# Fetch Pulumi stack outputs
echo "Fetching Pulumi stack outputs..."
pulumi stack output --stack prod --cwd "$DEPLOYMENT_DIR/infra" 2>/dev/null || {
    echo "Error: Pulumi stack not found. Run 'pulumi up' in deployment/infra first."
    exit 1
}

eval "$(pulumi stack output --stack prod --cwd "$DEPLOYMENT_DIR/infra" --shell)"

if [ -z "${ECR_BACKEND:-}" ] || [ -z "${ECR_FRONTEND:-}" ] || [ -z "${ECR_CADDY:-}" ]; then
    echo "Error: Missing ECR URIs in Pulumi stack outputs"
    exit 1
fi

# Save SSH key
echo "Saving SSH key..."
echo "$SSH_PRIVATE_KEY" > ~/.ssh/fireons-key.pem 2>/dev/null || true
chmod 600 ~/.ssh/fireons-key.pem 2>/dev/null || true

# Authenticate Docker to ECR
echo "Authenticating Docker to ECR..."
aws ecr get-login-password --region ap-south-1 | docker login --username AWS --password-stdin "$(echo "$ECR_BACKEND" | cut -d/ -f1)"

# Build and push backend image
echo "Building and pushing backend image..."
docker build -t "$ECR_BACKEND:$TAG" \
    --platform linux/amd64 \
    -f "$ROOT_DIR/backend/Dockerfile" \
    "$ROOT_DIR/backend"
docker push "$ECR_BACKEND:$TAG"

# Build and push frontend image
echo "Building and pushing frontend image..."
docker build -t "$ECR_FRONTEND:$TAG" \
    --platform linux/amd64 \
    -f "$ROOT_DIR/frontend/Dockerfile" \
    "$ROOT_DIR/frontend"
docker push "$ECR_FRONTEND:$TAG"

# Build and push Caddy image
echo "Building and pushing Caddy image..."
docker build -t "$ECR_CADDY:$TAG" \
    --platform linux/amd64 \
    -f "$DEPLOYMENT_DIR/docker/Dockerfile.caddy" \
    "$DEPLOYMENT_DIR"
docker push "$ECR_CADDY:$TAG"

# Configure environment on EC2
echo "Setting up environment on EC2..."
bash "$SCRIPT_DIR/setup_env.sh"

# Copy docker-compose and deploy
echo "Copying docker-compose.yml to EC2..."
scp -o StrictHostKeyChecking=no -i ~/.ssh/fireons-key.pem \
    "$DEPLOYMENT_DIR/docker-compose.yml" \
    ubuntu@"$ELASTIC_IP":/srv/app/docker-compose.yml

echo "Deploying on EC2..."
ssh -o StrictHostKeyChecking=no -i ~/.ssh/fireons-key.pem ubuntu@"$ELASTIC_IP" << 'EOF'
    set -euo pipefail
    cd /srv/app
    export AWS_DEFAULT_REGION=ap-south-1

    # Authenticate to ECR
    aws ecr get-login-password --region ap-south-1 | docker login --username AWS --password-stdin "$(echo "$ECR_BACKEND" | cut -d/ -f1)"

    # Pull latest images
    docker compose pull

    # Restart services
    docker compose up -d

    # Clean up old images
    docker image prune -f
EOF

echo "Deployment complete!"
echo "Frontend: https://app.fireons.com"
echo "Backend: https://app.fireons.com/api/health"
