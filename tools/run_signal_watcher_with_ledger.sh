#!/data/data/com.termux/files/usr/bin/bash
# Run one watcher scan and reconcile only evidence produced by that scan.
#
# If BOTA_CYCLE_ID is supplied by a parent orchestrator, this runner MUST reuse
# that exact cycle identity. When called standalone, it creates its own cycle
# identity and retains the legacy component-start/failure bookkeeping.
#
# Failed/interrupted cycles retain their bounded evidence files in state/ for
# post-crash forensics. Successful cycles remove them explicitly at the end.

set -euo pipefail

ROOT="${BOTA_ROOT:-${HOME}/BotA}"
DEPLOY_MARKER="${ROOT}/state/runtime_deploy_in_progress.json"
# Generation barrier must precede every filesystem/runtime/network side effect.
# -e is false for a dangling symlink, so -L is required as well. Never follow
# or read the marker: its mere presence means the runtime generation is
# ambiguous and trading work must fail closed until deployment/rollback clears it.
if [[ -e "${DEPLOY_MARKER}" || -L "${DEPLOY_MARKER}" ]]; then
  printf '[WATCHER_EVIDENCE] deployment_generation_barrier_active marker=%s\n' \
    "${DEPLOY_MARKER}" >&2
  exit 78
fi

TOOLS="${ROOT}/tools"
LOGS="${ROOT}/logs"
EVIDENCE_STATE="${ROOT}/state"
WATCHER_STATE_RAW="${BOTA_WATCHER_STATE:-logs/state}"
if [[ "${WATCHER_STATE_RAW}" = /* ]]; then
  DELIVERY_STATE="${WATCHER_STATE_RAW}"
else
  DELIVERY_STATE="${ROOT}/${WATCHER_STATE_RAW}"
fi
# One explicit watcher-state contract. Do not inherit an ambient generic STATE
# value from cron/runit/interactive shells. The signal watcher receives this
# exact path too, so its legacy cooldown/hash files and the canonical sender
# always operate on the same state directory.
export BOTA_WATCHER_STATE="${DELIVERY_STATE}"
export STATE="${DELIVERY_STATE}"

mkdir -p "${LOGS}" "${EVIDENCE_STATE}" "${DELIVERY_STATE}"

# telegram_send.sh is the only authorized watcher Telegram transport. Runtime
# code must not mutate deployment-tree permissions on every cycle; deployment
# is responsible for installing this file executable. Missing/non-executable is
# therefore a clear fail-closed configuration error.
if [[ ! -f "${TOOLS}/telegram_send.sh" ]]; then
  printf '[WATCHER_EVIDENCE] canonical telegram sender missing: %s\n' \
    "${TOOLS}/telegram_send.sh" >&2
  exit 66
fi
if [[ ! -x "${TOOLS}/telegram_send.sh" ]]; then
  printf '[WATCHER_EVIDENCE] canonical telegram sender not executable: %s\n' \
    "${TOOLS}/telegram_send.sh" >&2
  exit 66
fi

alerts="${LOGS}/alerts.csv"
alerts_offset="$(stat -c '%s' "${alerts}" 2>/dev/null || echo 0)"
# Bind any external Telegram side effect to rows appended after this exact
# cycle boundary. The sender fails closed if this offset is absent/invalid.
export BOTA_ALERTS_OFFSET="${alerts_offset}"
export BOTA_DELIVERY_STATE_DIR="${DELIVERY_STATE}"
cycle_log="$(mktemp "${EVIDENCE_STATE}/watcher_cycle.XXXXXX.log")"
telegram_result_log="$(mktemp "${EVIDENCE_STATE}/watcher_telegram.XXXXXX.jsonl")"
supabase_result_log="$(mktemp "${EVIDENCE_STATE}/watcher_supabase.XXXXXX.jsonl")"

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
export BOTA_TELEGRAM_RESULT_LOG="${telegram_result_log}"
export BOTA_SUPABASE_RESULT_LOG="${supabase_result_log}"

if (( owns_cycle == 1 )); then
  python3 "${TOOLS}/pipeline_ledger.py" component \
    --component watcher --status started --cycle-id "${cycle_id}" \
    --server-epoch "${server_epoch}" \
    >/dev/null 2>>"${LOGS}/error.log" || true
fi

watcher_rc=0
bash "${TOOLS}/signal_watcher_pro.sh" --once 2>"${cycle_log}" || watcher_rc=$?

# The watcher historically swallowed alerts.csv append failures. Enforce a
# cycle-level persistence postcondition before health can be green. Capture the
# verifier output first; never read and append the same cycle log concurrently.
persistence_rc=0
persistence_output="$({
  python3 "${TOOLS}/watcher_persistence_gate.py" \
    --alerts-path "${alerts}" \
    --alerts-offset "${alerts_offset}" \
    --log-path "${cycle_log}"
} 2>&1)" || persistence_rc=$?
if [[ -n "${persistence_output}" ]]; then
  printf '%s\n' "${persistence_output}" >>"${cycle_log}"
fi

reconcile_rc=0
python3 "${TOOLS}/watcher_cycle_ledger.py" \
  --cycle-id "${cycle_id}" \
  --alerts-offset "${alerts_offset}" \
  --log-path "${cycle_log}" \
  --log-offset 0 \
  --telegram-result-path "${telegram_result_log}" \
  --supabase-result-path "${supabase_result_log}" \
  --server-epoch "${BOTA_SERVER_EPOCH:-${server_epoch}}" \
  || reconcile_rc=$?

# Preserve the outward stderr contract so the parent gated cycle sees the exact
# watcher evidence that the reconciler just classified.
cat "${cycle_log}" >&2 || true

final_rc=0
if (( watcher_rc != 0 )); then
  final_rc="${watcher_rc}"
elif (( persistence_rc != 0 )); then
  final_rc="${persistence_rc}"
elif (( reconcile_rc != 0 )); then
  final_rc="${reconcile_rc}"
fi

if (( final_rc != 0 )); then
  printf '[WATCHER_EVIDENCE] retained cycle_log=%s telegram_log=%s supabase_log=%s\n' \
    "${cycle_log}" "${telegram_result_log}" "${supabase_result_log}" >&2
  if (( owns_cycle == 1 )); then
    python3 "${TOOLS}/pipeline_ledger.py" component \
      --component watcher --status failed --cycle-id "${cycle_id}" \
      --details "watcher_exit_code=${watcher_rc};persistence_exit_code=${persistence_rc};reconcile_exit_code=${reconcile_rc}" \
      --server-epoch "${BOTA_SERVER_EPOCH:-${server_epoch}}" \
      >/dev/null 2>>"${LOGS}/error.log" || true
  fi
  exit "${final_rc}"
fi

# Success-only cleanup. Interrupted/failed cycles deliberately retain evidence.
rm -f "${cycle_log}" "${telegram_result_log}" "${supabase_result_log}"
exit 0
