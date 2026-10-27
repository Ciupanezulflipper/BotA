#!/usr/bin/env bash
# FILE: tools/heartbeat.sh
# ROLE: Run one unified UTC heartbeat, deadman, and recovery cycle.
# Clock-domain adaptation is in tools/heartbeat_boottime.py.
# Unified orchestration remains in tools/heartbeat_runtime.py.
# Transport and retry primitives remain in tools/heartbeat_delivery.py.

set -euo pipefail

CODE_ROOT="${BOTA_CODE_ROOT:-${BOTA_ROOT:-${HOME}/BotA}}"
MUTABLE_ROOT="${BOTA_MUTABLE_ROOT:-${CODE_ROOT}}"
ROOT="${CODE_ROOT}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
CONTROLLER="${ROOT}/tools/heartbeat_boottime.py"
LOG_PATH="${MUTABLE_ROOT}/logs/cron.heartbeat.log"

if [[ "${BOTA_PATH_CONTRACT_CHECK:-0}" == 1 ]]; then
  printf 'CODE_ROOT=%s\nMUTABLE_ROOT=%s\nCONTROLLER=%s\nLOGS=%s\nSTATE=%s\nLOCK=%s\n' \
    "${CODE_ROOT}" "${MUTABLE_ROOT}" "${CONTROLLER}" \
    "${MUTABLE_ROOT}/logs" "${MUTABLE_ROOT}/state" \
    "${MUTABLE_ROOT}/state/heartbeat_delivery.lock"
  exit 0
fi

mkdir -p "${MUTABLE_ROOT}/logs"

log() {
  printf '[%s] %s\n' "$(date -u +'%Y-%m-%d %H:%M:%S UTC')" "$*" \
    >>"${LOG_PATH}"
}

if [[ ! -f "${CONTROLLER}" ]]; then
  log "heartbeat clock controller missing: ${CONTROLLER}"
  exit 0
fi

CONTROLLER_RC=0
"${PYTHON_BIN}" "${CONTROLLER}" --root "${MUTABLE_ROOT}" || CONTROLLER_RC=$?
if [[ "${CONTROLLER_RC}" -ne 0 ]]; then
  log "heartbeat clock controller failed: exit_code=${CONTROLLER_RC}"
fi

exit 0
