#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

ROOT="${HOME}/BotA"
TOOLS="${ROOT}/tools"
LOGS="${ROOT}/logs"
RUNTIME_ERR_LOG="${LOGS}/shadow_runtime.stderr.log"
DEPENDENCY_CHECK="${TOOLS}/runtime_dependency_check.py"
cd "${ROOT}"

mkdir -p "${LOGS}"

if [[ -f "${ROOT}/.env.runtime" ]]; then
  set -a
  # shellcheck disable=SC1090
  . "${ROOT}/.env.runtime"
  set +a
fi

if [[ -f "${ROOT}/config/strategy.env" ]]; then
  set -a
  # shellcheck disable=SC1090
  . "${ROOT}/config/strategy.env"
  set +a
fi

cycle_id="$({ cat /proc/sys/kernel/random/boot_id 2>/dev/null || echo unknown; } | tr -d '\n'):$({ python3 -c 'import time; c=getattr(time,"CLOCK_BOOTTIME",None); print(time.clock_gettime_ns(c) if c is not None else time.monotonic_ns())' 2>/dev/null || echo 0; })"

ledger() {
  local status="$1" details="${2:-}"
  python3 "${TOOLS}/pipeline_ledger.py" component \
    --component shadow \
    --status "${status}" \
    --cycle-id "${cycle_id}" \
    --details "${details}" \
    >/dev/null 2>>"${LOGS}/error.log" || true
}

runtime_error() {
  local message="$1"
  printf '[SHADOW_RUNTIME %s] %s\n' \
    "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "${message}" >>"${RUNTIME_ERR_LOG}"
}

ledger started

if dependency_output="$(python3 "${DEPENDENCY_CHECK}" 2>&1)"; then
  :
else
  rc=$?
  runtime_error "dependency_check_failed rc=${rc}"
  printf '%s\n' "${dependency_output}" >>"${RUNTIME_ERR_LOG}"
  ledger failed "dependency_check_exit_code=${rc}"
  exit "${rc}"
fi

rc=0
python3 "${TOOLS}/be_shadow_manager.py" 2>>"${RUNTIME_ERR_LOG}" || rc=$?

if (( rc == 0 )); then
  ledger completed "exit_code=0"
else
  runtime_error "be_shadow_manager_exit rc=${rc}"
  ledger failed "exit_code=${rc}"
fi

exit "${rc}"
