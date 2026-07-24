#!/data/data/com.termux/files/usr/bin/bash
# Start the native Termux service-daemon watchdog detached from the shell.
set -euo pipefail

ROOT="${BOTA_ROOT:-${HOME}/BotA}"
PYTHON="${PREFIX}/bin/python3"
WATCHDOG="${ROOT}/tools/native_service_daemon_watchdog.py"
LOG="${ROOT}/logs/native_service_daemon_watchdog.launch.log"

mkdir -p "${ROOT}/logs" "${ROOT}/state"
[ -x "${PYTHON}" ] || { echo "NATIVE_WATCHDOG_START=PYTHON_MISSING"; exit 1; }
[ -f "${WATCHDOG}" ] || { echo "NATIVE_WATCHDOG_START=FILE_MISSING"; exit 1; }

termux-wake-lock >/dev/null 2>&1 || true
if command -v setsid >/dev/null 2>&1; then
    nohup setsid "${PYTHON}" "${WATCHDOG}" </dev/null >>"${LOG}" 2>&1 &
else
    nohup "${PYTHON}" "${WATCHDOG}" </dev/null >>"${LOG}" 2>&1 &
fi

echo "NATIVE_WATCHDOG_START=REQUESTED"
