#!/data/data/com.termux/files/usr/bin/bash
# FILE: tools/watcher_gated_cycle.sh
# DESC: One gated watcher cycle that emits EXACTLY ONE terminal outcome to the
#       pipeline ledger, drawn from the Monday-readiness enum:
#
#         MARKET_CLOSED
#         CLOCK_GATE_FAILED
#         DATA_FETCH_FAILED
#         DATA_STALE
#         EVALUATED_REJECTED
#         EVALUATED_ACCEPTED
#         DEDUP_SUPPRESSED_DELIVERY
#         DELIVERY_ATTEMPTED
#         INTERNAL_ERROR
#
# This is the new top-level entry that a runit service (or cron) should invoke
# in place of directly calling signal_watcher_pro.sh. It:
#
#   1. Consults tools/market_open.sh (server-clock gate) and records the reason
#      code exposed via MARKET_OPEN_REASON_FILE.
#   2. Emits MARKET_CLOSED (when the gate correctly identified a closed session)
#      or CLOCK_GATE_FAILED (when the gate could not determine the time) and
#      exits early without running the watcher.
#   3. When the gate is Open, delegates the scan to
#      tools/run_signal_watcher_with_ledger.sh (which reconciles per-pair
#      decision events into the ledger). This script then aggregates those
#      per-cycle results into ONE component-level terminal outcome:
#        - EVALUATED_ACCEPTED, DELIVERY_ATTEMPTED, or DEDUP_SUPPRESSED_DELIVERY
#          when at least one pair produced an accepted decision.
#        - EVALUATED_REJECTED when all evaluated pairs were rejected by filters.
#        - DATA_STALE / DATA_FETCH_FAILED when the reconciler surfaced those
#          codes.
#        - INTERNAL_ERROR on unexpected non-zero exit paths.
#
# The script itself never sends Telegram messages or writes to Supabase — it
# only observes and records what the watcher pipeline reported.
#
# Environment:
#   BOTA_ROOT                 : BotA root override (default ${HOME}/BotA)
#   WATCHER_GATED_DRY_RUN     : when "1", do not execute the inner watcher.
#                                Useful for CI harnesses and the
#                                monday_readiness_check.py fixture harness.
#   WATCHER_GATED_MARKET_HINT : override for the fixture harness. When set,
#                                the gate is not consulted at runtime — the
#                                supplied reason code is used verbatim.
#
# Exit code: 0 on healthy cycle (terminal outcome recorded), nonzero on any
# internal failure that prevented recording a terminal outcome.

set -uo pipefail

ROOT="${BOTA_ROOT:-${HOME}/BotA}"
TOOLS="${ROOT}/tools"
LOGS="${ROOT}/logs"
STATE="${ROOT}/state"
mkdir -p "${LOGS}" "${STATE}"

COMPONENT="watcher"
ERROR_LOG="${LOGS}/error.log"

boot_id_value() {
  { cat /proc/sys/kernel/random/boot_id 2>/dev/null || echo unknown; } | tr -d '\n'
}

monotonic_ns_value() {
  python3 - <<'PY' 2>/dev/null || echo 0
import time
clock = getattr(time, "CLOCK_BOOTTIME", None)
print(time.clock_gettime_ns(clock) if clock is not None else time.monotonic_ns())
PY
}

CYCLE_ID="$(boot_id_value):$(monotonic_ns_value)"

record_terminal() {
  local status="$1"
  local outcome="$2"
  local details="$3"
  local market_reason="$4"
  local server_epoch="${BOTA_SERVER_EPOCH:-0}"
  python3 "${TOOLS}/pipeline_ledger.py" component \
    --component "${COMPONENT}" \
    --status "${status}" \
    --cycle-id "${CYCLE_ID}" \
    --details "${details}" \
    --terminal-outcome "${outcome}" \
    --market-reason "${market_reason}" \
    --server-epoch "${server_epoch}" \
    >/dev/null 2>>"${ERROR_LOG}" || return $?
}

