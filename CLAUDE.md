# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Coding Standards

**IMPORTANT: Do not add code comments anywhere unless explicitly requested.** The code should be self-documenting through clear naming and structure. Comments will only be added when the user specifically asks for them.

Never use em dashes (--) in any content or code.

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
- **FastAPI Application** (`app.py`): Main server; middleware rewrites `/api`-prefixed request paths before routing.
- **Ledger data model** (`database/models.py`): a double-entry, beancount-style schema — `Account` (hierarchical colon-separated names like `Assets:Bank:HDFC:6789`, typed `Assets`/`Liabilities`/`Equity`/`Income`/`Expenses`), `Transaction`/`Posting` (balanced double-entry postings), and `Balance` (point-in-time verified balances, one row per `account_id`+`date`+`currency`, optionally linked to the `IngestedDocument` it came from).
- **Authentication**: `auth_api.py` (register/login/`/api/auth/me`), `auth_utils.py` (bcrypt hashing, JWT), 30-minute token expiry.
- **`account_api.py` / `networth_api.py`**: manual account and balance CRUD, and net worth calculation, against the ledger tables above.
- **`convert_currency_api.py`**: USD/INR conversion using `ExchangeRate` rows.
- **Statement ingestion — two independent pipelines, do not conflate them:**
  - `statements/parsers/` — the older pipeline. Regex-based, single-institution-at-a-time (currently HDFC), caller supplies the bank code, single-holding output. Exposed via `statements_api.py`.
  - `ingestion/` — the current pipeline (see below), exposed via `ingestion_api.py`. `ingestion_test_api.py` is a debug-only endpoint that runs one file through `ingest()` from an empty net worth, for interactively checking parser/extraction output without needing a real ingestion run or the database.

### Statement ingestion pipeline (`backend/ingestion/`)
Full design rationale lives in `backend/ingestion/README.md` — read it before changing extraction, staleness, or dedup logic. Summary:

- **Entry point**: `pipeline.ingest(current_nw, files) -> NetWorth`, a pure function (`ingestion/model.py` defines `NetWorth`/`Position`). It does not touch the database itself.
- **Two-tier extraction**, chosen per-document by `router.route_extract()`: a deterministic parser tier (`parsers/`, one module per document-type group — bank accounts, loans, deposits, mutual funds, demat, retirement, SGB, insurance, brokerage) tries first; each `try_parse_X(text) -> dict | None` either returns a complete, confident result or defers. Anything no parser recognizes falls back to `extract.py`, a single Anthropic tool-use schema covering 11 document types (bank/loan/brokerage/demat/MF-CAS/EPF/SGB/deposit/NPS/insurance/unrecognized) — nothing is hardcoded per-institution.
- **Deterministic account keys** are always built in code (`pipeline._account_name`) from stable identifiers (folio number, ISIN, account number), never generated as free text by the LLM — this is what makes cross-document dedup and the staleness/supersession logic reliable.
- **`invariants.py`**: label-free self-checks on any produced `NetWorth` (units × NAV ≈ value, positions sum to total, no future `as_of`, account keys match their type prefix).
- **Async flow for real uploads**: `api/ingestion_api.py` (`POST /ingestion/upload`) writes files to a per-request temp dir, rate-limits (`rate_limit.py` — 50MB/hour cumulative upload volume per user is the binding guard, cost tracks bytes not requests), creates an `IngestionRun` row, and hands off to a `BackgroundTasks` job (`background.run_ingestion`), which runs the (synchronous, possibly slow/LLM-calling) `ingest()` in a thread, then persists via `persistence.py` (`load_current_networth` / `persist_networth`, which upsert `Account`/`Balance`/`IngestedDocument` rows). Clients poll `GET /ingestion/runs/{run_id}` for status.
- **Eval suite** (`backend/tests/evals/`): 31 cases in `cases/core.yaml`, run against synthetic fixtures generated by `fixtures/generate_eval_fixtures.py` (no real financial documents are ever committed — see `generate_eval_fixtures.py`'s own docstring on which fixtures are/aren't validated against real document layouts). `harness.py` loads cases and, when a case sets `permute: true`, runs every file-ordering permutation to prove order-independence. Run just this suite with `uv run pytest tests/evals/ -v`; a single case can be targeted with `uv run pytest tests/evals/ -k <case_id> -v`.

### Frontend (Next.js 15/React/TypeScript)
- **App Router** (`frontend/src/app/`): Next.js 15 with app directory structure
  - `/login`, `/register`: auth
  - `/networth`: net worth tracking dashboard (requires authentication)
  - `/onboarding`: statement upload flow driving the `ingestion/` pipeline above
  - `/ingestion-test`: debug UI for `ingestion-test` endpoint
  - `/`: Homepage — redirects to `/networth` if authenticated, `/login` if not
