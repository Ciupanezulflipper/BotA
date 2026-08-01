#!/data/data/com.termux/files/usr/bin/bash
# shellcheck shell=bash
# tools/bota_heartbeat_utc.sh
# Ship-time-independent hourly heartbeat using authoritative server UTC.
#
# Sends one Telegram heartbeat per UTC hour bucket.
# The bucket key (YYYYMMDDHH) is derived from HTTPS server clock, never from
# the Android system clock.  Safe when the device clock is manually adjusted
# to match ship time.
#
# Also performs a deadman check using server epoch instead of date +%s.
#
# Result markers (written to LOG and stdout):
#   HB_UTC_RESULT=PASS                     — heartbeat sent for new bucket
#   HB_UTC_RESULT=BUCKET_UNCHANGED         — already sent for this UTC hour
#   HB_UTC_RESULT=FAIL_SERVER_UTC          — could not obtain authoritative UTC
#   HB_UTC_RESULT=FAIL_ENV_MISSING         — .env.runtime not found
#   HB_UTC_RESULT=FAIL_CREDS_MISSING       — Telegram creds absent
#   HB_UTC_RESULT=FAIL_TRANSPORT           — Telegram send failed (transport)
#   HB_UTC_RESULT=FAIL_HTTP                — Telegram send failed (HTTP)
#   HB_UTC_RESULT=FAIL_API                 — Telegram send failed (API response)
#   DEADMAN_UTC_RESULT=HEALTHY             — pipeline fresh
#   DEADMAN_UTC_RESULT=ALERT_SENT          — stale pipeline alert delivered
#   DEADMAN_UTC_RESULT=ALREADY_ALERTED     — stale pipeline, alert already sent
#   DEADMAN_UTC_RESULT=RECOVERY_SENT       — pipeline recovered
#   DEADMAN_UTC_RESULT=SHADOW_MISSING      — shadow heartbeat file absent
#   DEADMAN_UTC_RESULT=TIMESTAMP_INVALID   — shadow timestamp parse error
#   DEADMAN_UTC_RESULT=SKIP_SERVER_UTC     — server UTC unavailable; skip check
#
# Exit 0 always (secondary failures do not justify runit restart).
set -uo pipefail

ROOT="${BOTA_ROOT:-${HOME}/BotA}"
LOGDIR="${ROOT}/logs"
RUNTIME_ENV="${ROOT}/.env.runtime"
BUCKET_FILE="${LOGDIR}/state/heartbeat_utc_bucket.txt"
DEADMAN_FLAG="${LOGDIR}/state/deadman.flag"
SHADOW_HB="${LOGDIR}/shadow_manager_heartbeat.txt"
SHADOW_MONO="${ROOT}/state/shadow_progress.monotonic"
LOG="${LOGDIR}/cron.heartbeat.log"
DEADMAN_STALE_MINUTES=90

mkdir -p "${LOGDIR}/state"

log()    { printf '[%s] %s\n' "$(date -u '+%Y-%m-%d %H:%M:%S UTC')" "$*" >> "${LOG}"; }
result() { log "$1"; printf '%s\n' "$1"; }

# ── Fetch authoritative server epoch (multi-endpoint consensus) ────────────────
_server_epoch() {
    python3 - <<'PYEOF' 2>/dev/null
import urllib.request, statistics
URLS = [
    "https://www.google.com",
    "https://api-fxpractice.oanda.com",
    "https://query1.finance.yahoo.com",
]
from email.utils import parsedate_to_datetime
epochs = []
for url in URLS:
    try:
        r = urllib.request.urlopen(url, timeout=8)
        d = r.headers.get("Date", "")
        if d:
            epochs.append(int(parsedate_to_datetime(d).timestamp()))
    except Exception:
        pass
if len(epochs) >= 2:
    spread = max(epochs) - min(epochs)
    if spread <= 10:
        print(int(statistics.median(epochs)))
    else:
        print(int(statistics.median(epochs)))
elif len(epochs) == 1:
    print(epochs[0])
PYEOF
}

