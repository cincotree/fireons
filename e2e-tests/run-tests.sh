#!/bin/bash

export TESTING=true

cleanup() {
  echo "Cleaning up test servers..."
  lsof -ti:8020 | xargs kill -9 2>/dev/null || true
  lsof -ti:3020 | xargs kill -9 2>/dev/null || true
  echo "Test servers stopped"
}

trap cleanup EXIT

echo "Starting backend server..."
./start-backend.sh > backend.log 2>&1 &
BACKEND_PID=$!

echo "Waiting for backend to be ready..."
while ! curl -s http://localhost:8020 > /dev/null; do
  if ! kill -0 $BACKEND_PID 2>/dev/null; then
    echo "Backend failed to start. Last lines of backend.log:"
    tail -5 backend.log
    exit 1
  fi
  sleep 1
done
echo "Backend is ready"

echo "Starting frontend server..."
./start-frontend.sh > frontend.log 2>&1 &
FRONTEND_PID=$!

echo "Waiting for frontend to be ready..."
while ! curl -s http://localhost:3020 > /dev/null; do
  if ! kill -0 $FRONTEND_PID 2>/dev/null; then
    echo "Frontend failed to start. Last lines of frontend.log:"
    tail -5 frontend.log
    exit 1
  fi
  sleep 1
done
echo "Frontend is ready"

echo "Running tests..."
npx playwright test "$@"
