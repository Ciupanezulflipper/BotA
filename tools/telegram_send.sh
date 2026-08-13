#!/data/data/com.termux/files/usr/bin/bash
# Canonical BotA watcher Telegram sender.
# All network delivery semantics live in telegram_delivery.py.
# A previously confirmed delivery (rc=76) is a successful reconciliation, not
# a new network failure. Normalize only that outcome to success; all other
# return codes remain unchanged and fail closed.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ $# -lt 1 ]]; then
  printf '%s\n' "[telegram_send] message argument required" >&2
  exit 64
fi
rc=0
python3 "${SCRIPT_DIR}/telegram_delivery.py" --message "$*" || rc=$?
if [[ "${rc}" -eq 76 ]]; then
  printf '%s\n' "[telegram_send] reconciled prior authoritative send" >&2
  exit 0
fi
exit "${rc}"
