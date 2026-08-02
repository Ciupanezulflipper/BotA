#!/data/data/com.termux/files/usr/bin/bash
###############################################################################
# FILE: tools/bota_supervisor.sh
# PURPOSE:
#   Report BotA runtime health from exact runit ownership and useful pipeline
#   progress.
#
# SAFETY:
#   - Never starts or restarts services.
#   - Trading processes remain independently fail-closed when trusted server
#     time is unavailable.
#   - A temporary internet-clock lookup failure is observable but is not, by
#     itself, classified as a full BotA runtime failure.
###############################################################################

set -euo pipefail
shopt -s inherit_errexit 2>/dev/null || true

ROOT="${HOME}/BotA"
TOOLS="${ROOT}/tools"
LOGS="${ROOT}/logs"
STATE="${ROOT}/state"
RUNTIME_HEALTH="${STATE}/runtime_health.json"
CLOCK_STATUS="${LOGS}/clock_drift_status.json"
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
      ""|\#*)
        continue
        ;;
      *=*)
        key="${line%%=*}"
        value="${line#*=}"
        ;;
      *)
        continue
        ;;
    esac

    case "${key}" in
      ""|[0-9]*|*[!A-Za-z0-9_]*)
        continue
        ;;
    esac

    case "${value}" in
      \"*\")
        value="${value#\"}"
        value="${value%\"}"
        ;;
      \'*\')
        value="${value#\'}"
        value="${value%\'}"
        ;;
    esac

    export "${key}=${value}"
  done <"${file}"
}

load_env "${ROOT}/config/tele.env"
load_env "${ROOT}/.env.runtime"

log() {
  printf '[SUPERVISOR %s] %s\n' \
    "$(date -u +'%Y-%m-%dT%H:%M:%SZ')" \
    "$*"
}

send_telegram() {
  local message="$1"

  if [[ -z "${TELEGRAM_BOT_TOKEN:-}" || -z "${TELEGRAM_CHAT_ID:-}" ]]; then
    log "NOTICE: Telegram settings unavailable; transition message not sent"
    return 0
  fi

  curl \
    -sS \
    --max-time 10 \
    -X POST \
    "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
    -d "chat_id=${TELEGRAM_CHAT_ID}" \
    --data-urlencode "text=${message}" \
    >/dev/null 2>&1 || {
      log "NOTICE: Telegram transition delivery failed"
      return 0
    }
}

json_failures() {
  local file="$1"
  local prefix="$2"

  JSON_PATH="${file}" PREFIX_VALUE="${prefix}" python3 - <<'PY'
import json
import os

try:
    data = json.load(
        open(
            os.environ["JSON_PATH"],
            "r",
            encoding="utf-8",
        )
    )
except Exception as exc:
    print(
        f"{os.environ['PREFIX_VALUE']}_status_unreadable:"
        f"{type(exc).__name__}"
    )
    raise SystemExit

for reason in data.get("failure_reasons", []) or []:
    print(f"{os.environ['PREFIX_VALUE']}:{reason}")
PY
}

clock_failure() {
  CLOCK_PATH="${CLOCK_STATUS}" python3 - <<'PY'
import json
import os
from pathlib import Path

path = Path(os.environ["CLOCK_PATH"])

try:
    data = json.loads(path.read_text(encoding="utf-8"))
except Exception:
    print("clock_status_missing")
    raise SystemExit

status = str(data.get("status") or "UNKNOWN")
server_clock_ok = data.get("server_clock_ok")
local_clock_unsafe = data.get("local_clock_unsafe")

if status == "SERVER_CLOCK_UNAVAILABLE":
    print(
        "CLOCK_OBSERVATION="
        "trusted_server_clock_temporarily_unavailable",
        file=__import__("sys").stderr,
    )
elif server_clock_ok is True and local_clock_unsafe is True:
    print(
        "CLOCK_OBSERVATION="
        "phone_clock_differs_but_trusted_server_clock_available",
        file=__import__("sys").stderr,
    )
PY
}

log "=== SUPERVISOR START ==="

control_tmp="$(mktemp)"
pipeline_tmp="$(mktemp)"

cleanup() {
  rm -f "${control_tmp}" "${pipeline_tmp}"
}

trap cleanup EXIT

control_rc=0
python3 "${TOOLS}/control_plane_status.py" \
  >"${control_tmp}" \
  2>>"${LOGS}/error.log" ||
  control_rc=$?

market_state="closed"

if bash "${TOOLS}/market_open.sh" >/dev/null 2>&1; then
  market_state="open"
fi

pipeline_rc=0

if [[ "${market_state}" == "open" ]]; then
  python3 "${TOOLS}/pipeline_health.py" \
    --market-open \
    >"${pipeline_tmp}" \
    2>>"${LOGS}/error.log" ||
    pipeline_rc=$?
