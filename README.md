## Fireons

A personal finance tracker for managing net worth and accounts.

### Features
- **User authentication** - Secure login and registration
- **Net worth tracking** - Track your assets and liabilities over time
- **Multi-currency support** - Handles accounts in different currencies

### Setup

#### PostgreSQL Database
The application requires PostgreSQL to be installed and running. Set up the database:

1. Install PostgreSQL (if not already installed):
   - macOS: `brew install postgresql`
   - Ubuntu: `sudo apt-get install postgresql`

2. Create the postgres role (if it doesn't exist):
```bash
psql postgres -c "CREATE ROLE postgres WITH LOGIN PASSWORD 'postgres' SUPERUSER CREATEDB CREATEROLE;"
```

3. The application will automatically create the database when it runs.

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
- Edit `.env.local` and set `BACKEND_HOST` (defaults to `localhost:8000` for local development)

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
docker run -p 3000:3000 -e BACKEND_HOST=localhost:8000 fireons/frontend
```