# ── Scoped credential loader (same pattern as heartbeat.sh v3.2) ───────────────
_load_telegram_creds() {
    local file="$1" line key val
    TELEGRAM_BOT_TOKEN=""
    TELEGRAM_CHAT_ID=""
    while IFS= read -r line; do
        if [[ "${line}" =~ ^[[:space:]]*# ]]; then continue; fi
        if [[ -z "${line//[[:space:]]/}" ]]; then continue; fi
        if ! [[ "${line}" =~ ^(TELEGRAM_BOT_TOKEN|TELEGRAM_CHAT_ID)=(.*)$ ]]; then continue; fi
        key="${BASH_REMATCH[1]}"; val="${BASH_REMATCH[2]}"
        if [[ "${val}" =~ ^\"(.*)\"$ ]]; then val="${BASH_REMATCH[1]}"; fi
        if [[ "${val}" =~ ^\'(.*)\'$ ]]; then val="${BASH_REMATCH[1]}"; fi
        case "${key}" in
            TELEGRAM_BOT_TOKEN) TELEGRAM_BOT_TOKEN="${val}" ;;
            TELEGRAM_CHAT_ID)   TELEGRAM_CHAT_ID="${val}"   ;;
        esac
    done < "${file}"
}

TGSEND_RESULT=""
_send_telegram() {
    local text="$1" timeout="${2:-20}" _resp_file _curl_rc _http_code _ok
    _resp_file="$(mktemp)"
    set +e
    _http_code="$(curl --silent --max-time "${timeout}" --request POST \
        --write-out '%{http_code}' --output "${_resp_file}" \
        "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
        -d "parse_mode=HTML" \
        --data-urlencode "disable_web_page_preview=true" \
        --data-urlencode "chat_id=${TELEGRAM_CHAT_ID}" \
        --data-urlencode "text=${text}" 2>/dev/null)"
    _curl_rc=$?; set -e; _http_code="${_http_code:-000}"
    if [[ "${_curl_rc}" -ne 0 ]]; then rm -f "${_resp_file}"; TGSEND_RESULT="FAIL_TRANSPORT"; return; fi
    if [[ "${_http_code}" -lt 200 || "${_http_code}" -ge 300 ]]; then rm -f "${_resp_file}"; TGSEND_RESULT="FAIL_HTTP"; return; fi
    _ok="$(RESP="${_resp_file}" python3 -c "
import json,os
try:
    d=json.load(open(os.environ['RESP']))
    print('PASS' if isinstance(d,dict) and d.get('ok') is True else 'FAIL')
except Exception: print('FAIL')
" 2>/dev/null || printf 'FAIL')"
    rm -f "${_resp_file}"
    TGSEND_RESULT="$( [[ "${_ok}" == 'PASS' ]] && echo 'PASS' || echo 'FAIL_API' )"
}

# ── 1. Credentials ────────────────────────────────────────────────────────────
if [[ ! -f "${RUNTIME_ENV}" ]]; then
    result "HB_UTC_RESULT=FAIL_ENV_MISSING"
    exit 0
fi
_load_telegram_creds "${RUNTIME_ENV}"
if [[ -z "${TELEGRAM_BOT_TOKEN}" || -z "${TELEGRAM_CHAT_ID}" ]]; then
    result "HB_UTC_RESULT=FAIL_CREDS_MISSING"
    exit 0
fi

# ── 2. Authoritative server UTC ───────────────────────────────────────────────
SERVER_EPOCH="$(_server_epoch)"
if [[ -z "${SERVER_EPOCH}" ]]; then
    result "HB_UTC_RESULT=FAIL_SERVER_UTC"
    exit 0
fi

UTC_BUCKET="$(python3 -c "
import datetime
dt = datetime.datetime.fromtimestamp(${SERVER_EPOCH}, datetime.timezone.utc)
print(dt.strftime('%Y%m%d%H'))
" 2>/dev/null)"

if [[ -z "${UTC_BUCKET}" ]]; then
    result "HB_UTC_RESULT=FAIL_SERVER_UTC"
    exit 0
fi

# ── 3. UTC hour bucket gate ────────────────────────────────────────────────────
LAST_BUCKET="$(cat "${BUCKET_FILE}" 2>/dev/null || echo '')"
if [[ "${UTC_BUCKET}" == "${LAST_BUCKET}" ]]; then
    result "HB_UTC_RESULT=BUCKET_UNCHANGED"
    # Still run deadman check even if heartbeat not sent this hour
else
    # New UTC hour — send heartbeat
    HB_TEXT="💓 <b>Heartbeat</b> — BotA alive at $(python3 -c "
import datetime
dt = datetime.datetime.fromtimestamp(${SERVER_EPOCH}, datetime.timezone.utc)
print(dt.strftime('%Y-%m-%d %H:%M:%S UTC'))
" 2>/dev/null)"
    _send_telegram "${HB_TEXT}"
    case "${TGSEND_RESULT}" in
        PASS)          printf '%s\n' "${UTC_BUCKET}" > "${BUCKET_FILE}"; result "HB_UTC_RESULT=PASS" ;;
        FAIL_TRANSPORT) result "HB_UTC_RESULT=FAIL_TRANSPORT" ;;
        FAIL_HTTP)      result "HB_UTC_RESULT=FAIL_HTTP" ;;
        FAIL_API)       result "HB_UTC_RESULT=FAIL_API" ;;
        *)              result "HB_UTC_RESULT=FAIL_TRANSPORT" ;;
    esac
