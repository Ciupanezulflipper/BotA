#!/bin/bash
# heartbeat.sh — quiet hourly heartbeat (cron: minute 0)
set -euo pipefail

ROOT="$HOME/BotA"
TMPDIR="$ROOT/tmp"
LOGDIR="$ROOT/logs"
TELE="$ROOT/config/tele.env"

mkdir -p "$TMPDIR" "$LOGDIR"

log(){ echo "[$(date -u +'%Y-%m-%d %H:%M:%S UTC')] $*" >> "$LOGDIR/cron.heartbeat.log"; }

# --- Load Telegram creds ---
if [ -f "$TELE" ]; then
  . "$TELE"
else
  log "❌ tele.env missing"
  exit 0
fi

if [ -z "${TELEGRAM_BOT_TOKEN:-}" ] || [ -z "${TELEGRAM_CHAT_ID:-}" ]; then
  log "❌ TELEGRAM_* vars missing"
  exit 0
fi

# --- Send heartbeat ---
API="https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage"
TEXT="💓 <b>Heartbeat</b> — BotA alive at $(date -u +'%Y-%m-%d %H:%M:%S UTC')"

RESP="$(curl -sS -X POST "$API" \
  -d "chat_id=${TELEGRAM_CHAT_ID}" \
  -d "parse_mode=HTML" \
  --data-urlencode "disable_web_page_preview=true" \
  --data-urlencode "text=$TEXT" || true)"

if echo "$RESP" | grep -q '"ok":true'; then
  log "✅ Heartbeat sent"
else
  log "❌ Heartbeat failed resp=$(echo "$RESP" | tr '\n' ' ')"
fi

# --- Deadman alert: shadow_manager pipeline staleness check ---
{
  DEADMAN_FLAG="$LOGDIR/state/deadman.flag"
  SHADOW_HB="$LOGDIR/shadow_manager_heartbeat.txt"
  mkdir -p "$LOGDIR/state"

  if [[ -f "$SHADOW_HB" ]]; then
    LAST_LINE="$(tail -1 "$SHADOW_HB" 2>/dev/null || true)"
    LAST_TS="$(echo "$LAST_LINE" | awk -F'|' '{print $1}' | tr -d ' ')"

    if [[ -n "${LAST_TS:-}" ]]; then
      LAST_EPOCH="$(LAST_TS="${LAST_TS}" python3 -c "
import datetime, os
ts = os.environ.get('LAST_TS','').strip()
try:
    print(int(datetime.datetime.fromisoformat(ts).timestamp()))
except:
    print(0)
" 2>/dev/null || echo 0)"
      NOW_EPOCH="$(date +%s)"
      AGE_MIN=$(( (NOW_EPOCH - LAST_EPOCH) / 60 ))

      if (( AGE_MIN > 60 )); then
        if [[ ! -f "$DEADMAN_FLAG" ]]; then
          DM_TEXT="[BotA DEADMAN] Pipeline stale for ${AGE_MIN}min — last heartbeat: ${LAST_TS}"
          curl -sS --max-time 10 -X POST "$API" \
            -d "chat_id=${TELEGRAM_CHAT_ID}" \
            -d "parse_mode=HTML" \
            --data-urlencode "text=${DM_TEXT}" >/dev/null 2>&1 || true
          echo "${DM_TEXT}" > "$DEADMAN_FLAG"
          log "⚠️ DEADMAN alert sent: pipeline stale ${AGE_MIN}min"
        fi
      else
        if [[ -f "$DEADMAN_FLAG" ]]; then
          REC_TEXT="[BotA RECOVERY] Pipeline alive again — last heartbeat: ${LAST_TS}"
          curl -sS --max-time 10 -X POST "$API" \
            -d "chat_id=${TELEGRAM_CHAT_ID}" \
            -d "parse_mode=HTML" \
            --data-urlencode "text=${REC_TEXT}" >/dev/null 2>&1 || true
          rm -f "$DEADMAN_FLAG"
          log "✅ RECOVERY alert sent: pipeline alive again"
        fi
      fi
    fi
  fi
} || true

exit 0
