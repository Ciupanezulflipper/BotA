#!/data/data/com.termux/files/usr/bin/bash
# FILE: tools/daily_summary_server_gate.sh
# ROLE: Server-UTC gate for BotA daily proof-of-work summary.
#
# Termux cron uses device/local time. On ship mode, Android time can drift.
# This wrapper checks server UTC first, then sends daily_summary.sh only during
# the target server-UTC hour, once per server date.
#
# Daily-summary-only fallback:
# - If live server clock is unavailable, use logs/clock_drift_last_good.json.
# - Estimate current server UTC from last-good server/local pair.
# - Only valid if last-good is younger than DAILY_SUMMARY_LAST_GOOD_MAX_AGE_SECONDS.
# - This fallback is NOT used by trading or market gates.
#
# Safety:
# - No strategy changes
# - No threshold changes
# - No H1 logic changes
# - No signal generation changes
# - No market_open.sh changes

set -euo pipefail

ROOT="${BOTA_ROOT:-${HOME}/BotA}"
LOGDIR="${ROOT}/logs"
STATE_DIR="${ROOT}/state"
TARGET_HOUR_UTC="${DAILY_SUMMARY_TARGET_HOUR_UTC:-20}"
FALLBACK_MAX_AGE_SECONDS="${DAILY_SUMMARY_LAST_GOOD_MAX_AGE_SECONDS:-28800}"
LAST_GOOD_FILE="${LOGDIR}/clock_drift_last_good.json"

mkdir -p "$LOGDIR" "$STATE_DIR"

ts_phone_utc() { date -u '+%Y-%m-%d %H:%M:%S UTC'; }

log() {
  echo "[$(ts_phone_utc)] $*" >> "${LOGDIR}/daily_summary_gate.log"
}

if [[ "${DAILY_SUMMARY_CLOCK_FORCE_FAIL:-0}" = "1" ]]; then
  CLOCK_JSON='{"server_clock_ok": false, "server_utc": "NA", "drift_seconds": null, "status": "FORCED_CLOCK_FAIL_FOR_TEST"}'
else
  CLOCK_JSON="$(
    python3 "${ROOT}/tools/clock_drift_check.py" --json --write-state 2>/dev/null || true
  )"
fi

if [[ -z "$CLOCK_JSON" ]]; then
  echo "GATE_SKIP reason=clock_check_empty"
  log "GATE_SKIP reason=clock_check_empty"
  exit 0
fi

GATE_INFO="$(
CLOCK_JSON="$CLOCK_JSON" \
TARGET_HOUR_UTC="$TARGET_HOUR_UTC" \
LAST_GOOD_FILE="$LAST_GOOD_FILE" \
FALLBACK_MAX_AGE_SECONDS="$FALLBACK_MAX_AGE_SECONDS" \
python3 - <<'PY'
import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

raw = os.environ.get("CLOCK_JSON", "")
target = int(os.environ.get("TARGET_HOUR_UTC", "20"))
last_good_file = Path(os.environ.get("LAST_GOOD_FILE", ""))
max_age = int(os.environ.get("FALLBACK_MAX_AGE_SECONDS", "28800"))

def clean(value):
    return str(value).replace("|", "/").replace("\n", " ").strip()

def iso_z(dt):
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def parse_iso(value):
    if value in (None, "", "NA"):
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return None

def emit_fail(live_status, server_utc="NA", drift="UNKNOWN", reason="unknown"):
    print(
        f"CLOCK_FAIL|NA|NA|{clean(server_utc)}|{clean(drift)}|"
        f"status={clean(live_status)};fallback=not_usable;reason={clean(reason)}"
    )

try:
    data = json.loads(raw)
except Exception as exc:
    print(f"PARSE_FAIL|NA|NA|NA|NA|json_error:{type(exc).__name__}")
    raise SystemExit(0)

live_status = data.get("status", "UNKNOWN")
server_ok = bool(data.get("server_clock_ok"))
server_utc_raw = data.get("server_utc") or "NA"
drift = data.get("drift_seconds", "UNKNOWN")

dt = None
clock_source = "live"
detail = f"clock_source=live;status={clean(live_status)}"

