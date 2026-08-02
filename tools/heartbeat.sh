#!/data/data/com.termux/files/usr/bin/bash
###############################################################################
# FILE: tools/heartbeat.sh
# PURPOSE:
#   Send a concise BotA runtime-state message only when the meaningful runtime
#   state changes.
#
# DELIVERY POLICY:
#   - Successful delivery is suppressed while the state remains unchanged.
#   - Failed Telegram delivery is persisted and retried with bounded backoff.
#   - The one-minute runit cycle does not create one Telegram attempt per minute
#     during an internet outage.
#   - No trading logic, market gate, strategy, threshold, pair, or timeframe is
#     changed by this file.
###############################################################################

set -u

ROOT="${HOME}/BotA"
LOG="${ROOT}/logs/cron.heartbeat.log"
HEALTH="${ROOT}/state/runtime_health.json"
CLOCK="${ROOT}/logs/clock_drift_status.json"
TELE="${ROOT}/config/tele.env"
STATE="${HEARTBEAT_STATE_FILE:-${ROOT}/state/heartbeat_delivery_state.json}"
DRY_RUN="${HEARTBEAT_DRY_RUN:-0}"

RETRY_BASE_SECONDS="${HEARTBEAT_RETRY_BASE_SECONDS:-300}"
RETRY_MAX_SECONDS="${HEARTBEAT_RETRY_MAX_SECONDS:-3600}"

mkdir -p "${ROOT}/logs" "${ROOT}/state"

HEALTH="${HEALTH}" \
CLOCK="${CLOCK}" \
STATE="${STATE}" \
TELE="${TELE}" \
LOG="${LOG}" \
DRY_RUN="${DRY_RUN}" \
RETRY_BASE_SECONDS="${RETRY_BASE_SECONDS}" \
RETRY_MAX_SECONDS="${RETRY_MAX_SECONDS}" \
python3 <<'PYTHON'
import hashlib
import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

health_path = Path(os.environ["HEALTH"])
clock_path = Path(os.environ["CLOCK"])
state_path = Path(os.environ["STATE"])
tele_path = Path(os.environ["TELE"])
log_path = Path(os.environ["LOG"])

dry_run = os.environ["DRY_RUN"] == "1"

try:
    retry_base_seconds = max(
        60,
        int(os.environ["RETRY_BASE_SECONDS"]),
    )
except (KeyError, ValueError):
    retry_base_seconds = 300

try:
    retry_max_seconds = max(
        retry_base_seconds,
        int(os.environ["RETRY_MAX_SECONDS"]),
    )
except (KeyError, ValueError):
    retry_max_seconds = 3600


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


def parse_utc(value: Any) -> datetime | None:
    text = str(value or "").strip()

    if not text:
        return None

    try:
        return datetime.fromisoformat(
            text.replace("Z", "+00:00")
        ).astimezone(timezone.utc)
    except ValueError:
        return None


def log(message: str) -> None:
    stamp = utc_now().strftime("%Y-%m-%d %H:%M:%S UTC")

    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(f"[{stamp}] {message}\n")


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}

    return value if isinstance(value, dict) else {}


def save_delivery_state(payload: dict[str, Any]) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)

    temporary = state_path.with_suffix(
        state_path.suffix + ".tmp"
    )

    temporary.write_text(
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    temporary.chmod(0o600)
    temporary.replace(state_path)


def retry_delay_seconds(retry_count: int) -> int:
    exponent = max(0, min(retry_count - 1, 10))
    delay = retry_base_seconds * (2**exponent)
    return min(delay, retry_max_seconds)


def persist_delivery_failure(
    *,
    previous: dict[str, Any],
    day: str,
    signature: str,
    healthy: bool,
    failure_reason: str,
) -> None:
    prior_retry_count = 0

    if (
        previous.get("delivery_failure") is True
        and previous.get("day") == day
        and previous.get("signature") == signature
    ):
        try:
            prior_retry_count = int(
                previous.get("retry_count") or 0
            )
        except (TypeError, ValueError):
            prior_retry_count = 0

    retry_count = prior_retry_count + 1
    delay = retry_delay_seconds(retry_count)
    now = utc_now()
    next_retry = now + timedelta(seconds=delay)

    save_delivery_state(
        {
            "schema_version": "2.0",
            "day": day,
            "signature": signature,
            "healthy": healthy,
            "delivery_failure": True,
            "delivery_failure_reason": failure_reason,
            "retry_count": retry_count,
            "last_failure_utc": iso_utc(now),
            "next_retry_utc": iso_utc(next_retry),
            "retry_delay_seconds": delay,
        }
    )

    log(
        "heartbeat delivery failure persisted: "
        f"reason={failure_reason} "
        f"retry_count={retry_count} "
        f"next_retry_utc={iso_utc(next_retry)}"
    )


health = read_json(health_path)

if not health:
    log("heartbeat skipped: health unreadable")
    raise SystemExit(0)

clock = read_json(clock_path)

control = health.get("control_plane") or {}
pipeline = health.get("pipeline_progress") or {}

failures = [
    str(reason)
    for reason in health.get("failure_reasons") or []
]

if clock.get("server_clock_ok") is True:
    failures = [
        reason
        for reason in failures
        if reason != "local_clock_drift"
    ]

required = int(control.get("required") or 7)
owned = control.get("owned")
running = control.get("running")
orphaned = control.get("orphaned")
progress = pipeline.get("healthy")

market = str(
    health.get("market_state") or "unknown"
).capitalize()

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
    json.dumps(
        signature_data,
        sort_keys=True,
    ).encode("utf-8")
).hexdigest()

