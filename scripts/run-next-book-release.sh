#!/usr/bin/env bash
# Accelerate S1 book release: compile next complete book(s) if needed, then release
# up to RELEASE_COUNT compiled-but-unreleased books (R2 + books.json + git).
# Does NOT post social — the Hermes cron agent handles announce after this exits 0.
#
# Env:
#   RELEASE_COUNT  max books this run (default 2)
#
# Outputs:
#   RELEASED_BOOKS=slug1,slug2
#   RELEASED_BOOK=<first>   (compat)
#   or NO_RELEASE=<reason>

set -euo pipefail

PROJECT_DIR="/opt/data/hey-bible/hey-bible-podcast"
LOG_FILE="${PROJECT_DIR}/state/cron.log"
SUMMARY_FILE="${PROJECT_DIR}/state/last-release-run.json"
RELEASE_COUNT="${RELEASE_COUNT:-2}"
cd "$PROJECT_DIR"

ts() { date '+%Y-%m-%d %H:%M:%S'; }
log() { echo "[$(ts)] $*" | tee -a "$LOG_FILE"; }

load_key() {
  local key="$1"
  local f
  for f in /opt/data/.hermes/.env /opt/data/.env "$HOME/.hermes/.env"; do
    if [[ -f "$f" ]]; then
      local line
      line=$(grep -E "^${key}=" "$f" | tail -1 || true)
      if [[ -n "$line" ]]; then
        export "${key}=${line#*=}"
        export "${key}=$(python3 -c "import os;v=os.environ.get('$key','');print(v.strip().strip(chr(34)).strip(chr(39)))")"
        return 0
      fi
    fi
  done
  return 1
}

for k in VENICE_API_KEY R2_ACCOUNT_ID R2_ACCESS_KEY_ID R2_SECRET_ACCESS_KEY R2_BUCKET_NAME; do
  load_key "$k" || true
done

log "=== S1 next-book release start (RELEASE_COUNT=$RELEASE_COUNT) ==="

BEFORE=$(python3 - <<'PY'
import json
from pathlib import Path
p = Path("state/progress.json")
d = json.loads(p.read_text()) if p.exists() else {}
print(",".join(d.get("released_books") or []))
PY
)

log "Released before: ${BEFORE:-none}"

log "Running compile-book.py (may compile multiple ready books)..."
set +e
python3 scripts/compile-book.py >>"$LOG_FILE" 2>&1
COMPILE_RC=$?
set -e
log "compile-book.py exit=$COMPILE_RC"

# Optional second compile pass so two books can be ready in one tick
set +e
python3 scripts/compile-book.py >>"$LOG_FILE" 2>&1
COMPILE_RC2=$?
set -e
log "compile-book.py second pass exit=$COMPILE_RC2"

RELEASED_LIST=()
RELEASE_RC=0
for i in $(seq 1 "$RELEASE_COUNT"); do
  log "Running release-book.py (pass $i/$RELEASE_COUNT)..."
  set +e
  RELEASE_OUT=$(python3 scripts/release-book.py 2>&1)
  RC=$?
  set -e
  echo "$RELEASE_OUT" | tee -a "$LOG_FILE"
  if [[ $RC -ne 0 ]]; then
    RELEASE_RC=$RC
    log "release-book.py failed rc=$RC on pass $i"
    break
  fi
  if echo "$RELEASE_OUT" | grep -qi "No compiled books ready"; then
    log "No more compiled books ready after pass $i"
    break
  fi
  if echo "$RELEASE_OUT" | grep -qi "SUCCESSFULLY RELEASED"; then
    # detect delta after each release
    AFTER_NOW=$(python3 - <<'PY'
import json
from pathlib import Path
p = Path("state/progress.json")
d = json.loads(p.read_text()) if p.exists() else {}
print(",".join(d.get("released_books") or []))
PY
    )
    NEW_ONE=$(python3 - <<PY
before = set(filter(None, "$BEFORE".split(",")))
# also exclude already captured this run
already = set(filter(None, "${RELEASED_LIST[*]}".replace(" ", ",").split(","))) if False else set()
PY
    )
    # simpler: compare AFTER_NOW to BEFORE+RELEASED_LIST
    NEW_ONE=$(BEFORE="$BEFORE" AFTER_NOW="$AFTER_NOW" RELEASED="${RELEASED_LIST[*]}" python3 - <<'PY'
import os
before = set(filter(None, os.environ.get("BEFORE","").split(",")))
after = set(filter(None, os.environ.get("AFTER_NOW","").split(",")))
already = set(filter(None, os.environ.get("RELEASED","").split()))
new = sorted(after - before - already)
print(new[0] if new else "")
PY
    )
    if [[ -n "$NEW_ONE" ]]; then
      RELEASED_LIST+=("$NEW_ONE")
      log "RELEASED_BOOK=$NEW_ONE (pass $i)"
    else
      log "Release pass $i reported success but no new slug detected"
      break
    fi
  else
    log "Release pass $i: no success marker"
    break
  fi
done

AFTER=$(python3 - <<'PY'
import json
from pathlib import Path
p = Path("state/progress.json")
d = json.loads(p.read_text()) if p.exists() else {}
print(",".join(d.get("released_books") or []))
PY
)

RELEASED_CSV=$(IFS=,; echo "${RELEASED_LIST[*]}")
NEW_BOOK="${RELEASED_LIST[0]:-}"
TITLES=$(python3 -c "import os; print(', '.join(b.replace('-',' ').title() for b in os.environ.get('R','').split(',') if b))" 2>/dev/null || true)
export R="$RELEASED_CSV"
TITLES=$(python3 - <<'PY'
import os
print(", ".join(b.replace("-", " ").title() for b in os.environ.get("R","").split(",") if b))
PY
)

if [[ ${#RELEASED_LIST[@]} -gt 0 ]]; then
  STATUS="released"
  REASON=""
  log "RELEASED_BOOKS=$RELEASED_CSV ($TITLES)"
  # compat
  log "RELEASED_BOOK=$NEW_BOOK"
elif [[ "$RELEASE_RC" -ne 0 ]]; then
  STATUS="error"
  REASON="release_failed_rc_${RELEASE_RC}"
  log "NO_RELEASE=$REASON"
else
  STATUS="noop"
  REASON="no_compiled_unreleased"
  log "NO_RELEASE=$REASON"
fi

python3 - <<PY
import json
from datetime import datetime, timezone
from pathlib import Path
released = [b for b in "$RELEASED_CSV".split(",") if b]
summary = {
  "ts": datetime.now(timezone.utc).isoformat(),
  "status": "$STATUS",
  "released_book": released[0] if released else None,
  "released_books": released,
  "title": "$TITLES" or None,
  "reason": "$REASON" or None,
  "compile_rc": $COMPILE_RC,
  "release_rc": $RELEASE_RC,
  "release_count_requested": int("$RELEASE_COUNT"),
  "released_books_after": [b for b in "$AFTER".split(",") if b],
}
Path("$SUMMARY_FILE").write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps(summary, indent=2))
PY

log "=== S1 next-book release end (status=$STATUS count=${#RELEASED_LIST[@]}) ==="

if [[ "$STATUS" == "error" ]]; then
  exit 1
fi
exit 0
