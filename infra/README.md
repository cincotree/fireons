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

## Background jobs

Jobs run as on-demand Fargate tasks, so idle cost is the ECR storage only. The in-process APScheduler job stays disabled in production (`EXCHANGE_RATE_SYNC_ENABLED=false`) because a Lambda is frozen between requests.

- Each task runs `python -m jobs.runner`. The runner records a row in `job_runs` (status, error, task ARN, timestamps), runs the job from `backend/jobs/registry.py`, and exits non-zero on failure.
- EventBridge Scheduler: each entry in `scheduled_jobs` starts a task directly with `JOB_NAME`; the runner creates the `job_runs` row itself. The default entry runs `exchange_rate_sync` at 20:30 UTC.
- Online triggers call `jobs.launcher.launch_job(name, payload)`, which inserts a `job_runs` row and calls `ecs:RunTask` with `JOB_RUN_ID`. Everything is found by convention from `APP_ENV`: cluster and task definition family are both `fireons-<env>-jobs`, the security group has the same name, and subnets are the default VPC subnets (looked up once per process). The caller needs `ecs:RunTask`, `iam:PassRole` for the task and execution roles, and `ec2:DescribeSubnets` and `ec2:DescribeSecurityGroups`. The API Lambda role has these permissions (`launch-jobs` policy).
- Admins are a separate identity from app users: an `admins` table (username and bcrypt password hash only), its own login `POST /admin/login`, and a token with `role: admin` that user endpoints reject (and the reverse). Create one with `make create-admin USERNAME=<name>` (prompts for a password of at least 12 characters, or reads `ADMIN_PASSWORD`). In production run the same command with `DATABASE_URL` pointing at Neon, or insert a row with a bcrypt hash.
- The admin UI is `/admin/login` then `/admin/jobs` (not linked from the app nav). The API is `POST /admin/jobs/runs` (body `{"job": "exchange_rate_sync", "payload": {}}`), `GET /admin/jobs/runs?status=&limit=` and `GET /admin/jobs` (registered job names).
- Test locally without AWS: set `JOBS_RUN_LOCALLY=true` in `backend/.env` (it is in `.env.sample`). `launch_job` then starts `python -m jobs.runner` as a local subprocess instead of a Fargate task, and the run is recorded the same way (`task_arn` shows `local:<pid>`). Run the app (`make backend`, `make frontend`), run `make create-admin USERNAME=<name>`, then open http://localhost:3000/admin/login to sign in, launch a job and watch its runs. A scheduled start can be mimicked with `cd backend && JOB_NAME=exchange_rate_sync uv run python -m jobs.runner`.
- There are no automatic retries. A failed run stays `failed` in `job_runs` with its error. Relaunch it by hand with `jobs.launcher.launch_run(run_id)`, or start a new run. A task killed without writing its status stays `queued` or `running`, so check `job_runs` and the task logs. Jobs should be idempotent.
- Resources: ECR repository (keeps 5 images), ECS cluster, task definition (arm64, 0.5 vCPU, 1 GB), egress only security group, log group. There is no service and no NAT gateway. Tasks use the default VPC public subnets with a public IP to reach Neon and AWS APIs.
- Build and push the image with `JOBS_ECR_REPOSITORY_URL=<jobs_ecr_repository_url output> make deploy-jobs-image` before the first job runs, and after any change under `backend/`.
- Add a job by registering it in `backend/jobs/registry.py`, and add a `scheduled_jobs` entry if it is periodic.

## Invite-only registration

Production registration needs an invite code from the `invites` table, which you manage with SQL. See [docs/invite-only-registration.md](../docs/invite-only-registration.md) for how to create, revoke and inspect invites.

## Which version is deployed

Every build records its git commit.
- API: `curl https://api.fireons.com/health` returns `{"status":"ok","version":"<commit>","built_at":"<time>"}`. The same fields are in `/health/ready`. A local run reports `"version":"dev"`.
- Web app: `curl https://app.fireons.com/version.json` returns the same two fields.
- A `-dirty` suffix means the build had uncommitted changes, which only happens for manual `make deploy-*` runs.
- The release scripts check these: the API smoke test fails, and the alias stays put, if the new version does not report the commit that was built, and the web app step fails if the site does not serve the new `version.json`.

## Notes

- State locking uses the S3 native lockfile, so no DynamoDB table is needed (Terraform or OpenTofu 1.10+).
- The deploy role can only update Lambda code and aliases for `fireons-production-*` functions, write objects to `fireons-production-*` buckets, and create CloudFront invalidations.
- Certificate validation resources are intentionally omitted so `apply` does not block on DNS, and the distributions only use the certificates once `enable_custom_domains` is true.
- Terraform owns the Lambda configuration and the alias target is ignored after creation, so the release workflow moves `live` without causing drift. The initial code is a placeholder that the first `make deploy-api` replaces.
- The Lambda has 1769 MB of memory (one full vCPU), which makes password hashing and cold starts faster. Each Lambda instance keeps one database connection (`POOL_SIZE=1`, `MAX_OVERFLOW=1`) between requests, checked with a ping before use, instead of reconnecting on every request.
- Terraform changes to Lambda memory or environment variables only reach production after the next `make deploy-api`, because a published version keeps the settings it was created with.
- Releases never run Terraform.
