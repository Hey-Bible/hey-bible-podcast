#!/bin/bash
# Daily cron script for WEB Bible Audio generation
# Runs at 7PM EST

set -e

PROJECT_DIR="/root/.openclaw/workspace-claudius/web-bible-audio"
LOG_FILE="$PROJECT_DIR/state/cron.log"

# Log start
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting daily verse generation" >> "$LOG_FILE"

cd "$PROJECT_DIR"

# Run the generator and capture output
python3 scripts/generate-verses.py >> "$LOG_FILE" 2>&1

# Log completion
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Completed" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"
