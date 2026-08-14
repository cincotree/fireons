.PHONY: install db \
	backend-setup backend backend-test \
	frontend-setup frontend frontend-build frontend-lint \
	e2e-setup e2e e2e-headed e2e-ui e2e-debug e2e-report \
	test

install: backend-setup frontend-setup e2e-setup

db:
	docker start fireons-postgres 2>/dev/null || docker run -d --name fireons-postgres \
		-e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=fireons_development \
		-p 5432:5432 postgres:16-alpine

backend-setup:
	cd backend && uv sync

backend:
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
