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

### Backend
- `cd backend && uv sync` — install deps
- `uv run uvicorn app:app --reload` — dev server
- `uv run pytest tests/ -v` — run tests

### Frontend
- `cd frontend && npm install` — install deps
- `npm run dev` — dev server on localhost:3000
- `npm run build` — production build
- `npm run lint` — lint
- Needs `.env.local` with `BACKEND_HOST=localhost:8000`

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