server_utc = str(clock.get("server_utc") or "")

if len(server_utc) >= 10:
    day = server_utc[:10]
else:
    day = utc_now().date().isoformat()

previous = read_json(state_path)

same_state = (
    previous.get("signature") == signature
    and previous.get("day") == day
)

if same_state and previous.get("delivery_failure") is not True:
    log(f"heartbeat suppressed: unchanged day={day}")
    raise SystemExit(0)

if same_state and previous.get("delivery_failure") is True:
    next_retry = parse_utc(previous.get("next_retry_utc"))

    if next_retry is not None and utc_now() < next_retry:
        remaining = max(
            0,
            int((next_retry - utc_now()).total_seconds()),
        )

        log(
            "heartbeat retry suppressed: "
            f"remaining_seconds={remaining} "
            f"next_retry_utc={iso_utc(next_retry)}"
        )

        raise SystemExit(0)

if healthy:
    lines = [
        "✅ BotA Operational",
        "",
        f"Market: {market}",
        f"Services: {required}/{required} running",
        "Runtime: Healthy",
    ]
else:
    lines = [
        "⚠️ BotA Attention Required",
        "",
        f"Market: {market}",
        f"Services: {running}/{required} running",
        "Runtime: Degraded",
    ]

if (
    clock.get("local_clock_unsafe") is True
    and clock.get("server_clock_ok") is True
):
    lines.append(
        "Clock: Trusted internet time active"
    )

lines.extend(
    [
        "",
        "Next message: state change or daily confirmation.",
    ]
)

message = "\n".join(lines)

if dry_run:
    log(
        "heartbeat dry-run would send: "
        + message.replace("\n", " | ")
    )
    raise SystemExit(0)

values: dict[str, str] = {}

try:
    tele_lines = tele_path.read_text(
        encoding="utf-8"
    ).splitlines()
except OSError:
    tele_lines = []

for raw in tele_lines:
    raw = raw.strip()

    if (
        not raw
        or raw.startswith("#")
        or "=" not in raw
    ):
        continue

    key, value = raw.split("=", 1)
    values[key.strip()] = value.strip().strip("'\"")

token = values.get("TELEGRAM_BOT_TOKEN", "")
chat = values.get("TELEGRAM_CHAT_ID", "")

if not token or not chat:
    log("heartbeat failed: Telegram settings missing")

    persist_delivery_failure(
        previous=previous,
        day=day,
        signature=signature,
        healthy=healthy,
        failure_reason="telegram_settings_missing",
    )

    raise SystemExit(0)

data = urllib.parse.urlencode(
    {
        "chat_id": chat,
        "text": message,
        "disable_web_page_preview": "true",
    }
).encode("utf-8")

request = urllib.request.Request(
    f"https://api.telegram.org/bot{token}/sendMessage",
    data=data,
    method="POST",
)

try:
    with urllib.request.urlopen(
        request,
        timeout=15,
    ) as response:
        result = json.loads(
            response.read().decode("utf-8")
        )
except Exception as exc:
    log(f"heartbeat failed: {type(exc).__name__}")

    persist_delivery_failure(
        previous=previous,
        day=day,
        signature=signature,
        healthy=healthy,
        failure_reason=type(exc).__name__,
    )

    raise SystemExit(0)

if result.get("ok") is not True:
    log("heartbeat failed: Telegram rejected message")

    persist_delivery_failure(
        previous=previous,
        day=day,
        signature=signature,
        healthy=healthy,
        failure_reason="telegram_rejected",
    )

    raise SystemExit(0)

log(
    f"heartbeat sent: healthy={healthy} "
    f"market={market}"
)

save_delivery_state(
    {
        "schema_version": "2.0",
        "day": day,
        "signature": signature,
        "healthy": healthy,
        "delivery_failure": False,
        "delivery_failure_reason": "",
        "retry_count": 0,
        "last_success_utc": iso_utc(utc_now()),
        "next_retry_utc": None,
    }
)
PYTHON
