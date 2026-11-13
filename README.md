## Fireons

A personal finance tracker for managing net worth and accounts.

### Features
- **User authentication** - Secure login and registration
- **Net worth tracking** - Track your assets and liabilities over time
- **Multi-currency support** - Handles accounts in different currencies

### Setup

#### Quick start
With [uv](https://docs.astral.sh/uv/), Node.js 22 and Docker installed, run from the repository root:

```bash
make setup
```

This installs backend, frontend and e2e dependencies, creates `backend/.env` and `frontend/.env.local` from the samples if missing, starts a Postgres container on port 5432, creates the `fireons_development` and `fireons_e2e` databases, and applies migrations. It is safe to rerun. Backend tests create and drop their own `fireons_test` database.

The sections below describe the same steps by hand, for example to use a Postgres you installed yourself.

#### PostgreSQL Database
The application requires PostgreSQL to be installed and running. Set up the database:

1. Install PostgreSQL (if not already installed):
   - macOS: `brew install postgresql`
   - Ubuntu: `sudo apt-get install postgresql`

2. Create the postgres role (if it doesn't exist):
```bash
psql postgres -c "CREATE ROLE postgres WITH LOGIN PASSWORD 'postgres' SUPERUSER CREATEDB CREATEROLE;"
```

3. Create the databases and apply migrations (after the backend setup below):
```bash
make db-create
make migrate
```

#### Backend
- Install [uv](https://docs.astral.sh/uv/) package manager
- cd backend
- uv sync
- cp .env.sample .env
- The defaults work out of the box for local development. `SECRET_KEY` signs auth JWTs, so set a real random value before deploying anywhere other than your machine.

#### Frontend
This is a [Next.js](https://nextjs.org) app bootstrapped with [`create-next-app`](https://nextjs.org/docs/app/api-reference/cli/create-next-app).

Install
- Node.js (version 22.x or later recommended)
- npm (comes with Node.js)
- cd frontend
- npm install
- cp .env.local.sample .env.local
- Edit `.env.local` and set `NEXT_PUBLIC_API_BASE_URL` (for example `http://localhost:8000`)

### Run

**Backend**

1. Install dependencies:
```bash
cd backend
uv sync
```

2. Run the server:
```bash
uv run uvicorn app:app --reload
```

Verify it started by visiting `http://localhost:8000/health` (returns `{"status": "ok"}`) or `http://localhost:8000/docs` for the interactive API docs.

Build and run using Docker:
```bash
docker build -t fireons/backend .
docker run -p 8000:8000 fireons/backend
```

**Frontend**

```bash
cd frontend
npm run dev
```

Visit localhost:3000

Build and run using Docker:
```bash
docker build -t fireons/frontend .
docker run -p 3000:3000 fireons/frontend
```

### Production registration

Registration is invite-only in production. See [docs/invite-only-registration.md](docs/invite-only-registration.md) for how to create and manage invites, and [infra/README.md](infra/README.md) for deploying the AWS infrastructure.

### Professionals directory data

The `/professionals` directory is filled from your machine, not from AWS. The only job that runs in production is `exchange_rate_sync`. Details are in [docs/professionals-data.md](docs/professionals-data.md).

Keys go in `backend/.env`: `GOOGLE_API_KEY` for the Google Places export and `TAVILY_API_KEY` for enrichment. Migrations are applied by the deploy (`scripts/deploy-api.sh`), so production is ready after the first release. Only if you run these before that release, apply them yourself first (`make migrate` with `DATABASE_URL` set). Run these from one machine only, because the usage counters and the export CSV live in `backend/exports/`.

```bash
make daily     # export and import Google places, enrich them via Tavily, check sites for NRI signals
make weekly    # scrape SEBI RIAs, SEBI research analysts, Fee-Only India and FPSB CFPs
```

To load production, set the database for that command only (never `export` it in a shell that also runs the e2e tests):

```bash
DATABASE_URL='postgresql+psycopg://...?sslmode=require' make daily
```

`make daily` stops at the first failing step. `make weekly` continues past a failing source and exits non-zero if any failed. Scrape registers weekly rather than daily, because a register row is delisted after two consecutive missed runs.
