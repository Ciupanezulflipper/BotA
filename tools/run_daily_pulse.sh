#!/data/data/com.termux/files/usr/bin/bash
# tools/run_daily_pulse.sh
# BotA Daily Market Pulse — cron wrapper for Step 6.
#
# Usage:
#   bash tools/run_daily_pulse.sh            # live send to private test chat
#   bash tools/run_daily_pulse.sh --dry-run  # gates tested + shadow output, no send
#
# STEP 6 RULES:
#   - Private test chat only. Main channel NOT approved.
#   - Add to cron ONLY after manual tests pass.
#   - Supabase: NO. ProfitLab: NO. Entry/SL/TP: NO.
#   - Kill switch: rm state/pulse_enabled.flag
#   - Dedup uses UTC date — not local phone date.
#   - Dedup check runs in BOTH live and dry-run modes.
#   - Dedup file is ONLY created in live mode, never in dry-run.

set -uo pipefail

# ── PATHS ─────────────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BOT_DIR="$(dirname "$SCRIPT_DIR")"
PYTHON="python3"
PRODUCT_MSG="$SCRIPT_DIR/product_message_v1.py"
LOG="$BOT_DIR/logs/pulse_cron.log"
ENABLED_FLAG="$BOT_DIR/state/pulse_enabled.flag"
DOT_ENV="$BOT_DIR/.env"
PULSE_ENV="$BOT_DIR/config/pulse.env"

# ── DRY RUN FLAG ──────────────────────────────────────────────────────────────
DRY_RUN=false
if [[ "${1:-}" == "--dry-run" ]]; then
    DRY_RUN=true
fi

# ── UTC TIMESTAMPS ────────────────────────────────────────────────────────────
NOW_UTC="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
TODAY_UTC="$(date -u +%Y-%m-%d)"
DEDUP_FILE="$BOT_DIR/state/daily_pulse_sent_${TODAY_UTC}.ok"
DRY_TAG=""
$DRY_RUN && DRY_TAG="[DRY_RUN] "

# ── LOG HELPER ────────────────────────────────────────────────────────────────
log() {
    mkdir -p "$(dirname "$LOG")"
    echo "[${NOW_UTC}] ${DRY_TAG}$*" | tee -a "$LOG"
}

# ── REDACT HELPER ─────────────────────────────────────────────────────────────
redact_chat_id() {
    local id="${1:-}"
    if [[ "${#id}" -le 4 ]]; then
        echo "***"
    else
        echo "***${id: -4}"
    fi
}

# ── CHANGE TO BOT_DIR ─────────────────────────────────────────────────────────
# product_message_v1.py uses ROOT_DIR from __file__, but cd ensures
# relative paths in any subprocess also resolve correctly.
cd "$BOT_DIR"

# ── GATE 1: KILL SWITCH ───────────────────────────────────────────────────────
if [[ ! -f "$ENABLED_FLAG" ]]; then
    log "SKIP pulse disabled — $ENABLED_FLAG missing"
    exit 0
fi

# ── GATE 2: WEEKDAY CHECK (Mon–Fri UTC only) ──────────────────────────────────
DOW="$(date -u +%u)"  # 1=Mon … 7=Sun
if [[ "$DOW" -ge 6 ]]; then
    log "SKIP weekend (DOW=${DOW} UTC)"
    exit 0
fi

# ── GATE 3: DEDUP — runs in BOTH live and dry-run ────────────────────────────
# Dry-run proves the skip logic without creating the file.
# File is only created later in live mode, immediately before send.
if [[ -f "$DEDUP_FILE" ]]; then
    log "SKIP already sent today (UTC ${TODAY_UTC}) — $DEDUP_FILE exists"
    exit 0
fi

