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

## Development Commands

### Backend Setup
```bash
cd backend
uv sync  # Install dependencies using uv
```

### Backend Development
```bash
# Run dev server (from backend/)
uv run uvicorn app:app --reload

# Run all tests (requires PostgreSQL running; creates/drops a *_test database each session)
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
npm test                    # starts backend (:8020) + frontend (:3020) against fireons_test DB, runs all specs, tears down
bash run-tests.sh <spec file>   # run a single spec
npm run test:headed         # visible browser
npm run test:ui             # interactive Playwright UI
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

# Ingestion pipeline (backend/ingestion/config.py)
ANTHROPIC_API_KEY=
ANTHROPIC_MODEL=claude-sonnet-5
```

### Frontend `.env.local` (required)
```bash
BACKEND_HOST=localhost:8000
```
