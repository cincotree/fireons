# AGENTS.md

Guidance for AI coding agents working on this repository.

## Coding Standards

- **Do not add code comments anywhere unless explicitly requested.**
- Code should be self-documenting through clear naming and structure.
- Never use em dashes (--) in any content or code.

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
