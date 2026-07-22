#!/data/data/com.termux/files/usr/bin/bash
# Hourly reachability heartbeat. Pipeline transitions are owned by bota_supervisor.sh.
set -euo pipefail

ROOT="${HOME}/BotA"
LOGDIR="${ROOT}/logs"
TELE="${ROOT}/config/tele.env"
HEALTH="${ROOT}/state/runtime_health.json"
mkdir -p "${LOGDIR}"

log() {
  printf '[%s] %s\n' "$(date -u +'%Y-%m-%d %H:%M:%S UTC')" "$*" >> "${LOGDIR}/cron.heartbeat.log"
}

if [[ -f "${TELE}" ]]; then
  # shellcheck disable=SC1090
  . "${TELE}"
else
  log "tele.env missing"
  exit 0
fi

if [[ -z "${TELEGRAM_BOT_TOKEN:-}" || -z "${TELEGRAM_CHAT_ID:-}" ]]; then
  log "TELEGRAM variables missing"
  exit 0
fi

summary="$(HEALTH_PATH="${HEALTH}" python3 - <<'PY'
import json
import os
from pathlib import Path

path = Path(os.environ["HEALTH_PATH"])
try:
    health = json.loads(path.read_text(encoding="utf-8"))
except Exception:
    print("mode=UNKNOWN | runtime_health.json missing or unreadable")
    raise SystemExit

mode = str(health.get("bot_mode") or "UNKNOWN")
market = str(health.get("market_state") or "unknown")
failures = health.get("failure_reasons") or []
control = health.get("control_plane") or {}
pipeline = health.get("pipeline_progress") or {}
owned = control.get("owned", "?")
required = control.get("required", 7)
running = control.get("running", "?")
orphaned = control.get("orphaned", "?")
progress_ok = pipeline.get("healthy")
parts = [
    f"mode={mode}",
    f"market={market}",
    f"owned={owned}/{required}",
    f"running={running}/{required}",
    f"orphaned={orphaned}",
    f"useful_progress={'PASS' if progress_ok is True else 'FAIL' if progress_ok is False else 'UNKNOWN'}",
]
if failures:
    parts.append("failures=" + "|".join(str(item) for item in failures[:4]))
print(" | ".join(parts))
PY
)"

api="https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage"
text="💓 BotA process heartbeat — ${summary}\nThis confirms Telegram reachability only; signal health is reported by the fields above."

response="$(curl -sS --max-time 15 -X POST "${api}" \
  -d "chat_id=${TELEGRAM_CHAT_ID}" \
  --data-urlencode "text=${text}" || true)"

if grep -q '"ok":true' <<<"${response}"; then
  log "heartbeat sent: ${summary}"
else
  log "heartbeat failed"
fi

exit 0