record_started() {
  local server_epoch="${BOTA_SERVER_EPOCH:-0}"
  python3 "${TOOLS}/pipeline_ledger.py" component \
    --component "${COMPONENT}" \
    --status started \
    --cycle-id "${CYCLE_ID}" \
    --server-epoch "${server_epoch}" \
    >/dev/null 2>>"${ERROR_LOG}" || true
}

# Alerts.csv is the persisted decision journal. Reading its size BEFORE running
# the watcher lets us tell "watcher persisted a new decision row" apart from
# "watcher exited before persisting anything". This is used to promote
# ambiguous EVALUATED_* outcomes when appropriate.
alerts_before_size() {
  stat -c '%s' "${LOGS}/alerts.csv" 2>/dev/null || echo 0
}

log_before_size() {
  stat -c '%s' "${LOGS}/cron.signals.log" 2>/dev/null || echo 0
}

record_started

# --- Gate check ------------------------------------------------------------
reason_file="$(mktemp -t market_reason.XXXXXX)"
epoch_file="$(mktemp -t market_epoch.XXXXXX)"
trap 'rm -f "${reason_file}" "${epoch_file}"' EXIT

gate_rc=0
if [[ -n "${WATCHER_GATED_MARKET_HINT:-}" ]]; then
  printf '%s\n' "${WATCHER_GATED_MARKET_HINT}" >"${reason_file}"
  case "${WATCHER_GATED_MARKET_HINT}" in
    MARKET_OPEN) gate_rc=0 ;;
    *)           gate_rc=1 ;;
  esac
else
  MARKET_OPEN_REASON_FILE="${reason_file}" \
    BOTA_SERVER_EPOCH_FILE="${epoch_file}" \
    bash "${TOOLS}/market_open.sh" >/dev/null 2>>"${ERROR_LOG}" || gate_rc=$?
fi

reason="$(head -n1 "${reason_file}" 2>/dev/null || true)"
reason="${reason//$'\r'/}"
reason="${reason:-MARKET_GATE_ERROR}"

if [[ -s "${epoch_file}" && -z "${BOTA_SERVER_EPOCH:-}" ]]; then
  probed_epoch="$(head -n1 "${epoch_file}" | tr -d '[:space:]')"
  if [[ "${probed_epoch}" =~ ^[0-9]+$ && "${probed_epoch}" -gt 1000000000 ]]; then
    export BOTA_SERVER_EPOCH="${probed_epoch}"
  fi
fi

if [[ "${reason}" = "MARKET_OPEN" ]]; then
  :  # fall through to watcher
else
  case "${reason}" in
    MARKET_CLOSED_*)
      record_terminal "skipped_market_closed" "MARKET_CLOSED" \
        "gate_reason=${reason}" "${reason}" || true
      exit 0
      ;;
    CLOCK_UNAVAILABLE|MARKET_GATE_ERROR|*)
      record_terminal "failed" "CLOCK_GATE_FAILED" \
        "gate_reason=${reason};gate_rc=${gate_rc}" "${reason}" || true
      exit 0
      ;;
  esac
fi

# --- Watcher execution ------------------------------------------------------
if [[ "${WATCHER_GATED_DRY_RUN:-0}" = "1" ]]; then
  record_terminal "completed" "EVALUATED_REJECTED" \
    "dry_run=1" "${reason}" || true
  exit 0
fi

alerts_before="$(alerts_before_size)"
log_before="$(log_before_size)"

inner_rc=0
inner_stderr="$(mktemp -t watcher_gated.XXXXXX)"
trap 'rm -f "${reason_file}" "${epoch_file}" "${inner_stderr}"' EXIT

bash "${TOOLS}/run_signal_watcher_with_ledger.sh" 2>"${inner_stderr}" >/dev/null || inner_rc=$?

alerts_after="$(alerts_before_size)"
log_after="$(log_before_size)"
alerts_grew=0
[[ "${alerts_after}" -gt "${alerts_before}" ]] && alerts_grew=1
log_grew=0
[[ "${log_after}" -gt "${log_before}" ]] && log_grew=1

