.DEFAULT_GOAL := help

TF_ENV ?= production
TF_DIR = infra/environments/$(TF_ENV)

.PHONY: tf-bootstrap tf-init tf-fmt tf-validate tf-plan tf-apply tf-output create-admin deploy-api deploy-jobs-image deploy-webapp help setup install env db db-create migrate \
	backend-setup backend backend-test scrape export-places import-places enrich-places enrich-nri find-websites scraper-worker \
	compose-up compose-up-scraper compose-down \
	frontend-setup frontend frontend-build frontend-lint \
	e2e-setup e2e e2e-headed e2e-ui e2e-debug e2e-report \
	test

help:
	@echo "Usage: make <target>"
	@echo ""
	@echo "Setup"
	@echo "  setup            One-time local setup: deps, env files, Postgres, databases, migrations"
	@echo "  install          Install backend, frontend and e2e dependencies"
	@echo "  env              Create backend/.env and frontend/.env.local from the samples if missing"
	@echo "  db               Start the local Postgres container"
	@echo "  db-create        Create the development and e2e databases if missing"
	@echo "  create-admin     Create an admin account: make create-admin USERNAME=<name>"
	@echo "  migrate          Apply migrations to the development database"
	@echo "  backend-setup    Install backend dependencies"
	@echo "  frontend-setup   Install frontend dependencies"
	@echo "  e2e-setup        Install e2e dependencies and the Playwright browser"
	@echo ""
	@echo "Run"
	@echo "  backend          Apply migrations and start the backend with reload"
	@echo "  frontend         Start the frontend dev server"
	@echo ""
	@echo "Registry scraper"
	@echo "  scrape              Run one scraper once (SOURCE=sebi_ria, sebi_research_analyst, fee_only_india or fpsb_cfp)"
	@echo "  scraper-worker      Run the weekly scraper scheduler in the foreground"
	@echo "  enrich-nri          Check firm websites for NRI signals (python -m enrichment review-queue to review)"
	@echo "  export-places       Export professionals found via Google Places to backend/exports (resumable, quota-capped)"
	@echo "  enrich-places       Search the web (Tavily) for details of imported Google listings; run daily until done"
	@echo "  find-websites       Find websites for unverified listings (register match, domain guess, Tavily search; run daily)"
	@echo "  import-places       Load the Google Places CSV into the directory as unverified listings"
	@echo ""
	@echo "Docker (local)"
	@echo "  compose-up          Start Postgres, migrations, backend and frontend in Docker"
	@echo "  compose-up-scraper  Same, plus the scheduled scraper worker"
	@echo "  compose-down        Stop the Docker stack"
	@echo ""
	@echo "Deploy (needs AWS credentials, see infra/README.md)"
	@echo "  deploy-api       Build and release the API to Lambda"
	@echo "  deploy-jobs-image Build and push the Fargate jobs image to ECR"
	@echo "  deploy-webapp    Build and release the frontend to S3 and CloudFront"
	@echo ""
	@echo "Infrastructure (Terraform, needs AWS credentials; TF_ENV=production by default)"
	@echo "  tf-bootstrap     Create the state bucket if missing and write backend.hcl"
	@echo "  tf-init          Initialize Terraform with backend.hcl"
	@echo "  tf-fmt           Format Terraform files"
	@echo "  tf-validate      Validate Terraform without touching the backend"
	@echo "  tf-plan          Write a plan to review (creates terraform.tfvars from the example if missing)"
	@echo "  tf-apply         Apply the plan written by tf-plan"
	@echo "  tf-output        Show Terraform outputs"
	@echo ""
	@echo "Test and check"
	@echo "  test             Run backend tests and e2e tests"
	@echo "  backend-test     Run backend tests"
	@echo "  e2e              Run e2e tests"
	@echo "  e2e-headed       Run e2e tests in a visible browser"
	@echo "  e2e-ui           Open the Playwright UI"
	@echo "  e2e-debug        Run e2e tests with the Playwright inspector"
	@echo "  e2e-report       Open the last e2e report"
	@echo "  frontend-lint    Lint the frontend"
	@echo "  frontend-build   Build the frontend for production"

setup: install env db db-create migrate

install: backend-setup frontend-setup e2e-setup

env:
	@test -f backend/.env || (cp backend/.env.sample backend/.env && echo "Created backend/.env")
	@test -f frontend/.env.local || (cp frontend/.env.local.sample frontend/.env.local && echo "Created frontend/.env.local")

db:
	docker start fireons-postgres 2>/dev/null || docker run -d --name fireons-postgres \
		-e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=fireons_development \
		-p 5432:5432 postgres:16-alpine

db-create:
	cd backend && uv run python -m scripts.create_databases

migrate:
	cd backend && uv run alembic upgrade head

SOURCE ?= sebi_ria

scrape:
	cd backend && uv run python -m scraping run $(SOURCE)

import-places:
	cd backend && uv run python -m scraping import-places exports/places_professionals.csv

export-places:
	cd backend && uv run python -m enrichment places

enrich-places:
	cd backend && uv run python -m enrichment enrich-places exports/places_professionals.csv

find-websites:
	cd backend && uv run python -m enrichment find-websites

enrich-nri:
	cd backend && uv run python -m enrichment nri

scraper-worker:
	cd backend && uv run python -m scraping worker

compose-up:
	docker compose up --build

compose-up-scraper:
	docker compose --profile scraper up --build

compose-down:
	docker compose --profile scraper down

backend-setup:
	cd backend && uv sync

create-admin:
	cd backend && uv run python -m scripts.create_admin $(USERNAME)

backend: migrate
	cd backend && uv run uvicorn app:app --reload

backend-test:
	cd backend && uv run pytest

frontend-setup:
	cd frontend && npm install

frontend:
	cd frontend && npm run dev

frontend-build:
	cd frontend && npm run build

frontend-lint:
	cd frontend && npm run lint

e2e-setup:
	cd e2e-tests && npm install && npx playwright install chromium

e2e:
	cd e2e-tests && npm test

e2e-headed:
	cd e2e-tests && npm run test:headed

e2e-ui:
	cd e2e-tests && npm run test:ui

e2e-debug:
	cd e2e-tests && npm run test:debug

e2e-report:
	cd e2e-tests && npm run report

test: backend-test e2e

deploy-api:
	./scripts/deploy-api.sh

deploy-jobs-image:
	./scripts/deploy-jobs-image.sh

deploy-webapp:
	./scripts/deploy-webapp.sh

tf-bootstrap:
	./infra/bootstrap.sh $(TF_ENV)

$(TF_DIR)/terraform.tfvars:
	cp $(TF_DIR)/terraform.tfvars.example $@
	@echo "Created $@ from the example, review it before applying"

tf-init:
	@test -f $(TF_DIR)/backend.hcl || (echo "Missing $(TF_DIR)/backend.hcl, run: make tf-bootstrap TF_ENV=$(TF_ENV)" && exit 1)
	cd $(TF_DIR) && terraform init -reconfigure -input=false -backend-config=backend.hcl

tf-fmt:
	cd infra && terraform fmt -recursive

tf-validate:
	cd $(TF_DIR) && (test -d .terraform || terraform init -backend=false -input=false > /dev/null) && terraform validate

tf-plan: $(TF_DIR)/terraform.tfvars
	cd $(TF_DIR) && terraform plan -input=false -out=$(TF_ENV).tfplan

tf-apply:
	cd $(TF_DIR) && terraform apply -input=false $(TF_ENV).tfplan

tf-output:
	cd $(TF_DIR) && terraform output
