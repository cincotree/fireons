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

### Registry data and scraping (`backend/scraping/`)
- Purpose: periodically scrape public regulator registers of financial professionals into Postgres, shown on the public `/professionals` page (nav link "Find professionals", tab title "Find a registered financial professional | Fireons"; the copy is deliberately not tied to one regulator, and the source chip shows each source's `regulator`). First source: SEBI Registered Investment Advisers (`sebi_ria`).
- Tables: `data_sources` (one per register), `financial_professionals` (who someone is, across sources), `professional_registrations` (one row per register entry, `UNIQUE (source_id, registration_number)`, `profession_type` says what kind of professional), `registration_versions` (append-only history, written on first sight and on every content change), `scrape_runs` (one row per execution).
- Add a source: implement a `Source` (a `SourceDefinition` plus `fetch_pages(client)` yielding normalized `ScrapedRegistration` records) in `scraping/sources/`, register it in `scraping/sources/__init__.py`. No schema change is needed.
- Idempotent by `content_hash`: a rerun with unchanged data writes no versions and only bumps `last_seen_at`.
- Delisting: a registration missing from a run is only counted as missing when that run `succeeded` (all pages fetched, zero parse errors, record count within 98% of the register's own total). After 2 consecutive missed succeeded runs it becomes `delisted`. Partial or failed runs never change status.
- A per-source Postgres advisory lock prevents overlapping runs.
- Politeness: minimum 3s between requests (`SCRAPE_MIN_INTERVAL_SECONDS`), identifying User-Agent, retry with backoff honouring `Retry-After`. Do not lower the interval or remove the retry cap.
- Schedule: `SCRAPE_SCHEDULE_CRON`, default `0 3 * * sun` in `Asia/Kolkata`. APScheduler numbers weekdays from Monday = 0, so use weekday names, not digits.
- Run it: `make scrape` (once), `make scraper-worker` (scheduler in the foreground), or `docker compose --profile scraper up` (worker in Docker). A deployed worker is not set up yet.
- Public API: `GET /registrations`, `/registrations/{id}`, `/registrations/{id}/history`, `/registrations/sources`, `/registrations/facets`. No auth (SEBI publishes this data), per-IP rate limit (`PUBLIC_READ_LIMIT_PER_MINUTE`, default 240; the e2e backend raises it because one test run is one IP), `page_size` capped at 100, no bulk export.
- Search: `q` is one fuzzy box. It is split into words (max 8); every word must match at least one of name, city, state, source name (substring, or `pg_trgm` word similarity >= 0.4 for words of 4+ letters) or part of the registration number. Results rank by closeness. Exact filters `source`, `state`, `city`, `status`, `profession_type` combine with it. `/registrations/facets` returns the states and cities (scoped by `source`/`state`) for the dropdowns. The UI is one search box plus a Filters button that reveals Source, State and City dropdowns (there is no status filter in the UI; the API still accepts `status`).
- Test fixtures are synthetic (`backend/tests/fixtures/generate_sebi_fixtures.py`). Never commit scraped pages or rows: they contain real people's names and contact details (see Handling Personal Data).

## Database Migrations and Extensions

The schema is managed by Alembic (`backend/alembic/`). The app no longer creates tables at startup; `verify_database()` in `database/session.py` refuses to start if migrations have not been applied.

- `make migrate` (`cd backend && uv run alembic upgrade head`) — apply migrations. Required before first run, after pulling new migrations, and as a release step in deployment.
- Changing `database/models.py` requires a migration: `uv run alembic revision --autogenerate -m "description"`, review it, commit it with the model change. `tests/test_migrations.py` fails if models and migrations drift apart.
- Never edit an applied migration; add a new one.
- A database created before Alembic was adopted (tables exist, no `alembic_version`) must be stamped once: `cd backend && uv run alembic stamp 0001 && uv run alembic upgrade head`.
- Tests build their database with `alembic upgrade head` once per session and truncate tables between tests.
- UUID primary keys and several `NOT NULL` defaults (`is_enabled`, run counters, `missing_runs`) are Python-side defaults, not database defaults. Raw SQL inserts must supply them explicitly (see `e2e-tests/tests/professionals.spec.ts`).

### pg_trgm extension (required)

Name search uses a GIN trigram index (`ix_financial_professionals_name_trgm`, `gin_trgm_ops`), which needs the `pg_trgm` extension.

- Migration `0002` runs `CREATE EXTENSION IF NOT EXISTS pg_trgm` before creating the index, so `alembic upgrade head` is the only step needed. `pg_trgm` is a trusted extension on Postgres 13+, so the normal application role can create it as long as the contrib package is installed (it is in the official `postgres` Docker images and Homebrew; managed services such as RDS, Cloud SQL, Supabase and Neon provide it).
- If the deployment role cannot create extensions, run `CREATE EXTENSION pg_trgm;` once as an admin before `alembic upgrade head`.
- Any new trigram index must be created in a migration that runs after the extension exists.
- On Supabase extensions live in the `extensions` schema; confirm the index creation succeeds there when deploying.
- The e2e teardown drops and recreates the `public` schema, which also drops the extension; `start-backend.sh` re-runs migrations, which recreates it.

## Development Commands

A top-level `Makefile` wraps the commands below. `make install` runs all three `*-setup` targets; `make test` runs `backend-test` + `e2e`.

### Database
- `make db` — start (or create, first time) a local Postgres container matching the dev defaults: `postgres:16-alpine`, user/pass `postgres`, db `fireons_development`, port 5432. Idempotent — safe to rerun.

### Docker (local)
`docker-compose.yml` runs postgres (published on 5433 to avoid clashing with a local Postgres), a one-shot `migrate` service, backend (8000) and frontend (3000). The frontend runs `next dev` (`frontend/Dockerfile.dev`) because `npm run build` currently fails on existing lint/type errors. The compose database starts empty; run a scrape to populate it. The scheduled scraper is opt-in: `make compose-up-scraper` (`--profile scraper`). `make compose-up` / `make compose-down` wrap it.

### Backend
- `make migrate` — apply database migrations (see Database Migrations and Extensions)
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

### Scraper settings (optional, backend `.env`)
```env
SCRAPE_MIN_INTERVAL_SECONDS=3.0
SCRAPE_MAX_RETRIES=4
SCRAPE_SCHEDULE_CRON=0 3 * * sun
SCRAPE_SCHEDULE_TIMEZONE=Asia/Kolkata
```

### Frontend `.env.local` (required)
```env
BACKEND_HOST=localhost:8000
```
