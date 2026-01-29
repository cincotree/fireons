# E2E Tests

Browser-based functional tests using Playwright for authentication and net worth features.

## Quick Start

```bash
npm install
npm test
```

Tests automatically start servers, run all tests, and clean up.

## Test Modes

```bash
npm test              # Run all tests (headless)
npm run test:headed   # Run with visible browser
npm run test:ui       # Interactive Playwright UI
npm run test:debug    # Debug mode with step-through
npm run report        # View HTML test report
```

## Database Setup

Tests use a separate `fireons_test` database for complete isolation:

```bash
createdb fireons_test
```

Test data is automatically cleaned up after each run.

## Configuration

- Frontend: `http://localhost:3020`
- Backend: `http://localhost:8020`
- Test Database: `fireons_test`

Override with environment variables:
```bash
BASE_URL=http://localhost:3020 BACKEND_URL=http://localhost:8020 npm test
```

## Test Coverage

**Authentication (9 tests)**
- User registration and login flows
- Form validation
- Protected routes
- Navigation

**Net Worth (5 tests)**
- Account creation (assets/liabilities)
- Balance management
- Multi-currency support
- Data isolation
