#!/data/data/com.termux/files/usr/bin/bash
# shellcheck shell=bash
# tools/heartbeat.sh  v3.2
# Sends an hourly Telegram heartbeat, validates the API response, and checks
# pipeline staleness via a deadman timer.  Cron: 0 * * * *
#
# Every result marker is written through result() to both stdout and
# cron.heartbeat.log.
#
# Result markers:
#   HEARTBEAT_RESULT=PASS
#   HEARTBEAT_RESULT=FAIL_ENV_RUNTIME_MISSING
#   HEARTBEAT_RESULT=FAIL_TELEGRAM_VARIABLES_MISSING
#   HEARTBEAT_RESULT=FAIL_TRANSPORT
#   HEARTBEAT_RESULT=FAIL_HTTP
#   HEARTBEAT_RESULT=FAIL_TELEGRAM_API
#   DEADMAN_RESULT=SHADOW_HEARTBEAT_MISSING
#   DEADMAN_RESULT=SHADOW_TIMESTAMP_MISSING
#   DEADMAN_RESULT=INVALID_SHADOW_TIMESTAMP
#   DEADMAN_RESULT=FUTURE_SHADOW_TIMESTAMP
#   DEADMAN_RESULT=ALERT_SENT
#   DEADMAN_RESULT=ALREADY_ALERTED
#   DEADMAN_RESULT=RECOVERY_SENT
#   DEADMAN_RESULT=HEALTHY
#   DEADMAN_RESULT=DEADMAN_DELIVERY_FAILED
#   DEADMAN_RESULT=RECOVERY_DELIVERY_FAILED
#
# Process status:
#   exit 1: HEARTBEAT_RESULT=FAIL_* (primary heartbeat could not be delivered)
#   exit 0: all other conditions, including secondary delivery failures
#
# Credentials: loads ONLY TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID from
# .env.runtime.  No other variables are assigned or auto-exported.
# Token, chat ID, response body, and API URL are never written to logs.
set -euo pipefail

ROOT="${BOTA_ROOT:-${HOME}/BotA}"
LOGDIR="${ROOT}/logs"
RUNTIME_ENV="${ROOT}/.env.runtime"
DEADMAN_FLAG="${LOGDIR}/state/deadman.flag"
SHADOW_HB="${LOGDIR}/shadow_manager_heartbeat.txt"
LOG="${LOGDIR}/cron.heartbeat.log"
CLOCK_JITTER_TOLERANCE_SEC=300

TGSEND_RESULT=""

mkdir -p "${LOGDIR}/state"

log() {
  printf '[%s] %s\n' "$(date -u '+%Y-%m-%d %H:%M:%S UTC')" "$*" >> "${LOG}"
}

result() {
  log "$1"
  printf '%s\n' "$1"
}

# ── Scoped credential loader ───────────────────────────────────────────────────
# Reads only TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID from the given file.
# No other variables are assigned or auto-exported.
_load_telegram_creds() {
  local file="$1"
  local line key val
  TELEGRAM_BOT_TOKEN=""
  TELEGRAM_CHAT_ID=""
  while IFS= read -r line; do
    if [[ "${line}" =~ ^[[:space:]]*# ]]; then continue; fi
    if [[ -z "${line//[[:space:]]/}" ]]; then continue; fi
    if ! [[ "${line}" =~ ^(TELEGRAM_BOT_TOKEN|TELEGRAM_CHAT_ID)=(.*)$ ]]; then continue; fi
    key="${BASH_REMATCH[1]}"
    val="${BASH_REMATCH[2]}"
    if [[ "${val}" =~ ^\"(.*)\"$ ]]; then val="${BASH_REMATCH[1]}"; fi
    if [[ "${val}" =~ ^\'(.*)\'$ ]]; then val="${BASH_REMATCH[1]}"; fi
    case "${key}" in
      TELEGRAM_BOT_TOKEN) TELEGRAM_BOT_TOKEN="${val}" ;;
      TELEGRAM_CHAT_ID)   TELEGRAM_CHAT_ID="${val}"   ;;
    esac
  done < "${file}"
}

# ── Shared Telegram sender ─────────────────────────────────────────────────────
# Sets global TGSEND_RESULT: TGSEND_PASS | TGSEND_FAIL_TRANSPORT |
#   TGSEND_FAIL_HTTP | TGSEND_FAIL_TELEGRAM_API
# JSON ok validation: response must parse as JSON, top-level ok must be the
# boolean true (not "true", not false, not absent).
# API URL, token, chat ID, and response body are never written to logs.
_send_telegram() {
  local text="$1"
  local timeout="${2:-20}"
  local _resp_file _curl_rc _http_code _ok_check
  _resp_file="$(mktemp)"
  _curl_rc=0
  _http_code=""
  set +e
  _http_code="$(curl \
    --silent \
    --max-time "${timeout}" \
    --request POST \
    --write-out '%{http_code}' \
    --output "${_resp_file}" \
    "${API_BASE}" \
    -d "parse_mode=HTML" \
    --data-urlencode "disable_web_page_preview=true" \
    --data-urlencode "chat_id=${TELEGRAM_CHAT_ID}" \
    --data-urlencode "text=${text}" \
    2>/dev/null)"
  _curl_rc=$?
  set -e
  _http_code="${_http_code:-000}"
  if [[ "${_curl_rc}" -ne 0 ]]; then
    rm -f "${_resp_file}"
    TGSEND_RESULT="TGSEND_FAIL_TRANSPORT"
    return 0
  fi
  if [[ "${_http_code}" -lt 200 || "${_http_code}" -ge 300 ]]; then
    rm -f "${_resp_file}"
    TGSEND_RESULT="TGSEND_FAIL_HTTP"
    return 0
  fi
  _ok_check="$(RESP_FILE="${_resp_file}" python3 -c "
import json, os, sys
try:
    with open(os.environ['RESP_FILE']) as fh:
        data = json.load(fh)
except Exception:
    print('FAIL'); sys.exit(0)
if isinstance(data, dict) and data.get('ok') is True:
    print('PASS')
else:
    print('FAIL')
" 2>/dev/null || printf 'FAIL')"
  rm -f "${_resp_file}"
  if [[ "${_ok_check}" != "PASS" ]]; then
    TGSEND_RESULT="TGSEND_FAIL_TELEGRAM_API"
    return 0
  fi
  TGSEND_RESULT="TGSEND_PASS"
  return 0
}

# ── Environment guards ─────────────────────────────────────────────────────────
if [[ ! -f "${RUNTIME_ENV}" ]]; then
  result "HEARTBEAT_RESULT=FAIL_ENV_RUNTIME_MISSING"
  exit 1
fi

_load_telegram_creds "${RUNTIME_ENV}"

if [[ -z "${TELEGRAM_BOT_TOKEN}" || -z "${TELEGRAM_CHAT_ID}" ]]; then
  result "HEARTBEAT_RESULT=FAIL_TELEGRAM_VARIABLES_MISSING"
  exit 1
fi

# ── Heartbeat send ─────────────────────────────────────────────────────────────
# API URL contains the token and must never be written to logs.
API_BASE="https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage"
HB_TEXT="💓 <b>Heartbeat</b> — BotA alive at $(date -u +'%Y-%m-%d %H:%M:%S UTC')"

_send_telegram "${HB_TEXT}"
case "${TGSEND_RESULT}" in
  TGSEND_PASS)              result "HEARTBEAT_RESULT=PASS" ;;
  TGSEND_FAIL_TRANSPORT)    result "HEARTBEAT_RESULT=FAIL_TRANSPORT";    exit 1 ;;
  TGSEND_FAIL_HTTP)         result "HEARTBEAT_RESULT=FAIL_HTTP";         exit 1 ;;
  TGSEND_FAIL_TELEGRAM_API) result "HEARTBEAT_RESULT=FAIL_TELEGRAM_API"; exit 1 ;;
  *)                        result "HEARTBEAT_RESULT=FAIL_UNKNOWN";      exit 1 ;;
