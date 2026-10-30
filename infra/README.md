# Infrastructure

Terraform (OpenTofu compatible) for the AWS foundation in `ap-southeast-1`. Nothing here contains account IDs or secret values.

## Layout

- `modules/fireons` is the whole stack for one environment (deploy role, secret, certificates, API, web app). Names are derived from `project` and `environment`, for example `fireons-production-api`.
- `environments/production` is the root that holds the state backend config, providers, the account-wide GitHub OIDC provider, budgets, and one `module "fireons"` call.
- A stage environment is a new `environments/stage` root that copies `environments/production`, sets `environment = "stage"`, its own domains, and looks up the existing OIDC provider with a data source if it shares the account. Run `./bootstrap.sh stage` for its state key.

## What it creates

- GitHub OIDC provider and the `fireons-production-github-deploy` role, assumable only by `repo:cincotree/fireons:environment:production`
- Secrets Manager secret `fireons/production` as an empty shell (no secret version is managed, so values never enter Terraform state) for the keys `SECRET_KEY`, `DATABASE_URL`, `ANTHROPIC_API_KEY`
- ACM certificates for `app.fireons.com` and `api.fireons.com` in `us-east-1` (CloudFront)
- API: Lambda `fireons-production-api` (arm64, Python 3.12, Lambda Web Adapter layer) with alias `live`, a Function URL on the alias, and a CloudFront distribution in front
- Web app: private S3 bucket `fireons-production-webapp-<account>`, CloudFront distribution with OAC, a path rewrite function, custom 404 and security headers
- The API Lambda has reserved concurrency (`api_reserved_concurrency`, default 3, set it to `null` for no reservation) so a flood of requests cannot exhaust database connections or run up costs
- The API runs with `INVITE_ONLY=true` (`invite_only`, default true): registration needs an invite code from the `invites` table
- AWS Budgets at 1 and 10 USD per month (actual and forecasted) notifying `budget_email`

## Human steps

Before Terraform:
1. AWS account on the Paid plan, MFA on the root user, and an Identity Center admin user. Log in with that user.
2. Check the Lambda concurrent executions quota in `ap-southeast-1`. Reserved concurrency of 3 needs a quota of at least 13, because AWS keeps 10 unreserved. Check it with `aws service-quotas get-service-quota --service-code lambda --quota-code L-B99A9384 --query Quota.Value`. If the quota is 10, request an increase or set `api_reserved_concurrency = null` in `terraform.tfvars`.
3. Check that the Lambda Web Adapter layer version in `lambda_web_adapter_layer_arn` still exists in `ap-southeast-1` (see https://github.com/awslabs/aws-lambda-web-adapter).

Apply, phase 1 (CloudFront default domains):
4. `./bootstrap.sh` creates the versioned, encrypted state bucket and writes `environments/production/backend.hcl` (gitignored).
5. `cd environments/production`, `cp terraform.tfvars.example terraform.tfvars` and set `budget_email`.
6. `terraform init -backend-config=backend.hcl`, then `terraform plan` and `terraform apply`.
7. Fill the secret with `aws secretsmanager put-secret-value --secret-id fireons/production --secret-string file://secret.json`, keys `SECRET_KEY`, `DATABASE_URL` (Neon direct URL as `postgresql+psycopg://...?sslmode=require`) and `ANTHROPIC_API_KEY`. Delete `secret.json` afterwards.

First deploy from your machine (AWS credentials for the same account, `uv`, Node, `zip`):
8. `make deploy-api` (names derive from `DEPLOY_ENV`, default `production`) builds the zip, runs migrations against Neon, publishes a version, smoke tests `/health` and `/health/ready`, then moves alias `live`.
9. Export the values from `terraform output -json github_environment_variables` (`WEBAPP_BUCKET`, `WEBAPP_DISTRIBUTION_ID`, `WEBAPP_URL`, `NEXT_PUBLIC_API_BASE_URL`) and run `make deploy-webapp`.
10. Open the `webapp_url` output. Register or log in and check the net worth page. `curl <api_base_url>/health` should return 200.

Deploy from GitHub Actions:
11. In GitHub, create the `production` environment (deployment branches: `main` only, no required reviewers) and add the keys of the `github_environment_variables` output as environment variables.
12. Trigger the `Release` workflow with `workflow_dispatch` (ref `main`) and check both jobs pass. Run it from another branch or a job without `environment: production` to confirm the role cannot be assumed.
13. After that, every green CI run on `main` releases automatically.

Custom domains, phase 2:
14. Add the `certificate_validation_records` output as CNAME records in Namecheap. Wait until both certificates show `ISSUED`.
15. Set `enable_custom_domains = true` in `terraform.tfvars` and apply again. This attaches the aliases and updates the Lambda CORS origin.
16. Add CNAME records in Namecheap: `app` to `webapp_distribution_domain_name` and `api` to `api_distribution_domain_name`.
17. Update the GitHub environment variables `WEBAPP_URL` and `NEXT_PUBLIC_API_BASE_URL` from the new output and run the `Release` workflow again so the frontend is rebuilt against `https://api.fireons.com`.

Checks: `terraform plan` is clean after apply, the budget alert test email arrives, and the secret values are not in state (`terraform state list` shows only the secret shell).

## Invite-only registration

Production registration needs an invite code from the `invites` table, which you manage with SQL. See [docs/invite-only-registration.md](../docs/invite-only-registration.md) for how to create, revoke and inspect invites.

## Notes

- State locking uses the S3 native lockfile, so no DynamoDB table is needed (Terraform or OpenTofu 1.10+).
- The deploy role can only update Lambda code and aliases for `fireons-production-*` functions, write objects to `fireons-production-*` buckets, and create CloudFront invalidations.
- Certificate validation resources are intentionally omitted so `apply` does not block on DNS, and the distributions only use the certificates once `enable_custom_domains` is true.
- Terraform owns the Lambda configuration and the alias target is ignored after creation, so the release workflow moves `live` without causing drift. The initial code is a placeholder that the first `make deploy-api` replaces.
- The Lambda has 1769 MB of memory (one full vCPU), which makes password hashing and cold starts faster. Each Lambda instance keeps one database connection (`POOL_SIZE=1`, `MAX_OVERFLOW=1`) between requests, checked with a ping before use, instead of reconnecting on every request.
- Terraform changes to Lambda memory or environment variables only reach production after the next `make deploy-api`, because a published version keeps the settings it was created with.
- Releases never run Terraform.
