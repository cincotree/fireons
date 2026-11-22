#!/bin/sh
exec python3 -m uvicorn app:app --host 0.0.0.0 --port "${AWS_LWA_PORT:-8000}"
