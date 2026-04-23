#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

ROOT="/data/data/com.termux/files/home/BotA"
cd "$ROOT" || exit 1

WARNINGS=()

add_warning() {
  WARNINGS+=("$1")
}

echo "=== BOTA HANDOFF PACK ==="
echo

echo "--- GIT ---"
BRANCH="$(git branch --show-current 2>/dev/null || true)"
COMMIT="$(git rev-parse --short HEAD 2>/dev/null || true)"
STATUS_SHORT="$(git status --short 2>/dev/null || true)"
echo "${BRANCH:-unknown_branch}"
echo "${COMMIT:-unknown_commit}"
printf '%s\n' "${STATUS_SHORT:-}"
echo

if [[ -n "${STATUS_SHORT}" ]]; then
  add_warning "git_worktree_dirty"
fi

for f in CONTINUITY.md DECISIONS.md RESOLVED.md state/STATE.json tools/handoff_pack.sh; do
  if [[ ! -e "$f" ]]; then
    add_warning "missing:${f}"
  fi
done

UNTRACKED=""
if command -v git >/dev/null 2>&1; then
  UNTRACKED="$(git status --short 2>/dev/null | awk '/^\?\? /{print $2}')"
fi

for wf in CONTINUITY.md DECISIONS.md RESOLVED.md state/STATE.json tools/handoff_pack.sh; do
  if printf '%s\n' "${UNTRACKED}" | grep -Fxq "${wf}"; then
    add_warning "untracked:${wf}"
  fi
done

STATE_TS=""
if [[ -f state/STATE.json ]]; then
  STATE_TS="$(python3 - <<'PY'
import json

try:
    data = json.load(open("state/STATE.json", "r", encoding="utf-8"))
    print(data.get("_meta", {}).get("last_updated", ""))
except Exception:
    print("")
PY
)"
fi

NEWEST_PROOF_TS="$(python3 - <<'PY'
from pathlib import Path
import datetime as dt

candidates = list(Path("cache").glob("d1_trend_*.json")) + list(Path("cache").glob("indicators_*.json"))
if not candidates:
    print("")
    raise SystemExit(0)

latest = max(candidates, key=lambda p: p.stat().st_mtime).stat().st_mtime
print(dt.datetime.fromtimestamp(latest, tz=dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
PY
)"

if [[ -n "${STATE_TS}" && -n "${NEWEST_PROOF_TS}" ]]; then
  CMP="$(python3 - "${STATE_TS}" "${NEWEST_PROOF_TS}" <<'PY'
import sys
import datetime as dt

state_ts = sys.argv[1]
proof_ts = sys.argv[2]

def parse(value: str):
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))

try:
    print("stale" if parse(state_ts) < parse(proof_ts) else "fresh")
except Exception:
    print("unknown")
PY
)"
  if [[ "${CMP}" = "stale" ]]; then
    add_warning "state_json_older_than_cache_or_indicators"
  elif [[ "${CMP}" = "unknown" ]]; then
    add_warning "state_json_timestamp_unparseable"
  fi
fi

echo "--- HANDOFF STATUS ---"
if (( ${#WARNINGS[@]} == 0 )); then
  echo "HANDOFF_STATUS=PASS"
else
  echo "HANDOFF_STATUS=WARN"
  for w in "${WARNINGS[@]}"; do
    echo "WARN=${w}"
  done
fi
echo

echo "--- STATE SNAPSHOT ---"
if [[ -f state/STATE.json ]]; then
  cat state/STATE.json
else
  echo "state/STATE.json missing"
fi
echo

echo "--- LOCKED DECISIONS (tail) ---"
tail -n 40 DECISIONS.md 2>/dev/null || echo "DECISIONS.md missing"
echo

echo "--- RESOLVED (tail) ---"
tail -n 40 RESOLVED.md 2>/dev/null || echo "RESOLVED.md missing"
echo

echo "--- CONTINUITY (tail) ---"
tail -n 40 CONTINUITY.md 2>/dev/null || echo "CONTINUITY.md missing"
echo

echo "--- CURRENT WATCHER SCOPE FROM STATE ---"
python3 - <<'PY'
import json

try:
    data = json.load(open("state/STATE.json", "r", encoding="utf-8"))
    scope = data.get("pipeline", {}).get("watcher", {})
    print("pairs=", scope.get("scope_pairs", []))
    print("timeframes=", scope.get("scope_timeframes", []))
except Exception as exc:
    print("state_scope_error=", exc)
PY
echo

echo "--- error.log tail ---"
tail -n 30 logs/error.log 2>/dev/null || echo "logs/error.log missing"
echo

echo "--- D1 cache mtimes ---"
find cache -maxdepth 1 -type f -name 'd1_trend_*.json' -exec ls -l --time-style=long-iso {} + 2>/dev/null \
  || echo "No d1_trend caches found"
echo

echo "--- indicator mtimes (latest 10) ---"
find cache -maxdepth 1 -type f -name 'indicators_*.json' -printf '%TY-%Tm-%Td %TH:%TM %p\n' 2>/dev/null \
  | sort -r \
  | head -n 10 \
  || echo "No indicators found"
