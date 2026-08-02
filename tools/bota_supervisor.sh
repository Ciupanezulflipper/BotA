#!/data/data/com.termux/files/usr/bin/bash
###############################################################################
# FILE: tools/bota_supervisor.sh
# PURPOSE:
#   Report BotA runtime health from exact runit ownership and useful pipeline
#   progress. Clock/market-gate availability is reported separately and never
#   promoted to a process-health failure by itself.
#
# SAFETY:
#   This supervisor is read-only toward services. It never starts or restarts
#   crond, runsvdir, runsv, or BotA workers.
###############################################################################

set -euo pipefail
shopt -s inherit_errexit 2>/dev/null || true

ROOT="${BOTA_ROOT:-${HOME}/BotA}"
TOOLS="${ROOT}/tools"
LOGS="${ROOT}/logs"
STATE="${ROOT}/state"
RUNTIME_HEALTH="${STATE}/runtime_health.json"
DEGRADED_FLAG="${LOGS}/state/supervisor_degraded.flag"
CLOCK_STATUS="${LOGS}/clock_drift_status.json"

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
  curl -sS --connect-timeout 5 --max-time 10 -X POST \
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
from pathlib import Path

path = Path(os.environ["JSON_PATH"])
prefix = os.environ["PREFIX_VALUE"]
try:
    data = json.loads(path.read_text(encoding="utf-8"))
except (OSError, UnicodeError, json.JSONDecodeError) as exc:
    print(f"{prefix}_status_unreadable:{type(exc).__name__}")
    raise SystemExit(0)

if not isinstance(data, dict):
    print(f"{prefix}_status_unreadable:invalid_json_type")
    raise SystemExit(0)

failures = data.get("failure_reasons")
if isinstance(failures, list):
    for reason in failures:
        print(f"{prefix}:{reason}")
PY
}

log "=== SUPERVISOR START ==="

control_tmp="$(mktemp)"
pipeline_tmp="$(mktemp)"
market_stdout_tmp="$(mktemp)"
market_stderr_tmp="$(mktemp)"
clock_tmp="$(mktemp)"
trap 'rm -f -- "${control_tmp}" "${pipeline_tmp}" "${market_stdout_tmp}" "${market_stderr_tmp}" "${clock_tmp}"' EXIT

control_rc=0
python3 "${TOOLS}/control_plane_status.py" >"${control_tmp}" 2>>"${LOGS}/error.log" || control_rc=$?

market_rc=0
MARKET_OPEN_DEBUG=1 bash "${TOOLS}/market_open.sh" \
  >"${market_stdout_tmp}" 2>"${market_stderr_tmp}" || market_rc=$?

market_stdout="$(head -c 4096 -- "${market_stdout_tmp}" 2>/dev/null || true)"
market_stderr="$(head -c 4096 -- "${market_stderr_tmp}" 2>/dev/null || true)"
clock_present=0
clock_json=""
if [[ -f "${CLOCK_STATUS}" ]]; then
  clock_present=1
  clock_json="$(head -c 16384 -- "${CLOCK_STATUS}" 2>/dev/null || true)"
fi

SUPERVISOR_MARKET_EXIT_CODE="${market_rc}" \
SUPERVISOR_MARKET_STDOUT="${market_stdout}" \
SUPERVISOR_MARKET_STDERR="${market_stderr}" \
SUPERVISOR_CLOCK_PRESENT="${clock_present}" \
SUPERVISOR_CLOCK_JSON="${clock_json}" \
python3 "${TOOLS}/supervisor_clock_status.py" >"${clock_tmp}"

market_state="$(
  CLOCK_REPORT_PATH="${clock_tmp}" python3 - <<'PY'
import json
import os
from pathlib import Path

data = json.loads(Path(os.environ["CLOCK_REPORT_PATH"]).read_text(encoding="utf-8"))
print(data["market_gate"]["state"])
PY
)"

pipeline_rc=0
if [ "${market_state}" = "open" ]; then
  python3 "${TOOLS}/pipeline_health.py" --market-open \
    >"${pipeline_tmp}" 2>>"${LOGS}/error.log" || pipeline_rc=$?
else
  python3 "${TOOLS}/pipeline_health.py" --market-closed \
    >"${pipeline_tmp}" 2>>"${LOGS}/error.log" || pipeline_rc=$?
fi

FAILURES=()
if (( control_rc != 0 )); then
  while IFS= read -r reason; do
    [[ -n "${reason}" ]] && FAILURES+=("${reason}")
  done < <(json_failures "${control_tmp}" control_plane)
