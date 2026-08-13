#!/data/data/com.termux/files/usr/bin/bash
# Canonical BotA watcher Telegram sender.
# - Prove exactly one matching current-cycle decision before network access.
# - Delegate Telegram network/state semantics through telegram_delivery_boundary.py.
# - Defer legacy cooldown/hash commit until the outer GREEN transaction proves
#   Supabase success.
# - rc=76 means an earlier authoritative send was reconciled; it is success for
#   the legacy caller, while chart_generator.py suppresses the duplicate chart.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ $# -lt 1 ]]; then
  printf '%s\n' "[telegram_send] message argument required" >&2
  exit 64
fi
python3 "${SCRIPT_DIR}/telegram_send_guard.py" --message "$*"
rc=0
python3 "${SCRIPT_DIR}/telegram_delivery_boundary.py" --message "$*" || rc=$?
if [[ "${rc}" -eq 76 ]]; then
  printf '%s\n' "[telegram_send] reconciled prior authoritative send" >&2
  exit 0
fi
exit "${rc}"
