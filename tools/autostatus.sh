#!/data/data/com.termux/files/usr/bin/bash
# FILE: tools/autostatus.sh
# ROLE: Send cache-only technical trend context during the configured FX session.

set -euo pipefail

ROOT="${BOTA_ROOT:-${HOME}/BotA}"
TMPDIR="${ROOT}/tmp"
LOGDIR="${ROOT}/logs"
TELE="${ROOT}/config/tele.env"
MARKET_GATE="${BOTA_MARKET_GATE:-${ROOT}/tools/market_open.sh}"
FORMATTER="${BOTA_STATUS_FORMATTER:-${ROOT}/tools/format_status.py}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
CURL_BIN="${CURL_BIN:-curl}"

mkdir -p "${TMPDIR}" "${LOGDIR}"

log() {
  printf '[%s] %s\n' "$(date -u +'%Y-%m-%d %H:%M:%S UTC')" "$*" \
    >>"${LOGDIR}/cron.autostatus.log"
}

if [[ ! -x "${MARKET_GATE}" ]]; then
  log "SKIP: market_gate_missing_or_not_executable"
  exit 0
fi

MARKET_STATE=""
if MARKET_STATE="$(${MARKET_GATE} 2>>"${LOGDIR}/cron.autostatus.log")"; then
  :
else
  log "SKIP: market_closed_or_clock_unavailable state=${MARKET_STATE:-unknown}"
  exit 0
fi

if [[ "${MARKET_STATE}" != "Open" ]]; then
  log "SKIP: market_closed_or_clock_unavailable state=${MARKET_STATE:-unknown}"
  exit 0
fi

if [[ ! -f "${FORMATTER}" ]]; then
  log "ERROR: status_formatter_missing path=${FORMATTER}"
  exit 0
fi

OUT="${TMPDIR}/as.out"
ERR="${TMPDIR}/as.err"
: >"${OUT}"
: >"${ERR}"

log "Building cache-only technical trend context"
if ! "${PYTHON_BIN}" "${FORMATTER}" >"${OUT}" 2>"${ERR}"; then
  log "ERROR: format_status failed: $(tr '\n' '|' <"${ERR}")"
  exit 0
fi

if [[ ! -s "${OUT}" ]]; then
  log "ERROR: empty status output"
  exit 0
fi

STATUS_RAW="$(cat "${OUT}")"
if [[ -z "${STATUS_RAW}" ]]; then
  log "ERROR: empty status output"
  exit 0
fi

if [[ "${AUTOSTATUS_DRY_RUN:-0}" = "1" ]]; then
  printf '%s\n' "${STATUS_RAW}"
  log "DRY_RUN: status rendered; Telegram not called"
  exit 0
fi

if [[ -f "${TELE}" ]]; then
  # shellcheck disable=SC1090
  source "${TELE}"
else
  log "ERROR: tele.env missing"
  exit 0
fi

if [[ -z "${TELEGRAM_BOT_TOKEN:-}" || -z "${TELEGRAM_CHAT_ID:-}" ]]; then
  log "ERROR: TELEGRAM_* vars missing"
  exit 0
fi

if ! command -v "${CURL_BIN}" >/dev/null 2>&1; then
  log "ERROR: curl unavailable command=${CURL_BIN}"
  exit 0
fi

API="https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage"
RESP="$(
  "${CURL_BIN}" -sS \
    --connect-timeout 10 \
    --max-time 20 \
    -w $'\nHTTP_STATUS:%{http_code}\n' \
    -X POST "${API}" \
    -d "chat_id=${TELEGRAM_CHAT_ID}" \
    -d "disable_web_page_preview=true" \
    --data-urlencode "text=${STATUS_RAW}" \
    || true
)"

HTTP_CODE="$(
  printf '%s' "${RESP}" \
    | sed -n 's/^HTTP_STATUS:\([0-9][0-9][0-9]\)$/\1/p' \
    | tail -n 1
)"
BODY="$(printf '%s' "${RESP}" | sed '/^HTTP_STATUS:[0-9][0-9][0-9]$/d')"

if printf '%s' "${BODY}" | grep -q '"ok":true'; then
  log "sendMessage OK plain_text http=${HTTP_CODE:-unknown}"
else
  log "ERROR: sendMessage failed http=${HTTP_CODE:-unknown} resp=$(printf '%s' "${BODY}" | tr '\n' ' ')"
fi

exit 0