else
  python3 "${TOOLS}/pipeline_health.py" \
    --market-closed \
    >"${pipeline_tmp}" \
    2>>"${LOGS}/error.log" ||
    pipeline_rc=$?
fi

FAILURES=()

if (( control_rc != 0 )); then
  while IFS= read -r reason; do
    [[ -n "${reason}" ]] && FAILURES+=("${reason}")
  done < <(
    json_failures "${control_tmp}" control_plane
  )
fi

if (( pipeline_rc != 0 )); then
  while IFS= read -r reason; do
    [[ -n "${reason}" ]] && FAILURES+=("${reason}")
  done < <(
    json_failures "${pipeline_tmp}" pipeline
  )
fi

while IFS= read -r reason; do
  [[ -n "${reason}" ]] && FAILURES+=("${reason}")
done < <(
  clock_failure
)

BOT_MODE="HEALTHY"
FAILURE_STR=""

if (( ${#FAILURES[@]} > 0 )); then
  BOT_MODE="DEGRADED"
  FAILURE_STR="$(IFS='|'; printf '%s' "${FAILURES[*]}")"
fi

CONTROL_PATH="${control_tmp}" \
PIPELINE_PATH="${pipeline_tmp}" \
RUNTIME_PATH="${RUNTIME_HEALTH}" \
BOT_MODE_VALUE="${BOT_MODE}" \
FAILURE_VALUE="${FAILURE_STR}" \
MARKET_STATE_VALUE="${market_state}" \
python3 - <<'PY'
import json
import os
from datetime import datetime, timezone
from pathlib import Path

control_path = Path(os.environ["CONTROL_PATH"])
pipeline_path = Path(os.environ["PIPELINE_PATH"])
runtime_path = Path(os.environ["RUNTIME_PATH"])

control = json.loads(control_path.read_text(encoding="utf-8"))
pipeline = json.loads(pipeline_path.read_text(encoding="utf-8"))

now = datetime.now(timezone.utc).isoformat()

health = {
    "schema_version": "2.1",
    "file_purpose": (
        "live runtime truth from exact runit ownership "
        "and monotonic useful progress"
    ),
    "bot_mode": os.environ["BOT_MODE_VALUE"],
    "market_state": os.environ["MARKET_STATE_VALUE"],
    "last_supervisor_run_utc": now,
    "failure_reasons": (
        os.environ["FAILURE_VALUE"].split("|")
        if os.environ["FAILURE_VALUE"]
        else []
    ),
    "control_plane": control,
    "pipeline_progress": pipeline,
    "service_mutation_performed": False,
}

if runtime_path.exists():
    try:
        previous = json.loads(
            runtime_path.read_text(encoding="utf-8")
        )

        for key in (
            "last_healthy_utc",
            "last_degraded_utc",
            "last_degraded_reason",
        ):
            if key in previous:
                health[key] = previous[key]
    except Exception:
        pass

if health["bot_mode"] == "HEALTHY":
    health["last_healthy_utc"] = now
else:
    health["last_degraded_utc"] = now
    health["last_degraded_reason"] = health["failure_reasons"]

runtime_path.parent.mkdir(parents=True, exist_ok=True)

temporary = runtime_path.with_suffix(
    runtime_path.suffix + ".tmp"
)

temporary.write_text(
    json.dumps(
        health,
        indent=2,
        sort_keys=True,
    )
    + "\n",
    encoding="utf-8",
)

os.replace(temporary, runtime_path)
PY

if [[ "${BOT_MODE}" == "DEGRADED" ]]; then
  log "DEGRADED: ${FAILURE_STR}"

  if [[ ! -f "${DEGRADED_FLAG}" ]]; then
    send_telegram \
      "[BotA DEGRADED] ${FAILURE_STR} — $(date -u +%Y-%m-%dT%H:%M:%SZ)"

    printf '%s\n' "${FAILURE_STR}" >"${DEGRADED_FLAG}"
    chmod 600 "${DEGRADED_FLAG}" 2>/dev/null || true

    log "ACTION: transition alert requested"
  fi
else
  log "HEALTHY: exact ownership and useful-progress gates passed"

  if [[ -f "${DEGRADED_FLAG}" ]]; then
    previous_failure="$(
      cat "${DEGRADED_FLAG}" 2>/dev/null ||
      printf 'previous runtime failure'
    )"

    send_telegram \
      "[BotA RECOVERY] Runtime health restored from: ${previous_failure} — $(date -u +%Y-%m-%dT%H:%M:%SZ)"

    rm -f "${DEGRADED_FLAG}"
    log "ACTION: recovery alert requested"
  fi
fi

log "SERVICE_MUTATION_PERFORMED=NO"
log "=== SUPERVISOR DONE: bot_mode=${BOT_MODE} market=${market_state} ==="
exit 0
