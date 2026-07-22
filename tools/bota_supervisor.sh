#!/data/data/com.termux/files/usr/bin/bash
###############################################################################
# FILE: tools/bota_supervisor.sh
# PURPOSE:
#   Report BotA runtime health from exact runit ownership and useful pipeline
#   progress. This supervisor is read-only toward services: it never starts or
#   restarts crond, runsvdir, runsv, or BotA workers.
###############################################################################

set -euo pipefail
shopt -s inherit_errexit 2>/dev/null || true

ROOT="${HOME}/BotA"
TOOLS="${ROOT}/tools"
LOGS="${ROOT}/logs"
STATE="${ROOT}/state"
RUNTIME_HEALTH="${STATE}/runtime_health.json"
DEGRADED_FLAG="${LOGS}/state/supervisor_degraded.flag"

mkdir -p "${LOGS}/state" "${STATE}"

load_env() {
  local file="$1"
  [[ -f "${file}" ]] || return 0
  local line key value
  while IFS= read -r line || [[ -n "${line}" ]]; do
    line="${line#"${line%%[![:space:]]*}"}"
    line="${line%"${line##*[![:space:]]}"}"
    case "${line}" in
      ""|\#*) continue ;;
      *=*)
        key="${line%%=*}"
        value="${line#*=}"
        ;;
      *) continue ;;
    esac
    case "${key}" in
      ""|[0-9]*|*[!A-Za-z0-9_]*) continue ;;
    esac
    case "${value}" in
      \"*\") value="${value#\"}"; value="${value%\"}" ;;
      \'*\') value="${value#\'}"; value="${value%\'}" ;;
    esac
    export "${key}=${value}"
  done < "${file}"
}

load_env "${ROOT}/config/tele.env"
load_env "${ROOT}/.env.runtime"

log() {
  printf '[SUPERVISOR %s] %s\n' "$(date -u +'%Y-%m-%dT%H:%M:%SZ')" "$*"
}

send_telegram() {
  local message="$1"
  [[ -z "${TELEGRAM_BOT_TOKEN:-}" || -z "${TELEGRAM_CHAT_ID:-}" ]] && return 0
  curl -sS --max-time 10 -X POST \
    "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
    -d "chat_id=${TELEGRAM_CHAT_ID}" \
    --data-urlencode "text=${message}" \
    >/dev/null 2>&1 || true
}

json_failures() {
  local file="$1" prefix="$2"
  JSON_PATH="${file}" PREFIX_VALUE="${prefix}" python3 - <<'PY'
import json
import os
try:
    data = json.load(open(os.environ["JSON_PATH"], "r", encoding="utf-8"))
except Exception as exc:
    print(f"{os.environ['PREFIX_VALUE']}_status_unreadable:{type(exc).__name__}")
    raise SystemExit
for reason in data.get("failure_reasons", []) or []:
    print(f"{os.environ['PREFIX_VALUE']}:{reason}")
PY
}

clock_failure() {
  python3 - <<'PY'
import json
from pathlib import Path
path = Path.home() / "BotA/logs/clock_drift_status.json"
try:
    data = json.loads(path.read_text(encoding="utf-8"))
except Exception:
    print("clock_status_missing")
    raise SystemExit
status = str(data.get("status") or "UNKNOWN")
unsafe = data.get("local_clock_unsafe")
if status == "SERVER_CLOCK_UNAVAILABLE":
    print("server_clock_unavailable")
elif status == "DRIFT_WARN" or unsafe is True:
    print("local_clock_drift")
PY
}

log "=== SUPERVISOR START ==="

control_tmp="$(mktemp)"
pipeline_tmp="$(mktemp)"
trap 'rm -f "${control_tmp}" "${pipeline_tmp}"' EXIT

control_rc=0
python3 "${TOOLS}/control_plane_status.py" >"${control_tmp}" 2>>"${LOGS}/error.log" || control_rc=$?

market_state="closed"
if bash "${TOOLS}/market_open.sh" >/dev/null 2>&1; then
  market_state="open"
fi

pipeline_rc=0
if [ "${market_state}" = "open" ]; then
  python3 "${TOOLS}/pipeline_health.py" --market-open >"${pipeline_tmp}" 2>>"${LOGS}/error.log" || pipeline_rc=$?