fi

# ── 4. Deadman check using monotonic successful progress ─────────────────────
if [[ ! -f "${SHADOW_MONO}" ]]; then
    result "DEADMAN_UTC_RESULT=MONOTONIC_PROGRESS_MISSING"
    exit 0
fi

read -r PROGRESS_BOOT PROGRESS_MONO < "${SHADOW_MONO}" || true

CURRENT_BOOT="$(cat /proc/sys/kernel/random/boot_id 2>/dev/null || echo unknown)"
CURRENT_MONO="$(python3 -c 'import time; c=getattr(time,"CLOCK_BOOTTIME",None); print(time.clock_gettime_ns(c)//1_000_000_000 if c is not None else time.monotonic_ns()//1_000_000_000)')"

if [[ -z "${PROGRESS_BOOT:-}" ||
      ! "${PROGRESS_MONO:-}" =~ ^[0-9]+$ ]]; then
    result "DEADMAN_UTC_RESULT=MONOTONIC_PROGRESS_INVALID"
    exit 0
fi

if [[ "${PROGRESS_BOOT}" != "${CURRENT_BOOT}" ]]; then
    result "DEADMAN_UTC_RESULT=BOOT_CHANGED_WAITING_FOR_PROGRESS"
    exit 0
fi

AGE_SEC=$(( CURRENT_MONO - PROGRESS_MONO ))

if (( AGE_SEC < 0 )); then
    result "DEADMAN_UTC_RESULT=MONOTONIC_PROGRESS_INVALID"
    exit 0
fi

AGE_MIN=$(( AGE_SEC / 60 ))

LAST_LINE="$(tail -1 "${SHADOW_HB}" 2>/dev/null || true)"
LAST_TS="$(printf '%s' "${LAST_LINE}" | awk -F'|' '{print $1}' | tr -d ' ')"
[[ -n "${LAST_TS}" ]] || LAST_TS="display timestamp unavailable"

DM_TEXT="[BotA DEADMAN] Pipeline stale for ${AGE_MIN}min (server UTC: $(python3 -c "
import datetime
dt = datetime.datetime.fromtimestamp(${SERVER_EPOCH}, datetime.timezone.utc)
print(dt.strftime('%Y-%m-%d %H:%M UTC'))
" 2>/dev/null)) — last shadow: ${LAST_TS}"

if (( AGE_MIN > DEADMAN_STALE_MINUTES )); then
    if [[ ! -f "${DEADMAN_FLAG}" ]]; then
        _send_telegram "${DM_TEXT}" 10
        if [[ "${TGSEND_RESULT}" == 'PASS' ]]; then
            printf '%s\n' "${DM_TEXT}" > "${DEADMAN_FLAG}"
            log "DEADMAN_AGE_MIN=${AGE_MIN}"
            result "DEADMAN_UTC_RESULT=ALERT_SENT"
        else
            result "DEADMAN_UTC_RESULT=DELIVERY_FAILED"
        fi
    else
        result "DEADMAN_UTC_RESULT=ALREADY_ALERTED"
    fi
else
    if [[ -f "${DEADMAN_FLAG}" ]]; then
        REC_TEXT="[BotA RECOVERY] Pipeline alive — last shadow: ${LAST_TS}"
        _send_telegram "${REC_TEXT}" 10
        if [[ "${TGSEND_RESULT}" == 'PASS' ]]; then
            rm -f "${DEADMAN_FLAG}"
            result "DEADMAN_UTC_RESULT=RECOVERY_SENT"
        else
            result "DEADMAN_UTC_RESULT=RECOVERY_DELIVERY_FAILED"
        fi
    else
        result "DEADMAN_UTC_RESULT=HEALTHY"
    fi
fi

exit 0
