# AGENTS.md

Guidance for AI coding agents working on this repository.

## Coding Standards

- **Do not add code comments anywhere unless explicitly requested.**
- Code should be self-documenting through clear naming and structure.
- Never use em dashes (--) in any content or code.

## Testing Requirements

Every new feature must ship with tests, not just the happy path:

- **Backend**: unit tests for new business logic, plus request-level tests for new API endpoints covering auth, validation errors, and success responses. Run `uv run pytest` and confirm new tests actually pass.
- **Frontend user flows**: a Playwright e2e spec (`e2e-tests/tests/`) driving the real UI, including at least one failure path, not only the happy path. Run it and confirm it passes against the real app before calling the work done.
- Extend existing test file patterns rather than inventing a new style. Flag pre-existing broken/stale tests found nearby instead of silently ignoring them or scope-creeping into unrelated fixes.
- Manually verify UI changes in a running browser — a green test suite is not proof the feature actually works end to end.

## Handling Personal Data

Never commit real personal, financial, or otherwise sensitive documents or data to this repository, even temporarily:

- Test fixtures must be synthetic, generated programmatically. Never copy in a real document, even redacted.
- If a real personal document is shared to help debug or validate logic, it's fine to process it locally, but never copy it into the repo tree, never reference its real contents (names, account numbers, amounts) in code/comments/commits/fixtures, and delete any temporary extracted copies once done.
- Before committing, check `git status`/`git diff` for anything resembling real personal data, not just secrets.

## Project Overview

Fireons is a personal finance tracker for managing net worth and accounts. FastAPI backend with PostgreSQL, Next.js frontend.

## Architecture

### Backend (Python/FastAPI)
- `app.py`: Main server with `/api` path rewriting middleware
- Authentication: `auth_api.py`, `auth_utils.py`, JWT-based (30min expiry)
- API routes: `convert_currency_api.py`, `networth_api.py`
- Package manager: uv. Python 3.10.5.
- Type checking: Pyright (strict mode disabled)

### Frontend (Next.js 15/React/TypeScript)
- App Router: `/login`, `/register`, `/networth`, `/`
- Auth: `AuthContext.tsx` with JWT token management
- Tech: Next.js 15, React 18, TanStack Table, Chart.js, Tailwind CSS, Radix UI, Ant Design

## Development Commands

A top-level `Makefile` wraps the commands below. `make install` runs all three `*-setup` targets; `make test` runs `backend-test` + `e2e`.

### Database
- `make db` — start (or create, first time) a local Postgres container matching the dev defaults: `postgres:16-alpine`, user/pass `postgres`, db `fireons_development`, port 5432. Idempotent — safe to rerun.

### Backend
- `make backend-setup` (`cd backend && uv sync`) — install deps
- `make backend` (`uv run uvicorn app:app --reload`) — dev server
- `make backend-test` (`uv run pytest`) — run tests

### Frontend
- `make frontend-setup` (`cd frontend && npm install`) — install deps
- `make frontend` (`npm run dev`) — dev server on localhost:3000
- `make frontend-build` (`npm run build`) — production build
- `make frontend-lint` (`npm run lint`) — lint
- Needs `.env.local` with `BACKEND_HOST=localhost:8000`

### E2E tests
Make targets wrap the Playwright suite in `e2e-tests/` (see `e2e-tests/package.json` for the underlying scripts):

- `make e2e-setup` — first-time setup: `npm install` + `npx playwright install chromium`
- `make e2e` — run the full suite headless (`bash e2e-tests/run-tests.sh`)
- `make e2e-headed` — same, with a visible browser window
- `make e2e-ui` — Playwright's interactive UI mode (test explorer, timeline, DOM snapshots per step)
- `make e2e-debug` — step through with the inspector
- `make e2e-report` — open the HTML report from the last run

`e2e-headed` and `e2e-ui` need a display, so they only work on a local machine, not headless CI/sandboxes.

Prerequisites: Postgres reachable per `backend/.env.test`, and the `fireons_test` database must already exist (`psql -U postgres -c "CREATE DATABASE fireons_test;"`) — `run-tests.sh` does not create it. (`make db` creates the dev database, not the test one.)

`run-tests.sh` starts the backend (`TESTING=true`, port 8020) and frontend (port 3020) itself, waits for both, runs the suite, then drops and recreates the `fireons_test` schema in teardown. Because of that teardown, don't run `npx playwright test` directly against an already-running backend from a prior `run-tests.sh` invocation — the tables will be gone and every test will fail with "relation does not exist". Always go through `run-tests.sh` (i.e. `make e2e`), or restart the backend first if running Playwright manually.

## Environment Variables

### Backend `.env` (optional)
```env
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=fireons_development
SECRET_KEY=your-secret-key-change-this-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### Frontend `.env.local` (required)
```env
BACKEND_HOST=localhost:8000
```
