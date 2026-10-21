.DEFAULT_GOAL := help

.PHONY: help install db \
	backend-setup backend backend-test \
	frontend-setup frontend frontend-build frontend-lint \
	e2e-setup e2e e2e-headed e2e-ui e2e-debug e2e-report \
	test

help:
	@echo "Usage: make <target>"
	@echo ""
	@echo "Setup"
	@echo "  install          Install backend, frontend and e2e dependencies"
	@echo "  db               Start the local Postgres container"
	@echo "  backend-setup    Install backend dependencies"
	@echo "  frontend-setup   Install frontend dependencies"
	@echo "  e2e-setup        Install e2e dependencies and the Playwright browser"
	@echo ""
	@echo "Run"
	@echo "  backend          Apply migrations and start the backend with reload"
	@echo "  frontend         Start the frontend dev server"
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

install: backend-setup frontend-setup e2e-setup

db:
	docker start fireons-postgres 2>/dev/null || docker run -d --name fireons-postgres \
		-e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=fireons_development \
		-p 5432:5432 postgres:16-alpine

backend-setup:
	cd backend && uv sync

backend:
	cd backend && uv run alembic upgrade head && uv run uvicorn app:app --reload

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
