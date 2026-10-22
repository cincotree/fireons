# Infrastructure

Terraform (OpenTofu compatible) for the AWS foundation in `ap-southeast-1`. Nothing here contains account IDs or secret values.

## What it creates

- GitHub OIDC provider and the `fireons-github-deploy` role, assumable only by `repo:cincotree/fireons:environment:production`
- Secrets Manager secret `fireons/production` with keys `SECRET_KEY`, `DATABASE_URL`, `ANTHROPIC_API_KEY` (placeholder values, never overwritten by Terraform)
- ACM certificates for `app.fireons.com` and `api.fireons.com` in `us-east-1` (CloudFront)
- SNS topic `fireons-alarms` with an email subscription
- AWS Budgets at 1 and 10 USD per month (actual and forecasted) notifying the topic and the email

## First run

1. Authenticate to the AWS account with admin access.
2. `./bootstrap.sh` creates the versioned, encrypted state bucket and writes `backend.hcl` (gitignored).
3. `cp terraform.tfvars.example terraform.tfvars` and set `alarm_email`.
4. `terraform init -backend-config=backend.hcl`
5. `terraform plan`, then `terraform apply`.
6. Confirm the SNS subscription email.
7. Put the real values into the secret, for example with `aws secretsmanager put-secret-value --secret-id fireons/production --secret-string file://secret.json`.
8. Add the `certificate_validation_records` output as CNAMEs in the `fireons.com` DNS zone. ACM validates the certificates once they resolve.
9. In GitHub, create the `production` environment and set the deploy role ARN (`github_deploy_role_arn` output) for workflows to assume.

## Notes

- State locking uses the S3 native lockfile, so no DynamoDB table is needed (Terraform or OpenTofu 1.10+).
- The deploy role has no permissions until `deploy_role_policy_arns` is set or policies are attached by the deployment stack.
- Certificate validation resources are intentionally omitted so `apply` does not block on DNS.