fi
if (( pipeline_rc != 0 )); then
  while IFS= read -r reason; do
    [[ -n "${reason}" ]] && FAILURES+=("${reason}")
  done < <(json_failures "${pipeline_tmp}" pipeline)
fi

BOT_MODE="HEALTHY"
FAILURE_STR=""
if (( ${#FAILURES[@]} > 0 )); then
  BOT_MODE="DEGRADED"
  FAILURE_STR="$(IFS='|'; echo "${FAILURES[*]}")"
fi

CONTROL_PATH="${control_tmp}" \
PIPELINE_PATH="${pipeline_tmp}" \
CLOCK_REPORT_PATH="${clock_tmp}" \
RUNTIME_PATH="${RUNTIME_HEALTH}" \
BOT_MODE_VALUE="${BOT_MODE}" \
FAILURE_VALUE="${FAILURE_STR}" \
python3 - <<'PY'
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path


def load_object(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} did not contain a JSON object")
    return data


control = load_object(Path(os.environ["CONTROL_PATH"]))
pipeline = load_object(Path(os.environ["PIPELINE_PATH"]))
clock_report = load_object(Path(os.environ["CLOCK_REPORT_PATH"]))
path = Path(os.environ["RUNTIME_PATH"])
now = datetime.now(timezone.utc).isoformat()

market_gate = clock_report.get("market_gate")
clock_observability = clock_report.get("clock_observability")
if not isinstance(market_gate, dict):
    raise ValueError("market_gate report missing")
if not isinstance(clock_observability, dict):
    raise ValueError("clock_observability report missing")

health = {
    "schema_version": "2.1",
    "file_purpose": (
        "live runtime truth from exact runit ownership and monotonic useful "
        "progress, with clock availability reported separately"
    ),
    "bot_mode": os.environ["BOT_MODE_VALUE"],
    "market_state": str(market_gate.get("state") or "error"),
    "last_supervisor_run_utc": now,
    "failure_reasons": (
        os.environ["FAILURE_VALUE"].split("|")
        if os.environ["FAILURE_VALUE"]
        else []
    ),
    "control_plane": control,
    "pipeline_progress": pipeline,
    "market_gate": market_gate,
    "clock_observability": clock_observability,
    "service_mutation_performed": False,
}

if path.exists():
    try:
        previous = load_object(path)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        previous = {}
    for key in ("last_healthy_utc", "last_degraded_utc", "last_degraded_reason"):
        if key in previous:
            health[key] = previous[key]

if health["bot_mode"] == "HEALTHY":
    health["last_healthy_utc"] = now
else:
    health["last_degraded_utc"] = now
    health["last_degraded_reason"] = health["failure_reasons"]

path.parent.mkdir(parents=True, exist_ok=True)
temporary_name = ""
try:
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f"{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        temporary_name = handle.name
        json.dump(health, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary_name, path)
finally:
    if temporary_name:
        try:
            Path(temporary_name).unlink()
        except FileNotFoundError:
            pass
PY

clock_status="$(
  CLOCK_REPORT_PATH="${clock_tmp}" python3 - <<'PY'
import json
import os
from pathlib import Path

data = json.loads(Path(os.environ["CLOCK_REPORT_PATH"]).read_text(encoding="utf-8"))
clock = data.get("clock_observability") or {}
print(clock.get("status") or "UNKNOWN")
PY
)"

market_detail="$(tr '\n' '|' <"${market_stderr_tmp}" | cut -c1-240)"
log "MARKET_GATE: state=${market_state} rc=${market_rc} detail=${market_detail:-none}"
log "CLOCK_OBSERVABILITY: status=${clock_status} runtime_failure=NO"

if [ "${BOT_MODE}" = "DEGRADED" ]; then
  log "DEGRADED: ${FAILURE_STR}"
  if [[ ! -f "${DEGRADED_FLAG}" ]]; then
    send_telegram "[BotA DEGRADED] ${FAILURE_STR} — $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    printf '%s\n' "${FAILURE_STR}" > "${DEGRADED_FLAG}"
    log "ACTION: transition alert attempted"
  fi
else
  log "HEALTHY: exact ownership and useful-progress gates passed"
  if [[ -f "${DEGRADED_FLAG}" ]]; then
    send_telegram "[BotA RECOVERY] Exact ownership and useful progress restored — $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    rm -f "${DEGRADED_FLAG}"
    log "ACTION: recovery alert attempted"
  fi
fi

log "SERVICE_MUTATION_PERFORMED=NO"
log "=== SUPERVISOR DONE: bot_mode=${BOT_MODE} market=${market_state} clock=${clock_status} ==="
exit 0
