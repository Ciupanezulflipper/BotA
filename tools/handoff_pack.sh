#!/data/data/com.termux/files/usr/bin/bash
###############################################################################
# FILE: tools/handoff_pack.sh  v2.0
# PURPOSE: Produces a full session handoff snapshot combining:
#   - state/STATE.json           (canonical session snapshot, human-updated)
#   - state/runtime_health.json  (live 5-min supervisor output)
# USAGE: bash tools/handoff_pack.sh
###############################################################################
set -euo pipefail

ROOT="/data/data/com.termux/files/home/BotA"
cd "$ROOT" || exit 1

WARNINGS=()

add_warning() {
  WARNINGS+=("$1")
}

echo "=== BOTA HANDOFF PACK ==="
echo

# ── Git ───────────────────────────────────────────────────────────────────────
echo "--- GIT ---"
BRANCH="$(git branch --show-current 2>/dev/null || true)"
COMMIT="$(git rev-parse --short HEAD 2>/dev/null || true)"
STATUS_SHORT="$(git status --short 2>/dev/null || true)"
echo "${BRANCH:-unknown_branch}"
echo "${COMMIT:-unknown_commit}"
printf '%s\n' "${STATUS_SHORT:-}"
echo

[[ -n "${STATUS_SHORT}" ]] && add_warning "git_worktree_dirty"

for f in CONTINUITY.md DECISIONS.md RESOLVED.md state/STATE.json tools/handoff_pack.sh tools/bota_supervisor.sh tools/signal_closer.py; do
  [[ ! -e "$f" ]] && add_warning "missing:${f}"
done

UNTRACKED=""
if command -v git >/dev/null 2>&1; then
  UNTRACKED="$(git status --short 2>/dev/null | awk '/^\?\? /{print $2}')"
fi

for wf in CONTINUITY.md DECISIONS.md RESOLVED.md state/STATE.json tools/handoff_pack.sh tools/bota_supervisor.sh tools/signal_closer.py; do
  printf '%s\n' "${UNTRACKED}" | grep -Fxq "${wf}" && add_warning "untracked:${wf}" || true
done

# ── STATE.json staleness check ────────────────────────────────────────────────
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
import sys, datetime as dt
def parse(v): return dt.datetime.fromisoformat(v.replace("Z", "+00:00"))
try:
    print("stale" if parse(sys.argv[1]) < parse(sys.argv[2]) else "fresh")
except Exception:
    print("unknown")
PY
  )"
  [[ "${CMP}" = "stale" ]]   && add_warning "state_json_older_than_cache_or_indicators"
  [[ "${CMP}" = "unknown" ]] && add_warning "state_json_timestamp_unparseable"
fi

# ── Handoff status ────────────────────────────────────────────────────────────
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

# ── Runtime health (supervisor output) ───────────────────────────────────────
echo "--- RUNTIME HEALTH (state/runtime_health.json) ---"
if [[ -f state/runtime_health.json ]]; then
  python3 - <<'PY'
import json, sys
try:
    h = json.load(open("state/runtime_health.json", "r", encoding="utf-8"))
    print(f"bot_mode              = {h.get('bot_mode','UNKNOWN')}")
    print(f"last_supervisor_run   = {h.get('last_supervisor_run_utc','?')}")
    print(f"crond_pid             = {h.get('crond_pid','?')}")
    print(f"watcher_log_age_min   = {h.get('watcher_log_age_min','?')}")
    print(f"updater_log_age_min   = {h.get('updater_log_age_min','?')}")
    print(f"shadow_log_age_min    = {h.get('shadow_log_age_min','?')}")
    print(f"eurusd_m15_cache_age  = {h.get('eurusd_m15_cache_age_min','?')}min")
    print(f"gbpusd_m15_cache_age  = {h.get('gbpusd_m15_cache_age_min','?')}min")
    print(f"eurusd_h1_cache_age   = {h.get('eurusd_h1_cache_age_min','?')}min")
    print(f"gbpusd_h1_cache_age   = {h.get('gbpusd_h1_cache_age_min','?')}min")
    fr = h.get('failure_reasons')
    print(f"failure_reasons       = {fr if fr else 'none'}")
    print(f"last_healthy_utc      = {h.get('last_healthy_utc','?')}")
    if h.get('last_degraded_utc'):
        print(f"last_degraded_utc     = {h.get('last_degraded_utc')}")
        print(f"last_degraded_reason  = {h.get('last_degraded_reason','?')}")
except Exception as e:
    print(f"ERROR reading runtime_health.json: {e}", file=sys.stderr)
PY
else
  echo "state/runtime_health.json missing — supervisor not yet deployed or not run"
  echo "Deploy tools/bota_supervisor.sh and add to cron: */5 * * * *"
fi
echo

# ── Canonical state snapshot ──────────────────────────────────────────────────
echo "--- STATE SNAPSHOT (state/STATE.json) ---"
if [[ -f state/STATE.json ]]; then
  cat state/STATE.json
else
  echo "state/STATE.json missing"
fi
echo

# ── Decisions ─────────────────────────────────────────────────────────────────
echo "--- LOCKED DECISIONS (tail) ---"
tail -n 40 DECISIONS.md 2>/dev/null || echo "DECISIONS.md missing"
echo

echo "--- RESOLVED (tail) ---"
tail -n 40 RESOLVED.md 2>/dev/null || echo "RESOLVED.md missing"
echo

echo "--- CONTINUITY (tail) ---"
tail -n 40 CONTINUITY.md 2>/dev/null || echo "CONTINUITY.md missing"
echo

# ── Watcher scope ─────────────────────────────────────────────────────────────
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

# ── Error log ─────────────────────────────────────────────────────────────────
echo "--- error.log tail ---"
tail -n 30 logs/error.log 2>/dev/null || echo "logs/error.log missing"
echo

# ── Cache mtimes ──────────────────────────────────────────────────────────────
echo "--- D1 cache mtimes ---"
find cache -maxdepth 1 -type f -name 'd1_trend_*.json' -exec ls -l --time-style=long-iso {} + 2>/dev/null \
  || echo "No d1_trend caches found"
echo

echo "--- indicator mtimes (latest 10) ---"
find cache -maxdepth 1 -type f -name 'indicators_*.json' -printf '%TY-%Tm-%Td %TH:%TM %p\n' 2>/dev/null \
  | sort -r | head -n 10 \
  || echo "No indicators found"
echo