# Aggregate the per-pair decisions written by the reconciler for THIS cycle
# into one component-level terminal outcome.
aggregate="$(BOTA_ROOT="${ROOT}" CYCLE_ID="${CYCLE_ID}" python3 - <<'PY' 2>/dev/null
import json, os, pathlib

root = os.environ.get("BOTA_ROOT", "").strip() or str(pathlib.Path.home() / "BotA")
cycle_id = os.environ.get("CYCLE_ID", "")
path = pathlib.Path(root) / "state" / "pipeline_progress.json"

try:
    state = json.loads(path.read_text(encoding="utf-8"))
except Exception:
    print("INTERNAL_ERROR"); raise SystemExit(0)

decisions = state.get("decisions") if isinstance(state, dict) else None
if not isinstance(decisions, dict):
    print("INTERNAL_ERROR"); raise SystemExit(0)

cycle_events = [
    event for event in decisions.values()
    if isinstance(event, dict) and str(event.get("cycle_id") or "") == cycle_id
]

if not cycle_events:
    # Reconciler ran but produced no per-pair events for this cycle.
    print("DATA_FETCH_FAILED"); raise SystemExit(0)

def has_outcome(events, needles):
    for event in events:
        outcome = str(event.get("outcome") or "").lower()
        if any(needle in outcome for needle in needles):
            return True
    return False

def any_persisted_accept(events):
    for event in events:
        if event.get("alerts_csv_persisted") and not event.get("filter_rejected"):
            return True
    return False

if has_outcome(cycle_events, ("telegram_sent",)):
    print("DELIVERY_ATTEMPTED"); raise SystemExit(0)

if has_outcome(cycle_events, ("telegram_failed",)):
    print("DELIVERY_ATTEMPTED"); raise SystemExit(0)

if has_outcome(cycle_events, ("delivery_dedup",)):
    print("DEDUP_SUPPRESSED_DELIVERY"); raise SystemExit(0)

if has_outcome(cycle_events, ("telegram_score_gate", "telegram_tier_gate", "telegram_cooldown")):
    print("EVALUATED_ACCEPTED"); raise SystemExit(0)

if any_persisted_accept(cycle_events):
    print("EVALUATED_ACCEPTED"); raise SystemExit(0)

if has_outcome(cycle_events, ("raw_cache_invalid",)):
    print("DATA_FETCH_FAILED"); raise SystemExit(0)

if has_outcome(cycle_events, ("candle_stale",)):
    print("DATA_STALE"); raise SystemExit(0)

if has_outcome(cycle_events, ("news_gate", "calendar_gate", "pause_guard",
                             "filter_rejected", "parse_error")):
    print("EVALUATED_REJECTED"); raise SystemExit(0)

# Reconciler produced events but no recognized terminal outcome for the cycle.
print("INTERNAL_ERROR")
PY
)"

aggregate="${aggregate:-INTERNAL_ERROR}"
inner_tail="$(tail -c 400 "${inner_stderr}" 2>/dev/null | tr -d '\r' | tr '\n' ' ' || true)"

if (( inner_rc != 0 )) && [[ "${aggregate}" = "INTERNAL_ERROR" ]]; then
  record_terminal "failed" "INTERNAL_ERROR" \
    "run_rc=${inner_rc};alerts_grew=${alerts_grew};log_grew=${log_grew};stderr_tail=${inner_tail}" \
    "${reason}" || true
  exit 0
fi

status_for_ledger="completed"
if [[ "${aggregate}" = "INTERNAL_ERROR" || "${aggregate}" = "DATA_FETCH_FAILED" ]]; then
  status_for_ledger="failed"
fi

record_terminal "${status_for_ledger}" "${aggregate}" \
  "run_rc=${inner_rc};alerts_grew=${alerts_grew};log_grew=${log_grew}" \
  "${reason}" || true

exit 0
