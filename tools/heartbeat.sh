#!/data/data/com.termux/files/usr/bin/bash
# FILE: tools/heartbeat.sh
# ROLE: Run one unified UTC heartbeat, deadman, and recovery cycle.
# Transport and retry primitives remain in tools/heartbeat_delivery.py.

set -euo pipefail

ROOT="${BOTA_ROOT:-${HOME}/BotA}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
CONTROLLER="${ROOT}/tools/heartbeat_runtime.py"
LOG_PATH="${ROOT}/logs/cron.heartbeat.log"

mkdir -p "${ROOT}/logs"

log() {
  printf '[%s] %s\n' "$(date -u +'%Y-%m-%d %H:%M:%S UTC')" "$*" \
    >>"${LOG_PATH}"
}

if [[ ! -f "${CONTROLLER}" ]]; then
  log "heartbeat runtime controller missing: ${CONTROLLER}"
  exit 0
fi

CONTROLLER_RC=0
"${PYTHON_BIN}" "${CONTROLLER}" --root "${ROOT}" || CONTROLLER_RC=$?
if [[ "${CONTROLLER_RC}" -ne 0 ]]; then
  log "heartbeat runtime controller failed: exit_code=${CONTROLLER_RC}"
fi

exit 0
