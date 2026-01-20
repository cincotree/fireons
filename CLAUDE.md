# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Coding Standards

**IMPORTANT: Do not add code comments anywhere unless explicitly requested.** The code should be self-documenting through clear naming and structure. Comments will only be added when the user specifically asks for them.

## Project Overview

AI Money is a personal finance expense tracker that converts credit card statements (CSV format) into beancount files and automatically categorizes expenses using AI agents. The system uses a LangGraph-based agent workflow with websocket communication between frontend and backend.

## Architecture

### Backend (Python/FastAPI)
- **FastAPI Application** (`app.py`): Main server with middleware to rewrite `/api` paths
- **Authentication System**:
  - `auth_api.py`: User registration, login, and JWT authentication endpoints
  - `auth_utils.py`: Password hashing (bcrypt) and JWT token generation/validation
  - `database/models.py`: User model with email, username, password, profile fields
  - JWT-based authentication with 30-minute token expiration
  - Endpoints: `/api/auth/register`, `/api/auth/login`, `/api/auth/me`
- **Agent Workflow System** (`agents/`):
  - `workflow.py`: LangGraph StateGraph that orchestrates the categorization flow
  - `orchestrator.py`: OrchestratorAgent manages workflow state transitions and user feedback collection
  - `categorizer.py`: CategorizationAgent uses Claude Haiku to batch-categorize transactions
  - `base.py`: Defines AgentState dataclass and Step enum for workflow state management
  - Workflow steps: ORCHESTRATE → CATEGORIZE → GET_USER_FEEDBACK → ORCHESTRATE (loop) → END
- **Accounting Module** (`accounting/`):
  - `cc.py`: Converts Fidelity and Amex CSV statements to beancount Transaction objects
  - `transactions.py`: Updates beancount files with categorized transactions, manages transaction metadata
  - `store.py`: Loads/persists beancount files
  - `catagory.py`: Defines expense categories and batch size
  - `accounts.py`: Creates beancount transaction objects
- **API Routes**:
  - `/ws/workflow`: WebSocket endpoint for agent workflow communication (beancount_filepath query param)
  - `transactions_api.py`: Transaction CRUD operations
  - `convert_currency_api.py`: Currency conversion (USD to INR)
  - `networth_api.py`: Net worth tracking and calculations
  - `uiflow.py`: WebSocket handler that invokes the LangGraph workflow

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
- **Components** (`frontend/src/components/`):
  - `TransactionFlowClient.tsx`: WebSocket client managing workflow state and user feedback
  - `TransactionTable.tsx`: Displays transactions with categorization status
  - `TransactionList.tsx`: List view of transactions
- **Tech Stack**: Next.js 15, React 18, TanStack Table, Chart.js, Tailwind CSS, Radix UI, Ant Design

### Key Workflow
1. User uploads CC statement CSV → converted to beancount format with `Expenses:Uncategorized`
2. Backend workflow starts via WebSocket with beancount file path
3. CategorizationAgent processes uncategorized transactions in batches using Claude Haiku
4. Transactions AI can't categorize are sent to user for manual feedback via WebSocket
5. User provides feedback → transactions updated → workflow continues until all categorized
6. Beancount file is updated with categories and vendor metadata

## Development Commands

### Backend Setup
```bash
cd backend
uv sync  # Install dependencies using uv
```

### Backend Development
```bash
# Run dev server (from backend/)
ANTHROPIC_API_KEY=<your_key> uv run uvicorn app:app --reload

# Or with .env file
uv run uvicorn app:app --reload

# Build Docker image
docker build -t fireons/backend .

# Run Docker container
docker run -p 8000:8000 -e ANTHROPIC_API_KEY=your_key fireons/backend
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
POSTGRES_DB=ai_money_development

# Authentication
SECRET_KEY=your-secret-key-change-this-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# API Keys
ANTHROPIC_API_KEY=your-anthropic-api-key  # Required for AI categorization
```

### Frontend `.env.local` (required)
```bash
NEXT_PUBLIC_BACKEND_HOST=localhost:8000
```

## Beancount Integration
- Transaction format uses beancount double-entry accounting
- Each transaction has a unique link (ID) used for tracking and updates
- Supported CC formats: Fidelity (YYYY-MM-DD dates, DEBIT/CREDIT) and Amex (MM/DD/YYYY dates)
- Uncategorized expenses start in `Expenses:Uncategorized` account
- Categories defined in `backend/accounting/catagory.py`
- Vendor information stored in transaction metadata
- Sample statements available in `backend/statements/`

## AWS Deployment
Both frontend and backend can be deployed to AWS ECR. Build with `--platform=linux/amd64`, tag with git commit hash, and push to ECR region us-west-2 (see README for full commands).

## Visualization
Use [Paisa](https://paisa.fyi/) dashboard to visualize categorized transactions from the beancount file.
