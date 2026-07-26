#!/usr/bin/env bash
# Accelerate S1 book release: compile next complete book if needed, then release
# the earliest compiled-but-unreleased book (R2 + books.json + git).
# Does NOT post social — the Hermes cron agent handles announce after this exits 0.
#
# Outputs a machine-readable summary line for the agent:
#   RELEASED_BOOK=<slug>
#   or NO_RELEASE=<reason>

set -euo pipefail

PROJECT_DIR="/opt/data/hey-bible/hey-bible-podcast"
LOG_FILE="${PROJECT_DIR}/state/cron.log"
SUMMARY_FILE="${PROJECT_DIR}/state/last-release-run.json"
cd "$PROJECT_DIR"

ts() { date '+%Y-%m-%d %H:%M:%S'; }
log() { echo "[$(ts)] $*" | tee -a "$LOG_FILE"; }

# Load secrets without sourcing entire .env (tirith / non-export lines)
load_key() {
  local key="$1"
  local f
  for f in /opt/data/.hermes/.env /opt/data/.env "$HOME/.hermes/.env"; do
    if [[ -f "$f" ]]; then
      local line
      line=$(grep -E "^${key}=" "$f" | tail -1 || true)
      if [[ -n "$line" ]]; then
        export "${key}=${line#*=}"
        # strip optional quotes
        export "${key}=$(python3 -c "import os;v=os.environ.get('$key','');print(v.strip().strip(chr(34)).strip(chr(39)))")"
        return 0
      fi
    fi
  done
  return 1
}

# r2.py requires: R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET_NAME
for k in VENICE_API_KEY R2_ACCOUNT_ID R2_ACCESS_KEY_ID R2_SECRET_ACCESS_KEY R2_BUCKET_NAME; do
  load_key "$k" || true
done

log "=== S1 next-book release start ==="

# Snapshot released books before
BEFORE=$(python3 - <<'PY'
import json
from pathlib import Path
p = Path("state/progress.json")
d = json.loads(p.read_text()) if p.exists() else {}
print(",".join(d.get("released_books") or []))
PY
)

log "Released before: ${BEFORE:-none}"

log "Running compile-book.py (no-op if nothing to compile)..."
set +e
python3 scripts/compile-book.py >>"$LOG_FILE" 2>&1
COMPILE_RC=$?
set -e
log "compile-book.py exit=$COMPILE_RC"

log "Running release-book.py..."
set +e
RELEASE_OUT=$(python3 scripts/release-book.py 2>&1)
RELEASE_RC=$?
set -e
echo "$RELEASE_OUT" | tee -a "$LOG_FILE"

AFTER=$(python3 - <<'PY'
import json
from pathlib import Path
p = Path("state/progress.json")
d = json.loads(p.read_text()) if p.exists() else {}
print(",".join(d.get("released_books") or []))
PY
)

# Detect newly released slug
NEW_BOOK=$(python3 - <<PY
before = set(filter(None, "$BEFORE".split(",")))
after = set(filter(None, "$AFTER".split(",")))
new = sorted(after - before)
print(new[0] if new else "")
PY
)

TITLE=""
if [[ -n "$NEW_BOOK" ]]; then
  TITLE=$(python3 -c "print('$NEW_BOOK'.replace('-', ' ').title())")
  log "RELEASED_BOOK=$NEW_BOOK ($TITLE)"
  STATUS="released"
  REASON=""
elif echo "$RELEASE_OUT" | grep -qi "No compiled books ready"; then
  STATUS="noop"
  REASON="no_compiled_unreleased"
  log "NO_RELEASE=no_compiled_unreleased"
elif [[ "$RELEASE_RC" -ne 0 ]]; then
  STATUS="error"
  REASON="release_failed_rc_${RELEASE_RC}"
  log "NO_RELEASE=$REASON"
else
  STATUS="noop"
  REASON="already_current_or_unknown"
  log "NO_RELEASE=$REASON"
fi

python3 - <<PY
import json
from datetime import datetime, timezone
from pathlib import Path
summary = {
  "ts": datetime.now(timezone.utc).isoformat(),
  "status": "$STATUS",
  "released_book": "$NEW_BOOK" or None,
  "title": "$TITLE" or None,
  "reason": "$REASON" or None,
  "compile_rc": $COMPILE_RC,
  "release_rc": $RELEASE_RC,
  "released_books_after": [b for b in "$AFTER".split(",") if b],
}
Path("$SUMMARY_FILE").write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps(summary, indent=2))
PY

log "=== S1 next-book release end (status=$STATUS) ==="

# Exit 0 even on noop so the agent can still report; non-zero only on hard failure
if [[ "$STATUS" == "error" ]]; then
  exit 1
fi
exit 0
