#!/data/data/com.termux/files/usr/bin/bash
# Canonical BotA watcher Telegram sender.
# All network delivery semantics live in telegram_delivery.py.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ $# -lt 1 ]]; then
  printf '%s\n' "[telegram_send] message argument required" >&2
  exit 64
fi
exec python3 "${SCRIPT_DIR}/telegram_delivery.py" --message "$*"
