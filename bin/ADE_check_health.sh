#!/bin/bash
# agent_env/bin/ADE_check_health.sh
# Verifies that the development stack is running.
# Intended to be run from project root or via relative path.

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# Robustly find project root if needed, though this script checks ports so it's less critical.
# However, standardizing is good.

echo "🏥 Checking System Health..."

# Check Backend (FastAPI on 8000)
if curl -s http://127.0.0.1:8000/docs > /dev/null; then
    echo -e "${GREEN}✓ Backend is UP (Port 8000)${NC}"
else
    echo -e "${RED}✗ Backend is DOWN (Port 8000)${NC}"
    echo "  Please run './bin/start_dev.sh' or 'uv run fastapi dev src/server/main.py'"
    exit 1
fi

# Check Frontend (Vite on 5173)
if curl -s http://127.0.0.1:5173 > /dev/null; then
    echo -e "${GREEN}✓ Frontend is UP (Port 5173)${NC}"
else
    echo -e "${RED}✗ Frontend is DOWN (Port 5173)${NC}"
    echo "  Please run 'npm run dev' in 'src/web'"
    exit 1
fi

echo -e "${GREEN}✓ System is healthy and ready for CSS validation.${NC}"
exit 0
