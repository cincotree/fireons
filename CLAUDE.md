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

### Frontend `.env.local` (required)
```bash
BACKEND_HOST=localhost:8000
```