else
  python3 "${TOOLS}/pipeline_health.py" --market-closed >"${pipeline_tmp}" 2>>"${LOGS}/error.log" || pipeline_rc=$?
fi

FAILURES=()
if (( control_rc != 0 )); then
  while IFS= read -r reason; do [[ -n "${reason}" ]] && FAILURES+=("${reason}"); done < <(json_failures "${control_tmp}" control_plane)
fi
if (( pipeline_rc != 0 )); then
  while IFS= read -r reason; do [[ -n "${reason}" ]] && FAILURES+=("${reason}"); done < <(json_failures "${pipeline_tmp}" pipeline)
fi
while IFS= read -r reason; do [[ -n "${reason}" ]] && FAILURES+=("${reason}"); done < <(clock_failure)

BOT_MODE="HEALTHY"
FAILURE_STR=""
if (( ${#FAILURES[@]} > 0 )); then
  BOT_MODE="DEGRADED"
  FAILURE_STR="$(IFS='|'; echo "${FAILURES[*]}")"
fi

CONTROL_PATH="${control_tmp}" PIPELINE_PATH="${pipeline_tmp}" \
RUNTIME_PATH="${RUNTIME_HEALTH}" BOT_MODE_VALUE="${BOT_MODE}" \
FAILURE_VALUE="${FAILURE_STR}" MARKET_STATE_VALUE="${market_state}" \
python3 - <<'PY'
import json
import os
from datetime import datetime, timezone
from pathlib import Path

control = json.load(open(os.environ["CONTROL_PATH"], "r", encoding="utf-8"))
pipeline = json.load(open(os.environ["PIPELINE_PATH"], "r", encoding="utf-8"))
path = Path(os.environ["RUNTIME_PATH"])
now = datetime.now(timezone.utc).isoformat()
health = {
    "schema_version": "2.0",
    "file_purpose": "live runtime truth from exact runit ownership and monotonic useful progress",
    "bot_mode": os.environ["BOT_MODE_VALUE"],
    "market_state": os.environ["MARKET_STATE_VALUE"],
    "last_supervisor_run_utc": now,
    "failure_reasons": os.environ["FAILURE_VALUE"].split("|") if os.environ["FAILURE_VALUE"] else [],
    "control_plane": control,
    "pipeline_progress": pipeline,
    "service_mutation_performed": False,
}
if path.exists():
    try:
        previous = json.loads(path.read_text(encoding="utf-8"))
        for key in ("last_healthy_utc", "last_degraded_utc", "last_degraded_reason"):
            if key in previous:
                health[key] = previous[key]
    except Exception:
        pass
if health["bot_mode"] == "HEALTHY":
    health["last_healthy_utc"] = now
else:
    health["last_degraded_utc"] = now
    health["last_degraded_reason"] = health["failure_reasons"]
path.parent.mkdir(parents=True, exist_ok=True)
tmp = path.with_suffix(path.suffix + ".tmp")
tmp.write_text(json.dumps(health, indent=2, sort_keys=True) + "\n", encoding="utf-8")
os.replace(tmp, path)
PY

if [ "${BOT_MODE}" = "DEGRADED" ]; then
  log "DEGRADED: ${FAILURE_STR}"
  if [[ ! -f "${DEGRADED_FLAG}" ]]; then
    send_telegram "[BotA DEGRADED] ${FAILURE_STR} — $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    printf '%s\n' "${FAILURE_STR}" > "${DEGRADED_FLAG}"
    log "ACTION: transition alert sent"
  fi
else
  log "HEALTHY: exact ownership and useful-progress gates passed"
  if [[ -f "${DEGRADED_FLAG}" ]]; then
    send_telegram "[BotA RECOVERY] Exact ownership and useful progress restored — $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    rm -f "${DEGRADED_FLAG}"
    log "ACTION: recovery alert sent"
  fi
fi

log "SERVICE_MUTATION_PERFORMED=NO"
log "=== SUPERVISOR DONE: bot_mode=${BOT_MODE} market=${market_state} ==="
exit 0