# ── GATE 4: LOAD ENV FILES ────────────────────────────────────────────────────
# Safe line-by-line loader — no arbitrary code execution.
# Strips surrounding single or double quotes from values.
# Skips comments (#) and blank lines.
load_env_file() {
    local file="$1"
    local label="$2"
    if [[ ! -f "$file" ]]; then
        log "FATAL ${label} not found: $file"
        exit 1
    fi
    while IFS= read -r line || [[ -n "$line" ]]; do
        [[ "$line" =~ ^[[:space:]]*# ]] && continue
        [[ -z "${line// }" ]] && continue
        if [[ "$line" =~ ^[A-Za-z_][A-Za-z0-9_]*= ]]; then
            local key="${line%%=*}"
            local val="${line#*=}"
            val="${val#\'}" ; val="${val%\'}"
            val="${val#\"}" ; val="${val%\"}"
            export "${key}=${val}" 2>/dev/null || true
        fi
    done < "$file"
}

load_env_file "$DOT_ENV"   ".env"
load_env_file "$PULSE_ENV" "config/pulse.env"

# Validate required variables after loading
if [[ -z "${TELEGRAM_BOT_TOKEN:-}" ]]; then
    log "FATAL TELEGRAM_BOT_TOKEN not set after loading $DOT_ENV"
    exit 1
fi
if [[ -z "${PULSE_TEST_CHAT_ID:-}" ]]; then
    log "FATAL PULSE_TEST_CHAT_ID not set after loading $PULSE_ENV"
    exit 1
fi

# ── GATE 5: M15 FRESHNESS ─────────────────────────────────────────────────────
MAX_AGE_M15=90
STALE_COUNT=0

for pair in EURUSD GBPUSD; do
    IND_FILE="$BOT_DIR/cache/indicators_${pair}_M15.json"
    if [[ ! -f "$IND_FILE" ]]; then
        log "WARN M15 cache missing: $pair"
        STALE_COUNT=$((STALE_COUNT + 1))
        continue
    fi
    age_min=$($PYTHON -c "
import json
try:
    d = json.loads(open('$IND_FILE').read())
    print(int(float(d.get('age_min', 9999))))
except Exception:
    print(9999)
" 2>/dev/null) || age_min=9999
    if [[ "${age_min:-9999}" -ge "$MAX_AGE_M15" ]]; then
        log "WARN M15 stale: $pair age=${age_min}min (max=${MAX_AGE_M15})"
        STALE_COUNT=$((STALE_COUNT + 1))
    fi
done

if [[ "$STALE_COUNT" -ge 2 ]]; then
    log "SKIP all pairs have stale M15 data — bot may be down or market closed"
    exit 0
fi

# ── GATE 6: PY_COMPILE ────────────────────────────────────────────────────────
if ! $PYTHON -m py_compile "$PRODUCT_MSG" 2>/dev/null; then
    log "FATAL py_compile failed: $PRODUCT_MSG"
    exit 1
fi

# ── DRY RUN EXIT PATH ─────────────────────────────────────────────────────────
if $DRY_RUN; then
    log "all gates passed — running shadow output (no Telegram send)"
    $PYTHON "$PRODUCT_MSG" --type market_pulse --shadow
    log "DRY_RUN complete — dedup file NOT created — TELEGRAM_SENT=NO"
    exit 0
fi

# ── MARK DEDUP BEFORE SEND (live mode only) ───────────────────────────────────
# Created before send to prevent double-send if process is interrupted.
# UTC-dated — never blocks tomorrow's pulse.
mkdir -p "$(dirname "$DEDUP_FILE")"
touch "$DEDUP_FILE"
log "dedup file created: $DEDUP_FILE"

# ── LIVE SEND ─────────────────────────────────────────────────────────────────
REDACTED_CHAT="$(redact_chat_id "$PULSE_TEST_CHAT_ID")"
log "SEND initiating — target: ${REDACTED_CHAT}"

if $PYTHON "$PRODUCT_MSG" \
    --type market_pulse \
    --send \
    --chat-id "$PULSE_TEST_CHAT_ID"; then
    log "SEND success — TELEGRAM_SENT=YES SUPABASE_PUBLISHED=NO"
else
    EXIT_CODE=$?
    log "ERROR send failed (exit=${EXIT_CODE}) — dedup file retained to prevent retry spam"
    exit "$EXIT_CODE"
fi
