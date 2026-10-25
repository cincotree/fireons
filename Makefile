.DEFAULT_GOAL := help

.PHONY: help setup install env db db-create migrate \
	backend-setup backend backend-test scrape scraper-worker \
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
	@echo "  scrape              Run the SEBI scraper once"
	@echo "  scraper-worker      Run the weekly scraper scheduler in the foreground"
	@echo ""
	@echo "Docker (local)"
	@echo "  compose-up          Start Postgres, migrations, backend and frontend in Docker"
	@echo "  compose-up-scraper  Same, plus the scheduled scraper worker"
	@echo "  compose-down        Stop the Docker stack"
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

scrape:
	cd backend && uv run python -m scraping run sebi_ria

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
