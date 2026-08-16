#!/data/data/com.termux/files/usr/bin/bash
# Canonical watcher boundary. The historical watcher implementation is preserved
# in signal_watcher_core.sh; this wrapper enforces the crash-consistent
# cycle/delivery context required by the evidence layer.
set -euo pipefail
ROOT="${BOTA_ROOT:-${HOME}/BotA}"
TOOLS="${ROOT}/tools"
CORE="${TOOLS}/signal_watcher_core.sh"
SENDER="${TOOLS}/telegram_send.sh"
RECOVERY="${TOOLS}/watcher_pending_delivery_recovery.py"

if [[ "${1:-}" = "--help" || "${1:-}" = "-h" ]]; then
  exec bash "${CORE}" "$@"
fi

required=(
  BOTA_CYCLE_ID
  BOTA_ALERTS_OFFSET
  BOTA_TELEGRAM_RESULT_LOG
  BOTA_SUPABASE_RESULT_LOG
  BOTA_DELIVERY_STATE_DIR
)
for name in "${required[@]}"; do
  if [[ -z "${!name:-}" ]]; then
    printf '[WATCHER_BOUNDARY] missing_required_context=%s -> fail_closed\n' "${name}" >&2
    exit 64
  fi
done

if [[ ! -f "${CORE}" ]]; then
  printf '[WATCHER_BOUNDARY] core_missing=%s -> fail_closed\n' "${CORE}" >&2
  exit 66
fi
if [[ ! -f "${SENDER}" ]]; then
  printf '[WATCHER_BOUNDARY] canonical_sender_missing=%s -> fail_closed\n' "${SENDER}" >&2
  exit 66
fi
if [[ ! -f "${RECOVERY}" ]]; then
  printf '[WATCHER_BOUNDARY] pending_recovery_missing=%s -> fail_closed\n' "${RECOVERY}" >&2
  exit 66
fi

# The legacy core uses STATE for cooldown/hash files while the canonical sender
# uses BOTA_DELIVERY_STATE_DIR. They must be one namespace or dedup/cooldown can
# diverge and suppress retries incorrectly.
if [[ -n "${STATE:-}" && "${STATE}" != "${BOTA_DELIVERY_STATE_DIR}" ]]; then
  printf '[WATCHER_BOUNDARY] state_dir_mismatch state=%s delivery=%s -> fail_closed\n' \
    "${STATE}" "${BOTA_DELIVERY_STATE_DIR}" >&2
  exit 64
fi
export STATE="${BOTA_DELIVERY_STATE_DIR}"

# GitHub's contents API does not preserve executable mode for newly created
# files. Repair only this reviewed sender's owner-only execute metadata when
# needed; never mutate its bytes. If permission repair fails, do not allow the
# historical core to fall through to its inline urllib sender.
if [[ ! -x "${SENDER}" ]]; then
  if ! chmod 700 "${SENDER}"; then
    printf '[WATCHER_BOUNDARY] canonical_sender_chmod_failed=%s -> fail_closed\n' \
      "${SENDER}" >&2
    exit 66
  fi
fi
if [[ ! -x "${SENDER}" ]]; then
  printf '[WATCHER_BOUNDARY] canonical_sender_not_executable=%s -> fail_closed\n' \
    "${SENDER}" >&2
  exit 66
fi

# A confirmed Telegram send whose legacy hash is not yet committed represents
# an incomplete Telegram->Supabase transaction. Clear only its stale cooldown so
# the next cycle reaches the canonical sender, reconciles without resending the
# text, retries Supabase, and commits cooldown/hash only after success.
if ! python3 "${RECOVERY}"; then
  printf '[WATCHER_BOUNDARY] pending_delivery_recovery_failed -> fail_closed\n' >&2
  exit 68
fi

# The legacy watcher labels every nonzero sender result as a "network failure",
# including local evidence failures and crash reconciliation. Under the canonical
# structured-delivery boundary that cross-signal backoff is semantically invalid.
# Disable only that legacy suppression mechanism; exact per-delivery state,
# UNKNOWN_OUTCOME handling, and cycle health remain fail-closed.
export NETWORK_FAIL_MAX=2147483647
export BOTA_CANONICAL_WATCHER_BOUNDARY=1
exec bash "${CORE}" "$@"