if server_ok and server_utc_raw not in ("NA", "", None):
    dt = parse_iso(server_utc_raw)
    if dt is None:
        emit_fail(live_status, server_utc_raw, drift, "live_time_parse_fail")
        raise SystemExit(0)
else:
    clock_source = "last_good"
    try:
        last_good = json.loads(last_good_file.read_text(encoding="utf-8"))
    except Exception as exc:
        emit_fail(live_status, server_utc_raw, drift, f"last_good_read_fail_{type(exc).__name__}")
        raise SystemExit(0)

    last_server_dt = parse_iso(last_good.get("server_utc"))
    last_local_dt = parse_iso(last_good.get("local_utc") or last_good.get("generated_utc"))
    last_drift = last_good.get("drift_seconds", "UNKNOWN")

    if last_server_dt is None:
        emit_fail(live_status, server_utc_raw, drift, "last_good_missing_server_utc")
        raise SystemExit(0)

    if last_local_dt is None:
        emit_fail(live_status, server_utc_raw, drift, "last_good_missing_local_utc")
        raise SystemExit(0)

    now_local_dt = datetime.now(timezone.utc)
    age_seconds = int((now_local_dt - last_local_dt).total_seconds())

    if age_seconds < 0:
        emit_fail(live_status, server_utc_raw, drift, f"last_good_from_future_age_{age_seconds}")
        raise SystemExit(0)

    if age_seconds > max_age:
        emit_fail(live_status, server_utc_raw, drift, f"last_good_too_old_age_{age_seconds}_max_{max_age}")
        raise SystemExit(0)

    dt = last_server_dt + timedelta(seconds=age_seconds)
    server_utc_raw = iso_z(dt)
    drift = int(now_local_dt.timestamp()) - int(dt.timestamp())
    detail = (
        f"clock_source=last_good;"
        f"status=FALLBACK_LAST_GOOD;"
        f"live_status={clean(live_status)};"
        f"age_secs={age_seconds};"
        f"max_age_secs={max_age};"
        f"last_drift={clean(last_drift)}"
    )

server_date = dt.strftime("%Y-%m-%d")
server_hour = dt.hour
server_iso = iso_z(dt)

if server_hour == target:
    print(f"SEND_WINDOW|{server_date}|{server_hour}|{server_iso}|{drift}|target_hour={target};{detail}")
else:
    print(f"OUTSIDE_WINDOW|{server_date}|{server_hour}|{server_iso}|{drift}|target_hour={target};{detail}")
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
  echo "GATE_DRY_RUN would_send=YES server_date=${server_date} server_utc=${server_iso} drift=${drift} detail=${detail}"
  log "GATE_DRY_RUN would_send=YES server_date=${server_date} server_utc=${server_iso} drift=${drift} detail=${detail}"
  exit 0
fi

echo "GATE_SEND_START server_date=${server_date} server_utc=${server_iso} drift=${drift} detail=${detail}"
log "GATE_SEND_START server_date=${server_date} server_utc=${server_iso} drift=${drift} detail=${detail}"

SEND_OUTPUT="$(
  SUMMARY_DATE="${server_date}" DAILY_SUMMARY_SEND="${DAILY_SUMMARY_SEND:-1}" bash "${ROOT}/tools/daily_summary.sh" 2>&1 || true
)"

echo "$SEND_OUTPUT"
log "DAILY_SUMMARY_OUTPUT $(printf '%s' "$SEND_OUTPUT" | tr '\n' ' ' | head -c 800)"

if printf '%s' "$SEND_OUTPUT" | grep -q "TELEGRAM_SEND=PASS"; then
  {
    echo "sent_utc=${server_iso}"
    echo "server_date=${server_date}"
    echo "drift=${drift}"
    echo "detail=${detail}"
  } > "$SENT_FILE"

  echo "GATE_SEND_DONE status=PASS server_date=${server_date}"
  log "GATE_SEND_DONE status=PASS server_date=${server_date}"
else
  echo "GATE_SEND_DONE status=NO_PASS_MARKER server_date=${server_date}"
  log "GATE_SEND_DONE status=NO_PASS_MARKER server_date=${server_date}"
fi

exit 0
