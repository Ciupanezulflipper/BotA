#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
ROOT="$(CDPATH= cd -- "${SCRIPT_DIR}/.." && pwd)"
LOG_DIR="${ROOT}/logs"
mkdir -p "${LOG_DIR}"

env_safe_source() {
  local file="$1"
  [[ -f "${file}" ]] || return 0
  eval "$(
    python3 - "${file}" <<'PY'
import re
import shlex
import sys
from pathlib import Path

path = Path(sys.argv[1])
for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
    line = raw.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    if line.startswith("export "):
        line = line[7:].lstrip()
    key, value = line.split("=", 1)
    key = key.strip()
    if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", key):
        continue
    value = value.strip()
    if len(value) >= 2 and ((value[0] == value[-1] == '"') or (value[0] == value[-1] == "'")):
        value = value[1:-1]
    print(f"export {key}={shlex.quote(value)}")
PY
  )"
}

echo "=== DAILY REPLAY AUDIT: env load ==="
env_safe_source "${ROOT}/.env.runtime"
env_safe_source "${ROOT}/.env"
env_safe_source "${ROOT}/config/strategy.env"
env_safe_source "${ROOT}/strategy.env"

echo "=== DAILY REPLAY AUDIT: python ==="
python3 "${ROOT}/tools/daily_replay_audit.py" "$@"
