#!/bin/bash

# Stop the Zen Vision local backend and local static web server.
# Usage: bash stop_zenvision_local.sh

pkill -f "uvicorn zenvision_api.main:app --host 127.0.0.1 --port 8000" 2>/dev/null && echo "Stopped Zen Vision backend"
pkill -f "python3 -m http.server 8001" 2>/dev/null && echo "Stopped local web server"

echo "Done."
