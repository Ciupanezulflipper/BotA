#!/data/data/com.termux/files/usr/bin/bash
set -u

ROOT="${HOME}/BotA"
LOG="${ROOT}/logs/cron.heartbeat.log"
HEALTH="${ROOT}/state/runtime_health.json"
CLOCK="${ROOT}/logs/clock_drift_status.json"
TELE="${ROOT}/config/tele.env"
STATE="${HEARTBEAT_STATE_FILE:-${ROOT}/state/heartbeat_delivery_state.json}"
DRY_RUN="${HEARTBEAT_DRY_RUN:-0}"

mkdir -p "${ROOT}/logs" "${ROOT}/state"

HEALTH="$HEALTH" CLOCK="$CLOCK" STATE="$STATE" TELE="$TELE" LOG="$LOG" DRY_RUN="$DRY_RUN" python3 <<'PYTHON'
import hashlib
import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

health_path = Path(os.environ["HEALTH"])
clock_path = Path(os.environ["CLOCK"])
state_path = Path(os.environ["STATE"])
tele_path = Path(os.environ["TELE"])
log_path = Path(os.environ["LOG"])
dry_run = os.environ["DRY_RUN"] == "1"

def log(message):
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(f"[{stamp}] {message}\n")

try:
    health = json.loads(health_path.read_text(encoding="utf-8"))
except Exception as exc:
    log(f"heartbeat skipped: health unreadable {type(exc).__name__}")
    raise SystemExit

try:
    clock = json.loads(clock_path.read_text(encoding="utf-8"))
except Exception:
    clock = {}

control = health.get("control_plane") or {}
pipeline = health.get("pipeline_progress") or {}
failures = [str(x) for x in health.get("failure_reasons") or []]

if clock.get("server_clock_ok") is True:
    failures = [x for x in failures if x != "local_clock_drift"]

required = int(control.get("required") or 7)
owned = control.get("owned")
running = control.get("running")
orphaned = control.get("orphaned")
progress = pipeline.get("healthy")
market = str(health.get("market_state") or "unknown").capitalize()

healthy = (
    owned == required
    and running == required
    and orphaned == 0
    and progress is True
    and not failures
)

signature_data = {
    "healthy": healthy,
    "market": market,
    "owned": owned,
    "running": running,
    "orphaned": orphaned,
    "progress": progress,
    "failures": failures,
}
signature = hashlib.sha256(
    json.dumps(signature_data, sort_keys=True).encode()
).hexdigest()

server_utc = str(clock.get("server_utc") or "")
day = server_utc[:10] if len(server_utc) >= 10 else datetime.now(timezone.utc).date().isoformat()

try:
    previous = json.loads(state_path.read_text(encoding="utf-8"))
except Exception:
    previous = {}

if previous.get("signature") == signature and previous.get("day") == day:
    log(f"heartbeat suppressed: unchanged day={day}")
    raise SystemExit

if healthy:
    lines = [
        "💚 BotA is working normally",
        "",
        f"Market: {market}",
        f"Services: All {required} running",
        "System: Working normally",
    ]
else:
    lines = [
        "⚠️ BotA needs attention",
        "",
        f"Market: {market}",
        f"Services: {running} of {required} running",
        "System: One or more checks need attention",
    ]

if clock.get("local_clock_unsafe") is True and clock.get("server_clock_ok") is True:
    lines.append("Phone time: Different, but BotA is using safe internet time")

lines.extend(["", "Next update: Only if something changes, or tomorrow."])
message = "\n".join(lines)

if dry_run:
    log("heartbeat dry-run would send: " + message.replace("\n", " | "))
else:
    values = {}
    for raw in tele_path.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        values[key.strip()] = value.strip().strip("'\"")

    token = values.get("TELEGRAM_BOT_TOKEN", "")
    chat = values.get("TELEGRAM_CHAT_ID", "")

    if not token or not chat:
        log("heartbeat failed: Telegram settings missing")
        raise SystemExit

    data = urllib.parse.urlencode({"chat_id": chat, "text": message}).encode()
    request = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=data,
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            result = json.loads(response.read().decode())
    except Exception as exc:
        log(f"heartbeat failed: {type(exc).__name__}")
        raise SystemExit

    if result.get("ok") is not True:
        log("heartbeat failed: Telegram rejected message")
        raise SystemExit

    log(f"heartbeat sent: healthy={healthy} market={market}")

state_path.parent.mkdir(parents=True, exist_ok=True)
temporary = state_path.with_suffix(".tmp")
temporary.write_text(
    json.dumps({"day": day, "signature": signature, "healthy": healthy}, indent=2) + "\n",
    encoding="utf-8",
)
temporary.chmod(0o600)
temporary.replace(state_path)
PYTHON
