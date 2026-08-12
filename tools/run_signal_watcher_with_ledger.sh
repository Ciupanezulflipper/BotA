#!/data/data/com.termux/files/usr/bin/bash
# Run one watcher scan and reconcile only evidence produced by that scan.
#
# If BOTA_CYCLE_ID is supplied by a parent orchestrator, this runner MUST reuse
# that exact cycle identity. When called standalone, it creates its own cycle
# identity and retains the legacy component-start/failure bookkeeping.

set -euo pipefail

ROOT="${BOTA_ROOT:-${HOME}/BotA}"
TOOLS="${ROOT}/tools"
LOGS="${ROOT}/logs"
STATE="${ROOT}/state"

mkdir -p "${LOGS}" "${STATE}"

alerts="${LOGS}/alerts.csv"
alerts_offset="$(stat -c '%s' "${alerts}" 2>/dev/null || echo 0)"
cycle_log="$(mktemp "${STATE}/watcher_cycle.XXXXXX.log")"
trap 'rm -f "${cycle_log}" 2>/dev/null || true' EXIT

server_epoch="${BOTA_SERVER_EPOCH:-0}"
owns_cycle=0
cycle_id="${BOTA_CYCLE_ID:-}"

if [[ -z "${cycle_id}" ]]; then
  boot="$({ cat /proc/sys/kernel/random/boot_id 2>/dev/null || echo unknown; } | tr -d '\n')"
  mono="$({ python3 -c 'import time; c=getattr(time,"CLOCK_BOOTTIME",None); print(time.clock_gettime_ns(c) if c is not None else time.monotonic_ns())' 2>/dev/null || echo 0; })"
  cycle_id="${boot}:${mono}"
  owns_cycle=1
fi

export BOTA_CYCLE_ID="${cycle_id}"

if (( owns_cycle == 1 )); then
  python3 "${TOOLS}/pipeline_ledger.py" component \
    --component watcher --status started --cycle-id "${cycle_id}" \
    --server-epoch "${server_epoch}" \
    >/dev/null 2>>"${LOGS}/error.log" || true
fi

watcher_rc=0
bash "${TOOLS}/signal_watcher_pro.sh" --once 2>"${cycle_log}" || watcher_rc=$?

reconcile_rc=0
python3 "${TOOLS}/watcher_cycle_ledger.py" \
  --cycle-id "${cycle_id}" \
  --alerts-offset "${alerts_offset}" \
  --log-path "${cycle_log}" \
  --log-offset 0 \
  --server-epoch "${BOTA_SERVER_EPOCH:-${server_epoch}}" \
  || reconcile_rc=$?

# Preserve the existing outward stderr contract so the parent gated cycle sees
# the exact watcher evidence that the reconciler just classified.
cat "${cycle_log}" >&2 || true

if (( watcher_rc != 0 )); then
  if (( owns_cycle == 1 )); then
    python3 "${TOOLS}/pipeline_ledger.py" component \
      --component watcher --status failed --cycle-id "${cycle_id}" \
      --details "watcher_exit_code=${watcher_rc};reconcile_exit_code=${reconcile_rc}" \
      --server-epoch "${BOTA_SERVER_EPOCH:-${server_epoch}}" \
      >/dev/null 2>>"${LOGS}/error.log" || true
  fi
  exit "${watcher_rc}"
fi

exit "${reconcile_rc}"
