#!/bin/bash
# First Sunday of the month book publish for Hey Bible Podcast
# Runs compile-book.py (stitches full book + uploads preview) then release-book.py (final R2 + books.json + deploy)
# Only acts on the first Sunday of the month; otherwise exits cleanly.
# Target: 8AM New York time on first Sunday (12:00 UTC during EDT)

set -e

PROJECT_DIR="/opt/data/hey-bible/hey-bible-podcast"
LOG_FILE="$PROJECT_DIR/state/cron.log"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting first-Sunday book publish check" >> "$LOG_FILE"

# Date check: first Sunday of the month?
# weekday: 1=Mon ... 7=Sun (Linux %u); day 1-7 on a Sunday means first Sunday
weekday=$(date +%u)
day=$(date +%d)

if [ "$weekday" -ne 7 ] || [ "$day" -gt 7 ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Not the first Sunday of the month (weekday=$weekday, day=$day) — skipping publish" >> "$LOG_FILE"
    exit 0
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] First Sunday of the month — proceeding with compile + release (review step skipped per policy)" >> "$LOG_FILE"

# Load Hermes-managed credentials (VENICE for title TTS + R2 for uploads)
set -a
if [ -f /opt/data/.hermes/.env ]; then
    source <(grep -E '^(VENICE_API_KEY|R2_)' /opt/data/.hermes/.env | sed 's/^/export /') || true
fi
set +a

cd "$PROJECT_DIR"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Running compile-book.py (generates full book from verses + chapter titles, uploads preview)" >> "$LOG_FILE"
if python3 scripts/compile-book.py >> "$LOG_FILE" 2>&1; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] compile-book.py completed" >> "$LOG_FILE"
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: compile-book.py failed" >> "$LOG_FILE"
    exit 1
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Running release-book.py (final upload with streaming headers, updates books.json, commits, triggers deploy)" >> "$LOG_FILE"
if python3 scripts/release-book.py >> "$LOG_FILE" 2>&1; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] release-book.py completed — book published" >> "$LOG_FILE"
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: release-book.py failed" >> "$LOG_FILE"
    exit 1
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] First Sunday book publish completed successfully" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"