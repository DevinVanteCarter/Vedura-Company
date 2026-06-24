#!/bin/bash
# Section 9 Daily Report — cron installer
# Runs section9_daily_report.py at 7:00 AM every day

PYTHON=/opt/anaconda3/bin/python3
SCRIPT="$HOME/Vedura Company/section9/section9_daily_report.py"
LOG=/tmp/section9_daily.log

echo "Installing Section 9 daily report cron job..."

# Add to crontab (removes any existing section9_daily_report entry first)
(crontab -l 2>/dev/null | grep -v "section9_daily_report"; \
  echo "0 7 * * * $PYTHON \"$SCRIPT\" >> $LOG 2>&1") | crontab -

echo "Cron job installed:"
crontab -l | grep section9_daily_report
echo ""
echo "Runs at: 7:00 AM daily"
echo "Log:     $LOG"
