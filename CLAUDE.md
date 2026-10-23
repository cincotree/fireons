# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Coding Standards

**IMPORTANT: Do not add code comments anywhere unless explicitly requested.** The code should be self-documenting through clear naming and structure. Comments will only be added when the user specifically asks for them.

## Testing Requirements

**Every new feature must ship with tests, not just the happy path.** Before considering a change done:

- **Backend**: add unit tests for new business logic (`backend/tests/`) and, for new API endpoints, request-level tests that exercise auth, validation errors, and success responses. Run `uv run pytest` and confirm your new tests pass — don't just eyeball the code.
- **Frontend user flows**: add a Playwright e2e spec (`e2e-tests/tests/`) that drives the actual UI for the new flow, including at least one realistic failure path (bad input, wrong credentials, rejected upload, etc.), not only the happy path. Run it (`bash e2e-tests/run-tests.sh <spec file>`) and confirm it passes against the real app.
- Prefer extending an existing test file's patterns over inventing a new style. If you find pre-existing broken/stale tests while working nearby, flag them rather than silently leaving them broken or trying to fix unrelated debt in the same change.
- Manually verify UI changes in a running browser before reporting a frontend change complete — a passing test suite is not a substitute for seeing the feature work.

## Handling Personal Data

**Never commit real personal, financial, or otherwise sensitive documents or data to this repository, even temporarily.** This includes real bank statements, real account numbers, real names/addresses, screenshots containing real personal data, or any file downloaded from a live personal account.

- Test fixtures must always be synthetic. When a feature needs a sample document (e.g. a bank statement PDF), generate one programmatically with fake data — don't copy in a real one, even redacted.
- If a user shares a real personal document to help validate or debug logic (e.g. "here's my real statement, fix the parser"), it's fine to read and process it locally to inform the fix, but never copy it into the repository working tree, never reference its real contents (names, account numbers, amounts) in code, comments, commit messages, or fixtures, and delete any temporary extracted copies (e.g. in scratch/tmp dirs) once done.
- Before committing, check `git status`/`git diff` for anything that looks like real personal data, not just secrets — a filename or fixture that looks synthetic is worth a second look if it was derived from something real.

## Project Overview

Fireons is a personal finance tracker for managing net worth and accounts. The system uses a FastAPI backend with PostgreSQL and a Next.js frontend.

## Architecture

### Backend (Python/FastAPI)
- **FastAPI Application** (`app.py`): Main server with middleware to rewrite `/api` paths
- **Authentication System**:
  - `auth_api.py`: User registration, login, and JWT authentication endpoints
  - `auth_utils.py`: Password hashing (bcrypt) and JWT token generation/validation
  - `database/models.py`: User model with email, username, password, profile fields
  - JWT-based authentication with 30-minute token expiration
  - Endpoints: `/api/auth/register`, `/api/auth/login`, `/api/auth/me`
- **API Routes**:
  - `convert_currency_api.py`: Currency conversion (USD to INR)
  - `networth_api.py`: Net worth tracking and calculations

### Frontend (Next.js 15/React/TypeScript)
- **App Router** (`frontend/src/app/`): Next.js 15 with app directory structure
  - `/login`: User login page
  - `/register`: User registration page with email, username, password, optional fields
  - `/networth`: Net worth tracking dashboard (requires authentication)
  - `/`: Homepage - redirects to `/networth` if authenticated, `/login` if not
- **Authentication** (`frontend/src/contexts/`):
  - `AuthContext.tsx`: Global auth state, login/register/logout functions, JWT token management
  - Automatic token validation on page load
  - Protected routes redirect to login if not authenticated
- **Tech Stack**: Next.js 15, React 18, TanStack Table, Chart.js, Tailwind CSS, Radix UI, Ant Design

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
- Public API: `GET /registrations`, `/registrations/{id}`, `/registrations/{id}/history`, `/registrations/sources`, `/registrations/facets`. No auth (SEBI publishes this data), per-IP rate limit, `page_size` capped at 100, no bulk export.
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

### Migrations and Docker
`make migrate` applies Alembic migrations (required before first run). `docker-compose.yml` runs postgres, migrate, backend and frontend (dev server, `frontend/Dockerfile.dev`) locally (`make compose-up`); its database starts empty until a scrape runs; the scheduled scraper is opt-in (`make compose-up-scraper`).

### Backend Setup
```bash
cd backend
uv sync  # Install dependencies using uv
```

### Backend Development
```bash
# Run dev server (from backend/)
uv run uvicorn app:app --reload

# Build Docker image
docker build -t fireons/backend .

# Run Docker container
docker run -p 8000:8000 fireons/backend
```

### Frontend Setup
```bash
cd frontend
npm install

# Create .env.local from sample
cp .env.local.sample .env.local
# Edit .env.local and set BACKEND_HOST if needed (defaults to localhost:8000)
```

### Frontend Development
```bash
# Run dev server (from frontend/)
npm run dev  # Starts on localhost:3000

# Build production
npm run build

# Start production server
npm start

# Lint
npm run lint

# Build Docker image
docker build -t fireons/frontend .

# Run Docker container
docker run -p 3000:3000 -e BACKEND_HOST=localhost:8000 fireons/frontend
```

## Python Configuration
- **Version**: Python 3.10.5 (specified in `backend/.tool-versions` and `pyproject.toml`)
- **Package Manager**: uv (fast Python package installer and resolver)
- **Type Checking**: Pyright with strict mode disabled for general type issues (see `pyrightconfig.json` and `backend/pyproject.toml`)

## Environment Variables

### Backend `.env` (optional, has defaults)
```bash
# Database
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=fireons_development

# Authentication
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
```bash
BACKEND_HOST=localhost:8000
```
