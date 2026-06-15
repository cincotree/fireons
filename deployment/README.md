# Fireons Deployment

Infrastructure-as-code and deployment scripts for the Fireons application on AWS.

## Architecture

```
Internet -> app.fireons.com (DNS -> Elastic IP)
               |
            EC2 t3.small
               |
        +------+------+
        |             |
     Caddy (80/443)   |
     (TLS via LE)     |
        |             |
   +----+----+   +----+----+
   |         |   |         |
Frontend  Backend       RDS PostgreSQL
(Next.js) (FastAPI)     (db.t3.micro)
 :3000      :8000        :5432
```

## Prerequisites

- [Pulumi CLI](https://www.pulumi.com/docs/install/)
- [AWS CLI](https://aws.amazon.com/cli/) configured with `fireons-deploy` profile
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)

## First-Time Setup

1. Initialize the Pulumi stacks:
   ```bash
   cd deployment/infra && pulumi stack init prod
   cd ../cicd && pulumi stack init prod
   ```

2. Configure the infrastructure stack:
   ```bash
   cd deployment/infra
   pulumi config set aws:region ap-south-1
   pulumi config set aws:profile fireons-deploy
   pulumi config set fireons-infra:admin_cidr $(curl -s ifconfig.me)/32
   pulumi config set --secret fireons-infra:db_password <your-db-password>
   pulumi config set --secret fireons-infra:jwt_secret <your-jwt-secret>
   pulumi config set --secret fireons-infra:secret_key <your-secret-key>
   ```

3. Configure the CI/CD stack:
   ```bash
   cd deployment/cicd
   pulumi config set aws:region ap-south-1
   pulumi config set aws:profile fireons-deploy
   pulumi config set --secret fireons-cicd:github_token <your-github-pat>
   ```

4. Provision all infrastructure:
   ```bash
   cd deployment/infra
   pulumi up
   ```

5. Point DNS at the Elastic IP:
   - Add an A record for `app.fireons.com` pointing to the Elastic IP output from Pulumi.

6. Run the deploy script:
   ```bash
   AWS_PROFILE=fireons-deploy bash deployment/scripts/deploy.sh
   ```

7. Verify:
   ```bash
   curl -I https://app.fireons.com
   ```

## Ongoing Deploys

Automatic on merge to main (via GitHub Actions on CodeBuild). Manual deploy:

```bash
AWS_PROFILE=fireons-deploy bash deployment/scripts/deploy.sh [tag]
```

## SSH

```bash
ssh -i ~/.ssh/fireons-key.pem ubuntu@<elastic-ip>
```

## Teardown

```bash
cd deployment/infra && pulumi destroy
cd ../cicd && pulumi destroy
```

## Cost Estimate

| Resource | Estimated Monthly Cost |
|----------|----------------------|
| EC2 t3.small | ~$15 |
| RDS db.t3.micro | ~$15 |
| Elastic IP | ~$3.60 |
| EBS (40 GB gp3) | ~$3.20 |
| ECR (3 repos) | ~$1 |
| **Total** | **~$38/month** |
