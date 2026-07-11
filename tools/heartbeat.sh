#!/data/data/com.termux/files/usr/bin/bash
set -u

ROOT="$HOME/BotA"
LOG="$ROOT/logs/cron.heartbeat.log"
RUNTIME_ENV="$ROOT/.env.runtime"

mkdir -p "$ROOT/logs"

timestamp() {
  date -u '+%Y-%m-%d %H:%M:%S UTC'
}

log() {
  printf '[%s] %s\n' "$(timestamp)" "$*" >> "$LOG"
}

if [ -f "$RUNTIME_ENV" ]; then
  set -a
  . "$RUNTIME_ENV"
  set +a
else
  log "❌ .env.runtime missing"
  printf '%s\n' "HEARTBEAT_RESULT=FAIL_ENV_RUNTIME_MISSING"
  exit 0
fi

if [ -z "${TELEGRAM_BOT_TOKEN:-}" ] ||
   [ -z "${TELEGRAM_CHAT_ID:-}" ]; then
  log "❌ Telegram credential variables missing from .env.runtime"
  printf '%s\n' "HEARTBEAT_RESULT=FAIL_TELEGRAM_VARIABLES_MISSING"
  exit 0
fi

API="https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage"
HOST="$(hostname 2>/dev/null || printf '%s' unknown)"
NOW="$(timestamp)"

message="✅ BotA heartbeat
Host: ${HOST}
UTC: ${NOW}"

curl \
  --silent \
  --show-error \
  --max-time 20 \
  --request POST \
  "$API" \
  --data-urlencode "chat_id=${TELEGRAM_CHAT_ID}" \
  --data-urlencode "text=${message}" \
  >/dev/null 2>>"$LOG"

curl_rc=$?

if [ "$curl_rc" -eq 0 ]; then
  log "✅ heartbeat delivered"
  printf '%s\n' "HEARTBEAT_RESULT=PASS"
else
  log "❌ heartbeat delivery failed rc=$curl_rc"
  printf '%s\n' "HEARTBEAT_RESULT=FAIL_DELIVERY rc=$curl_rc"
fi

exit 0
