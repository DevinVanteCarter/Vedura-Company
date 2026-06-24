#!/bin/bash

# Start the Zen Vision local backend and local static web server.
# Usage: bash run_zenvision_local.sh

ROOT="$HOME/Vedura Company"
API_DIR="$ROOT/zenvision_api"
WEB_DIR="$ROOT"
LOG_DIR="/tmp"

cd "$ROOT" || exit 1

# Stop any previous instances first
pkill -f "uvicorn zenvision_api.main:app --host 127.0.0.1 --port 8000" 2>/dev/null
pkill -f "python3 -m http.server 8001" 2>/dev/null
sleep 1

echo "Starting Zen Vision backend..."
cd "$API_DIR" || exit 1
nohup python3 -m uvicorn main:app --host 127.0.0.1 --port 8000 > "$LOG_DIR/zenvision_api.log" 2>&1 &
API_PID=$!

echo "Starting local web server..."
cd "$WEB_DIR" || exit 1
nohup python3 -m http.server 8001 > "$LOG_DIR/zenvision_site.log" 2>&1 &
WEB_PID=$!

sleep 2

echo ""
echo "Zen Vision backend PID: $API_PID"
echo "Static site server PID: $WEB_PID"
echo "Open this in your browser: http://127.0.0.1:8001/app.html"
echo "Backend health: http://127.0.0.1:8000/health"
echo "Logs: $LOG_DIR/zenvision_api.log and $LOG_DIR/zenvision_site.log"

echo "If you need to stop both, run: bash stop_zenvision_local.sh"