esac

# ── Deadman / recovery check ───────────────────────────────────────────────────
if [[ ! -f "${SHADOW_HB}" ]]; then
  result "DEADMAN_RESULT=SHADOW_HEARTBEAT_MISSING"
  exit 0
fi

LAST_LINE="$(tail -1 "${SHADOW_HB}" 2>/dev/null || true)"
LAST_TS="$(printf '%s' "${LAST_LINE}" | awk -F'|' '{print $1}' | tr -d ' ')"

if [[ -z "${LAST_TS:-}" ]]; then
  result "DEADMAN_RESULT=SHADOW_TIMESTAMP_MISSING"
  exit 0
fi

LAST_EPOCH="$(LAST_TS="${LAST_TS}" python3 -c "
import datetime, os
ts = os.environ.get('LAST_TS', '').strip()
try:
    print(int(datetime.datetime.fromisoformat(ts).timestamp()))
except Exception:
    print('PARSE_ERROR')
" 2>/dev/null || printf 'PARSE_ERROR')"

if [[ "${LAST_EPOCH}" == "PARSE_ERROR" ]]; then
  result "DEADMAN_RESULT=INVALID_SHADOW_TIMESTAMP"
  exit 0
fi

NOW_EPOCH="$(date +%s)"

if (( LAST_EPOCH > NOW_EPOCH )); then
  FUTURE_SEC=$(( LAST_EPOCH - NOW_EPOCH ))
  if (( FUTURE_SEC > CLOCK_JITTER_TOLERANCE_SEC )); then
    log "DEADMAN_FUTURE_SEC=${FUTURE_SEC}"
    result "DEADMAN_RESULT=FUTURE_SHADOW_TIMESTAMP"
    exit 0
  fi
  AGE_MIN=0
else
  AGE_MIN=$(( (NOW_EPOCH - LAST_EPOCH) / 60 ))
fi

if (( AGE_MIN > 60 )); then
  if [[ ! -f "${DEADMAN_FLAG}" ]]; then
    DM_TEXT="[BotA DEADMAN] Pipeline stale for ${AGE_MIN}min — last heartbeat: ${LAST_TS}"
    _send_telegram "${DM_TEXT}" 10
    if [[ "${TGSEND_RESULT}" == "TGSEND_PASS" ]]; then
      printf '%s\n' "${DM_TEXT}" > "${DEADMAN_FLAG}"
      log "DEADMAN_AGE_MIN=${AGE_MIN}"
      result "DEADMAN_RESULT=ALERT_SENT"
    else
      result "DEADMAN_RESULT=DEADMAN_DELIVERY_FAILED"
    fi
  else
    result "DEADMAN_RESULT=ALREADY_ALERTED"
  fi
else
  if [[ -f "${DEADMAN_FLAG}" ]]; then
    REC_TEXT="[BotA RECOVERY] Pipeline alive again — last heartbeat: ${LAST_TS}"
    _send_telegram "${REC_TEXT}" 10
    if [[ "${TGSEND_RESULT}" == "TGSEND_PASS" ]]; then
      rm -f "${DEADMAN_FLAG}"
      result "DEADMAN_RESULT=RECOVERY_SENT"
    else
      result "DEADMAN_RESULT=RECOVERY_DELIVERY_FAILED"
    fi
  else
    result "DEADMAN_RESULT=HEALTHY"
  fi
fi

exit 0
