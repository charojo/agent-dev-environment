#!/bin/bash
# Kill existing backend if it's there
pkill -f "uvicorn src.server.main:app" || echo "No backend running."
sleep 2
# Start fresh
nohup uv run uvicorn src.server.main:app --reload --port 8000 > logs/backend.log 2>&1 &
echo "Backend restarted."
