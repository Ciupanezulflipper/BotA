#!/data/data/com.termux/files/usr/bin/bash
# FILE: tools/daily_summary_server_gate.sh
# ROLE: Server-UTC gate for BotA daily proof-of-work summary.
#
# Termux cron uses device/local time. On ship mode, Android time can drift.
# This wrapper checks server UTC first, then sends daily_summary.sh only during
# the target server-UTC hour, once per server date.
#
# Safety:
# - No strategy changes
# - No threshold changes
# - No H1 logic changes
# - No signal generation changes

set -euo pipefail

ROOT="${BOTA_ROOT:-${HOME}/BotA}"
LOGDIR="${ROOT}/logs"
STATE_DIR="${ROOT}/state"
TARGET_HOUR_UTC="${DAILY_SUMMARY_TARGET_HOUR_UTC:-20}"

mkdir -p "$LOGDIR" "$STATE_DIR"

ts_phone_utc() { date -u '+%Y-%m-%d %H:%M:%S UTC'; }

log() {
  echo "[$(ts_phone_utc)] $*" >> "${LOGDIR}/daily_summary_gate.log"
}

CLOCK_JSON="$(
  python3 "${ROOT}/tools/clock_drift_check.py" --json --write-state 2>/dev/null || true
)"

if [[ -z "$CLOCK_JSON" ]]; then
  echo "GATE_SKIP reason=clock_check_empty"
  log "GATE_SKIP reason=clock_check_empty"
  exit 0
fi

GATE_INFO="$(
CLOCK_JSON="$CLOCK_JSON" TARGET_HOUR_UTC="$TARGET_HOUR_UTC" python3 - <<'PY'
import json
import os
from datetime import datetime, timezone

raw = os.environ.get("CLOCK_JSON", "")
target = int(os.environ.get("TARGET_HOUR_UTC", "20"))

try:
    data = json.loads(raw)
except Exception as exc:
    print(f"PARSE_FAIL|NA|NA|NA|NA|json_error:{type(exc).__name__}")
    raise SystemExit(0)

server_ok = bool(data.get("server_clock_ok"))
server_utc = data.get("server_utc") or "NA"
status = data.get("status", "UNKNOWN")
drift = data.get("drift_seconds", "UNKNOWN")

if not server_ok or server_utc in ("NA", "", None):
    print(f"CLOCK_FAIL|NA|NA|{server_utc}|{drift}|status={status}")
    raise SystemExit(0)

try:
    dt = datetime.fromisoformat(str(server_utc).replace("Z", "+00:00")).astimezone(timezone.utc)
except Exception as exc:
    print(f"TIME_PARSE_FAIL|NA|NA|{server_utc}|{drift}|time_error:{type(exc).__name__}")
    raise SystemExit(0)

server_date = dt.strftime("%Y-%m-%d")
server_hour = dt.hour

if server_hour == target:
    print(f"SEND_WINDOW|{server_date}|{server_hour}|{server_utc}|{drift}|status={status}")
else:
    print(f"OUTSIDE_WINDOW|{server_date}|{server_hour}|{server_utc}|{drift}|target_hour={target}|status={status}")
PY
)"

IFS='|' read -r gate_status server_date server_hour server_iso drift detail <<< "$GATE_INFO"

case "$gate_status" in
  SEND_WINDOW)
    ;;
  *)
    echo "GATE_SKIP status=${gate_status} server_utc=${server_iso} server_hour=${server_hour} drift=${drift} detail=${detail}"
    log "GATE_SKIP status=${gate_status} server_utc=${server_iso} server_hour=${server_hour} drift=${drift} detail=${detail}"
    exit 0
    ;;
esac

SENT_FILE="${STATE_DIR}/daily_summary_sent_${server_date}.ok"

if [[ -f "$SENT_FILE" ]]; then
  echo "GATE_SKIP reason=already_sent server_date=${server_date} server_utc=${server_iso}"
  log "GATE_SKIP reason=already_sent server_date=${server_date} server_utc=${server_iso}"
  exit 0
fi

if [[ "${DAILY_SUMMARY_GATE_DRY_RUN:-0}" = "1" ]]; then
  echo "GATE_DRY_RUN would_send=YES server_date=${server_date} server_utc=${server_iso} drift=${drift}"
  log "GATE_DRY_RUN would_send=YES server_date=${server_date} server_utc=${server_iso} drift=${drift}"
  exit 0
fi

echo "GATE_SEND_START server_date=${server_date} server_utc=${server_iso} drift=${drift}"
log "GATE_SEND_START server_date=${server_date} server_utc=${server_iso} drift=${drift}"

SEND_OUTPUT="$(
  DAILY_SUMMARY_SEND="${DAILY_SUMMARY_SEND:-1}" bash "${ROOT}/tools/daily_summary.sh" 2>&1 || true
)"

echo "$SEND_OUTPUT"
log "DAILY_SUMMARY_OUTPUT $(printf '%s' "$SEND_OUTPUT" | tr '\n' ' ' | head -c 800)"

if printf '%s' "$SEND_OUTPUT" | grep -q "TELEGRAM_SEND=PASS"; then
  {
    echo "sent_utc=${server_iso}"
    echo "server_date=${server_date}"
    echo "drift=${drift}"
  } > "$SENT_FILE"

  echo "GATE_SEND_DONE status=PASS server_date=${server_date}"
  log "GATE_SEND_DONE status=PASS server_date=${server_date}"
else
  echo "GATE_SEND_DONE status=NO_PASS_MARKER server_date=${server_date}"
  log "GATE_SEND_DONE status=NO_PASS_MARKER server_date=${server_date}"
fi

exit 0
