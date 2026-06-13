#!/bin/bash
# Daily verse generation for Hey Bible Podcast (WEB Bible audio library)
# Target schedule: 7PM New York time (23:00 UTC during EDT)
# Runs via Hermes cron (no_agent mode)

set -e

PROJECT_DIR="/opt/data/hey-bible/hey-bible-podcast"
LOG_FILE="$PROJECT_DIR/state/cron.log"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting daily verse generation (target: 500 verses via Venice TTS)" >> "$LOG_FILE"

# Load Hermes-managed credentials (VENICE_API_KEY is required for TTS)
# Also pull any R2 vars in case later steps need them
set -a
if [ -f /opt/data/.hermes/.env ]; then
    source <(grep -E '^(VENICE_API_KEY|R2_)' /opt/data/.hermes/.env | sed 's/^/export /') || true
fi
set +a

cd "$PROJECT_DIR"

# Execute the generator (it handles batch size 500, rate limiting, file writes, progress.json, git commit + push)
if python3 scripts/generate-verses.py >> "$LOG_FILE" 2>&1; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Daily verse generation completed successfully" >> "$LOG_FILE"
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: generate-verses.py exited with failure" >> "$LOG_FILE"
    exit 1
fi

echo "" >> "$LOG_FILE"
