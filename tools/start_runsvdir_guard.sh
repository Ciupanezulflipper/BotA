#!/data/data/com.termux/files/usr/bin/bash
# Start the durable runsvdir guard detached from the current Termux session.
set -euo pipefail

ROOT="${BOTA_ROOT:-${HOME}/BotA}"
PYTHON="${PREFIX}/bin/python3"
GUARD="${ROOT}/tools/runsvdir_guard.py"
LAUNCH_LOG="${ROOT}/logs/runsvdir_guard.launch.log"

mkdir -p "${ROOT}/logs" "${ROOT}/state"

[ -x "${PYTHON}" ] || {
    echo "RUNSVDIR_GUARD_START=ABORTED_PYTHON_MISSING"
    exit 1
}

[ -f "${GUARD}" ] || {
    echo "RUNSVDIR_GUARD_START=ABORTED_GUARD_MISSING"
    exit 1
}

termux-wake-lock >/dev/null 2>&1 || true

if command -v setsid >/dev/null 2>&1; then
    nohup setsid "${PYTHON}" "${GUARD}" \
        </dev/null >>"${LAUNCH_LOG}" 2>&1 &
else
    nohup "${PYTHON}" "${GUARD}" \
        </dev/null >>"${LAUNCH_LOG}" 2>&1 &
fi

echo "RUNSVDIR_GUARD_START=REQUESTED"
# END
