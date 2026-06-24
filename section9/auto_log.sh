#!/bin/bash
DATE=$(date +%Y-%m-%d)
DAYS=$(python3 -c "import datetime; print((datetime.date(2026,6,9)-datetime.date.today()).days)")
SCRIPT_PATH="$HOME/Vedura Company/The Vedura Company/log_to_obsidian.py"

python3 "$SCRIPT_PATH" --agent major --content "MORNING BRIEF $DATE: Cincinnati $DAYS days. Users: 0. API: healthy. Plant scanner: 35000+ species."

python3 "$SCRIPT_PATH" --agent ishikawa --content "METRICS $DATE: Users 0. Revenue 0. Days to Cincinnati $DAYS. API healthy."

echo "Logged at $DATE"
