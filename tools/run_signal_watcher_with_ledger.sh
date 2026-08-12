#!/data/data/com.termux/files/usr/bin/bash
# Run one watcher scan and reconcile only evidence produced by that scan.
#
# If BOTA_CYCLE_ID is supplied by a parent orchestrator, this runner MUST reuse
# that exact cycle identity. When called standalone, it creates its own cycle
# identity and retains the legacy component-start/failure bookkeeping.
#
# Failed/interrupted cycles retain their bounded evidence files in state/ for
# post-crash forensics. Successful cycles remove them on exit.

set -euo pipefail

ROOT="${BOTA_ROOT:-${HOME}/BotA}"
TOOLS="${ROOT}/tools"
LOGS="${ROOT}/logs"
EVIDENCE_STATE="${ROOT}/state"
WATCHER_STATE_RAW="${STATE:-}"
if [[ -z "${WATCHER_STATE_RAW}" ]]; then
  DELIVERY_STATE="${ROOT}/logs/state"
elif [[ "${WATCHER_STATE_RAW}" == /* ]]; then
  DELIVERY_STATE="${WATCHER_STATE_RAW}"
else
  DELIVERY_STATE="${ROOT}/${WATCHER_STATE_RAW}"
fi

mkdir -p "${LOGS}" "${EVIDENCE_STATE}" "${DELIVERY_STATE}"

# The watcher selects tools/telegram_send.sh only when it is executable. GitHub
# contents/API deployments may not preserve executable mode, so make that
# requirement explicit at the runtime boundary and fail closed if it cannot be
# established. The sender itself remains version-controlled and testable.
if [[ ! -f "${TOOLS}/telegram_send.sh" ]]; then
  printf '[WATCHER_EVIDENCE] canonical telegram sender missing: %s\n' \
    "${TOOLS}/telegram_send.sh" >&2
  exit 66
fi
if ! chmod 700 "${TOOLS}/telegram_send.sh"; then
  printf '[WATCHER_EVIDENCE] canonical telegram sender chmod failed: %s\n' \
    "${TOOLS}/telegram_send.sh" >&2
  exit 66
fi
if [[ ! -x "${TOOLS}/telegram_send.sh" ]]; then
  printf '[WATCHER_EVIDENCE] canonical telegram sender not executable after chmod: %s\n' \
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
delete_evidence_on_exit=0
trap 'if (( delete_evidence_on_exit == 1 )); then rm -f "${cycle_log}" "${telegram_result_log}" "${supabase_result_log}" 2>/dev/null || true; fi' EXIT

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
# cycle-level persistence postcondition before health can be green.
persistence_rc=0
python3 "${TOOLS}/watcher_persistence_gate.py" \
  --alerts-path "${alerts}" \
  --alerts-offset "${alerts_offset}" \
  --log-path "${cycle_log}" \
  >>"${cycle_log}" 2>&1 || persistence_rc=$?

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

delete_evidence_on_exit=1
exit 0
