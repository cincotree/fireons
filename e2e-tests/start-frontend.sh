#!/bin/bash
cd ../frontend
export NEXT_PUBLIC_API_BASE_URL=http://localhost:8020
npm run build
cd out
exec python3 -m http.server 3020