- **Authentication** (`frontend/src/contexts/AuthContext.tsx`): global auth state, login/register/logout, JWT token management, automatic validation on load; protected routes redirect to login.
- **Tech Stack**: Next.js 15, React 18, TanStack Table, Chart.js/Recharts, Tailwind CSS, Radix UI, Ant Design.

### Registry data and scraping (`backend/scraping/`)
- Purpose: periodically scrape public regulator registers of financial professionals into Postgres, shown on the public `/professionals` page (nav link "Find professionals", tab title "Find a registered financial professional | Fireons"; the copy is deliberately not tied to one regulator, and the source chip shows each source's `regulator`). Sources: SEBI Registered Investment Advisers (`sebi_ria`), SEBI Registered Research Analysts (`sebi_research_analyst`, same SEBI page with `intmId=14` and `INH` numbers, about 2,300 records; both use `SebiListingSource` in `scraping/sources/sebi_ria.py`), AMFI registered mutual fund distributors (`amfi_arn`) and Fee-Only India members (`fee_only_india`).
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
- AMFI (`amfi_arn`, `scraping/sources/amfi_arn.py`): AMFI's locate-distributor API refuses unfiltered queries and caps `pageSize` at 50, so the source reads the city list embedded in the `/locate-distributor` page and walks every city (exact, case-insensitive match) page by page. `expected_total` is the running sum of each city's `meta.total`. Registration numbers are stored as `ARN-<digits>`. The API has no state field: state comes from the address when present, otherwise from a conservative pincode prefix table (`state_inferred_from_pincode` is set in `attributes`). A full run is roughly 6,500 city requests plus every page of results at 3s apart, so expect many hours; `make scrape SOURCE=amfi_arn`. The scheduled worker runs sources one after another in key order. Suspended and invalid ARN lists on AMFI are not scraped.
- NRI enrichment (`backend/enrichment/`, migration `0003`): `make enrich-nri` (`python -m enrichment nri [--limit N]`) derives a firm website from each registration email domain (generic providers such as gmail and domains shared by more than 3 professionals are skipped), then checks the homepage plus up to 4 same-site pages whose links look NRI or services related. It honours robots.txt, uses the same 3s politeness, and re-checks a site only after `NRI_RECHECK_DAYS` (30). Signals (`nri_signals`) store the matched text, page URL, signal type, location (title, meta, heading, link, body), a `high`/`medium`/`low` confidence and a `review_status` (`pending`, `confirmed`, `rejected`). Confidence: NRI or NRE/NRO wording in a title, heading, meta or link is high; a body mention is medium (high if the page has several signal types); FEMA, repatriation or overseas-audience wording alone is low or medium; a negated mention is always low. Reruns keep reviewed signals and delete stale pending ones; unreachable sites keep their old signals. Review with `python -m enrichment review-queue [--confidence high]` and `python -m enrichment review <signal_id> confirmed|rejected`. Signals are not exposed by the public API or UI until reviewed. It is not on the scraper schedule yet.
- Fee-Only India (`fee_only_india`): a curated member list, not a regulator register (the `regulator` chip reads "Fee-Only India"). One page, about 32 planners with name, firm, website and languages; no registration number, address or contact details, so the key is `FOI-<name slug>` and a renamed planner shows as a new row. Planner cards are repeater items that contain an `h6`; the independent completeness check is the count of "Website" buttons. The listed website is stored in `attributes` and NRI enrichment crawls it (`derived_from=source_listing`). Members are also SEBI RIAs, so the same person appears under `sebi_ria` too (no cross-source merging yet).
- Test fixtures are synthetic (`backend/tests/fixtures/generate_sebi_fixtures.py`). Never commit scraped pages or rows: they contain real people's names and contact details (see Handling Personal Data).

## Database Migrations and Extensions

Alembic owns the schema and the app never creates tables (see Deployment settings). Migration `0001` is the baseline; `0002` adds the registry tables and the `pg_trgm` extension.

- `make migrate` (`cd backend && uv run alembic upgrade head`) — apply migrations. Required before first run, after pulling new migrations, and as a release step in deployment.
- Changing `database/models.py` requires a migration: `uv run alembic revision --autogenerate -m "description"`, review it, commit it with the model change. `tests/test_migrations.py` fails if models and migrations drift apart.
- Never edit an applied migration; add a new one.
- `tests/conftest.py` builds the test database with `create_all` (after creating `pg_trgm`); `tests/test_migrations.py` runs the migrations on an empty database and fails if they drift from the models, which CI also checks with `alembic check`.
- UUID primary keys and several `NOT NULL` defaults (`is_enabled`, run counters, `missing_runs`) are Python-side defaults, not database defaults. Raw SQL inserts must supply them explicitly (see `e2e-tests/tests/professionals.spec.ts`).

### pg_trgm extension (required)

Name search uses a GIN trigram index (`ix_financial_professionals_name_trgm`, `gin_trgm_ops`), which needs the `pg_trgm` extension.

- Migration `0002` runs `CREATE EXTENSION IF NOT EXISTS pg_trgm` before creating the index, so `alembic upgrade head` is the only step needed. `pg_trgm` is a trusted extension on Postgres 13+, so the normal application role can create it as long as the contrib package is installed (it is in the official `postgres` Docker images and Homebrew; managed services such as RDS, Cloud SQL, Supabase and Neon provide it).
- If the deployment role cannot create extensions, run `CREATE EXTENSION pg_trgm;` once as an admin before `alembic upgrade head`.
- Any new trigram index must be created in a migration that runs after the extension exists.
- Managed Postgres services (including Neon) provide `pg_trgm`; confirm migration `0002` succeeds on the first deploy.
- The e2e teardown drops and recreates the `public` schema, which also drops the extension; `start-backend.sh` re-runs migrations, which recreates it.

## Development Commands

### One-time local setup
```bash
make setup  # deps, .env files, Postgres container, fireons_development + fireons_e2e databases, migrations
```
Databases: development uses `fireons_development`, backend tests use `fireons_test` (created and dropped by `tests/conftest.py`), e2e uses `fireons_e2e`. `make db-create` creates the first and last from `backend/.env` and `backend/.env.test`.

### Migrations and Docker
`make migrate` applies Alembic migrations (required before first run). `docker-compose.yml` runs postgres, migrate, backend and frontend locally (`make compose-up`); its database starts empty until a scrape runs; the scheduled scraper is opt-in (`make compose-up-scraper`).

### Backend Setup
```bash
cd backend
uv sync  # Install dependencies using uv
```

### Backend Development
```bash
# Run dev server (from backend/)
uv run uvicorn app:app --reload

# Run all tests (requires PostgreSQL running; creates/drops the fireons_test database each session)
uv run pytest

# Run a single test file / test / eval case
uv run pytest tests/test_ingestion_pipeline_robustness.py -v
uv run pytest tests/test_ingestion_pipeline_robustness.py::test_some_case -v
uv run pytest tests/evals/ -k <case_id> -v

# Alembic migrations (see backend/alembic/README.md)
uv run alembic upgrade head
uv run alembic revision --autogenerate -m "description"

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

### E2E Tests
```bash
cd e2e-tests
npm install
npm test                    # starts backend (:8020) + frontend (:3020) against fireons_e2e DB, runs all specs, tears down
bash run-tests.sh <spec file>   # run a single spec
npm run test:headed         # visible browser
npm run test:ui             # interactive Playwright UI
```

## Python Configuration
- **Version**: Python 3.12 (specified in `backend/.tool-versions` and `pyproject.toml`; matches the Lambda `python3.12` runtime)
- **Package Manager**: uv (fast Python package installer and resolver)
- **Type Checking**: Pyright with strict mode disabled for general type issues (see `pyrightconfig.json` and `backend/pyproject.toml`)

## Environment Variables

### Backend `.env` (`cp .env.sample .env`; `SECRET_KEY` and `DATABASE_URL` are required)
```bash
# Database
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/fireons_development

# Authentication
SECRET_KEY=your-secret-key-change-this-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Ingestion pipeline (backend/ingestion/config.py)
ANTHROPIC_API_KEY=
ANTHROPIC_MODEL=claude-sonnet-5
```

### Deployment settings (`backend/app_config.py`, `backend/database/config.py`)
Every environment is configured the same way, through env vars (locally from `.env`). `SECRET_KEY` and `DATABASE_URL` have no default and the app will not start without them. Everything else is optional and defaults to local dev behavior:
```bash
CORS_ORIGINS=http://localhost:3000,http://localhost:3020   # comma-separated
INGESTION_TEST_ENABLED=true                    # mounts the /ingestion-test debug router
DATABASE_URL=postgresql+psycopg://...          # used exactly as given by the app and Alembic (add ?sslmode=require for Neon)
DB_NULL_POOL=false                             # NullPool instead of QueuePool (Lambda)
EXCHANGE_RATE_SYNC_ENABLED=true                # in-process APScheduler job
```
The schema comes from Alembic only; the app never creates tables. Run `uv run alembic upgrade head` before starting a fresh database (`make backend` and the e2e runner do this).

When `APP_ENV` is set (e.g. `APP_ENV=production` on the Lambda), settings missing from the environment are read from the AWS Secrets Manager secret `fireons/<APP_ENV>`, a JSON object such as `{"SECRET_KEY": ..., "DATABASE_URL": ..., "ANTHROPIC_API_KEY": ...}` (`backend/secrets_source.py`). Env vars and `.env` take precedence. Locally `APP_ENV` is unset and nothing calls AWS.

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
