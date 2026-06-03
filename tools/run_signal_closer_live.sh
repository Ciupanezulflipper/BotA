#!/usr/bin/env bash
# tools/run_signal_closer_live.sh
# BotA signal closer live wrapper.
#
# Purpose:
# - Load only the Supabase env values required by tools/signal_closer.py.
# - Run signal_closer.py in explicit LIVE mode.
# - Keep signal_closer.py safe defaults unchanged.
#
# Safety:
# - No Telegram sends.
# - No strategy changes.
# - Live DB writes only happen when ACTIVE Supabase signals need closing.
# - Max batch is capped by SIGNAL_CLOSER_MAX_BATCH, default 5.
# - --allow-bulk is intentional, protected by --max-batch.

set -u

ROOT="/data/data/com.termux/files/home/BotA"
cd "$ROOT" || exit 1

mkdir -p "$ROOT/logs"

eval "$(
python3 - <<'PY'
from pathlib import Path
import re
import shlex

allowed = {
    "SUPABASE_SERVICE_KEY",
    "SUPABASE_URL",
    "SIGNAL_MAX_AGE_HOURS",
    "SIGNAL_CLOSER_MAX_BATCH",
}

for filename in ("config/strategy.env", ".env", ".env.runtime"):
    p = Path(filename)
    if not p.exists():
        continue

    for raw in p.read_text(errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        if line.startswith("export "):
            line = line[len("export "):].strip()

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()

        if key not in allowed:
            continue

        if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", key):
            continue

        if (
            (value.startswith('"') and value.endswith('"')) or
            (value.startswith("'") and value.endswith("'"))
        ):
            value = value[1:-1]

        print(f"export {key}={shlex.quote(value)}")
PY
)"

if [ -z "${SUPABASE_SERVICE_KEY:-}" ]; then
  echo "[run_signal_closer_live] ERROR: SUPABASE_SERVICE_KEY missing after safe env load" >&2
  exit 2
fi

MAX_AGE="${SIGNAL_MAX_AGE_HOURS:-24}"
MAX_BATCH="${SIGNAL_CLOSER_MAX_BATCH:-5}"

python3 "$ROOT/tools/signal_closer.py" \
  --max-age "$MAX_AGE" \
  --live \
  --confirm CLOSE_SIGNALS \
  --max-batch "$MAX_BATCH" \
  --allow-bulk
