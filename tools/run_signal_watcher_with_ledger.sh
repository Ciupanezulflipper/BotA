#!/data/data/com.termux/files/usr/bin/bash
# Run one watcher scan and reconcile only evidence appended by that scan.
set -euo pipefail

ROOT="${BOTA_ROOT:-${HOME}/BotA}"
TOOLS="${ROOT}/tools"
LOGS="${ROOT}/logs"
STATE="${ROOT}/state"
mkdir -p "${LOGS}" "${STATE}"

alerts="${LOGS}/alerts.csv"
watcher_log="${LOGS}/cron.signals.log"
alerts_offset="$(stat -c '%s' "${alerts}" 2>/dev/null || echo 0)"
log_offset="$(stat -c '%s' "${watcher_log}" 2>/dev/null || echo 0)"
boot="$({ cat /proc/sys/kernel/random/boot_id 2>/dev/null || echo unknown; } | tr -d '\n')"
mono="$({ python3 -c 'import time; c=getattr(time,"CLOCK_BOOTTIME",None); print(time.clock_gettime_ns(c) if c is not None else time.monotonic_ns())' 2>/dev/null || echo 0; })"
cycle_id="${boot}:${mono}"
server_epoch="${BOTA_SERVER_EPOCH:-0}"

python3 "${TOOLS}/pipeline_ledger.py" component \
  --component watcher \
  --status started \
  --cycle-id "${cycle_id}" \
  --server-epoch "${server_epoch}" \
  >/dev/null 2>>"${LOGS}/error.log" || true

watcher_rc=0
bash "${TOOLS}/signal_watcher_pro.sh" --once || watcher_rc=$?

reconcile_rc=0
python3 "${TOOLS}/watcher_cycle_ledger.py" \
  --cycle-id "${cycle_id}" \
  --alerts-offset "${alerts_offset}" \
  --log-offset "${log_offset}" \
  --server-epoch "${BOTA_SERVER_EPOCH:-${server_epoch}}" \
  || reconcile_rc=$?

if (( watcher_rc != 0 )); then
  python3 "${TOOLS}/pipeline_ledger.py" component \
    --component watcher \
    --status failed \
    --cycle-id "${cycle_id}" \
    --details "watcher_exit_code=${watcher_rc};reconcile_exit_code=${reconcile_rc}" \
    --server-epoch "${BOTA_SERVER_EPOCH:-${server_epoch}}" \
    >/dev/null 2>>"${LOGS}/error.log" || true
  exit "${watcher_rc}"
fi

exit "${reconcile_rc}"
