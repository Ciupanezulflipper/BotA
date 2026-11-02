#!/data/data/com.termux/files/usr/bin/bash
# FILE: tools/autostatus.sh
# ROLE: Refresh cache-only technical context locally during the FX session.
# POLICY: This scheduled context is informational and must never send Telegram.

set -euo pipefail

CODE_ROOT="${BOTA_CODE_ROOT:-${BOTA_ROOT:-${HOME}/BotA}}"
MUTABLE_ROOT="${BOTA_MUTABLE_ROOT:-${CODE_ROOT}}"
TMPDIR="${MUTABLE_ROOT}/tmp"
LOGDIR="${MUTABLE_ROOT}/logs"
MARKET_GATE="${BOTA_MARKET_GATE:-${CODE_ROOT}/tools/market_open.sh}"
FORMATTER="${BOTA_STATUS_FORMATTER:-${CODE_ROOT}/tools/format_status.py}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
LATEST="${LOGDIR}/technical_context.latest.txt"

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
if MARKET_STATE="$("${MARKET_GATE}" 2>>"${LOGDIR}/cron.autostatus.log")"; then
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

if ! WORKDIR="$(mktemp -d "${TMPDIR}/autostatus.XXXXXX")"; then
  log "ERROR: temporary_workspace_creation_failed"
  exit 0
fi

OUT="${WORKDIR}/status.out"
ERR="${WORKDIR}/status.err"
LATEST_TMP="${WORKDIR}/technical_context.latest.txt"
trap 'rm -f -- "${OUT}" "${ERR}" "${LATEST_TMP}"; rmdir -- "${WORKDIR}" 2>/dev/null || true' EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM

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

if [[ "${AUTOSTATUS_DRY_RUN:-0}" = "1" ]]; then
  cat "${OUT}"
  log "DRY_RUN: status rendered locally; Telegram disabled by policy"
  exit 0
fi

cp "${OUT}" "${LATEST_TMP}"
chmod 600 "${LATEST_TMP}"
mv -f "${LATEST_TMP}" "${LATEST}"

log "TECHNICAL_CONTEXT_RESULT=LOCAL_ONLY path=${LATEST}"
exit 0
