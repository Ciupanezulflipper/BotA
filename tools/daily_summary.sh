#!/data/data/com.termux/files/usr/bin/bash
# FILE: tools/daily_summary.sh
# ROLE: One concise, authoritative BotA daily proof-of-work report.
#
# Truth hierarchy:
#   1. state/runtime_health.json
#   2. exact control-plane and pipeline-progress fields inside that state
#   3. canonical schedule verification
#   4. provider-specific usage from state/provider_usage.json
#
# Routine job-log age cannot override healthy live runtime truth. The historical
# logs/api_credits.json counter is intentionally ignored because it mixed
# OANDA/Yahoo requests with Twelve Data credits.

set -euo pipefail

ROOT="${BOTA_ROOT:-${HOME}/BotA}"
LOGDIR="${ROOT}/logs"
CFGDIR="${ROOT}/config"
mkdir -p "${LOGDIR}"

DOTENV="${ROOT}/.env"
RUNTIME_ENV="${ROOT}/.env.runtime"
SIGENV="${CFGDIR}/signal.env"
TELEENV="${CFGDIR}/tele.env"

ts_utc() { date -u +'%Y-%m-%d %H:%M:%S UTC'; }

load_env_file() {
  local file="$1"
  [[ -f "$file" ]] || return 0

  while IFS= read -r line || [[ -n "$line" ]]; do
    [[ -z "$line" || "$line" =~ ^[[:space:]]*# || "$line" != *"="* ]] && continue

    local key value
    key="${line%%=*}"
    value="${line#*=}"

    key="$(printf '%s' "$key" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
    value="$(printf '%s' "$value" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"

    [[ "$key" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] || continue

    value="${value%\"}"
    value="${value#\"}"
    value="${value%\'}"
    value="${value#\'}"

    if [[ -z "${!key-}" ]]; then
      export "${key}=${value}"
    fi
  done < "$file"
}

load_env_file "$DOTENV"
load_env_file "$RUNTIME_ENV"
load_env_file "$SIGENV"
load_env_file "$TELEENV"

tg_send_plain() {
  local text="$1"
  local token="${TELEGRAM_BOT_TOKEN:-${TELEGRAM_TOKEN:-${BOT_TOKEN:-}}}"
  local chat_id="${TELEGRAM_CHAT_ID:-${CHAT_ID:-${TG_CHAT_ID:-}}}"

  if [[ "${DAILY_SUMMARY_SEND:-1}" = "0" ]]; then
    echo "[daily] SEND_SKIPPED DAILY_SUMMARY_SEND=0"
    return 0
  fi

  if [[ -z "$token" || -z "$chat_id" ]]; then
    echo "[daily] TELEGRAM_SEND=SKIPPED reason=missing_token_or_chat"
    return 0
  fi

  local api="https://api.telegram.org/bot${token}/sendMessage"
  local response http_code body

  response="$(
    curl -sS \
      --connect-timeout 10 \
      --max-time 20 \
      -w $'\nHTTP_STATUS:%{http_code}\n' \
      -X POST "$api" \
      --data-urlencode "chat_id=${chat_id}" \
      --data-urlencode "disable_web_page_preview=true" \
      --data-urlencode "text=${text}" || true
  )"

  http_code="$(
    printf '%s' "$response" |
      sed -n 's/^HTTP_STATUS:\([0-9][0-9][0-9]\)$/\1/p' |
      tail -n 1
  )"
  body="$(printf '%s' "$response" | sed '/^HTTP_STATUS:[0-9][0-9][0-9]$/d')"

  if printf '%s' "$body" | grep -q '"ok":true'; then
    echo "[daily] TELEGRAM_SEND=PASS http=${http_code:-unknown}"
  else
    echo "[daily] TELEGRAM_SEND=FAIL http=${http_code:-unknown} body=$(printf '%s' "$body" | tr '\n' ' ' | head -c 240)"
  fi
}

SUMMARY="$(
BOTA_ROOT="$ROOT" python3 - <<'PY'
from __future__ import annotations

import csv
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(os.environ.get("BOTA_ROOT", str(Path.home() / "BotA"))).expanduser().resolve()
LOGDIR = ROOT / "logs"
STATE = ROOT / "state"
TODAY = os.environ.get("SUMMARY_DATE") or datetime.now(timezone.utc).strftime("%Y-%m-%d")
NOW_UTC = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

ALERTS = LOGDIR / "alerts.csv"
CLOCK_STATE = LOGDIR / "clock_drift_status.json"
RUNTIME_HEALTH = STATE / "runtime_health.json"
PROVIDER_USAGE = STATE / "provider_usage.json"
VERIFY_CANONICAL = ROOT / "tools" / "verify_canonical_crontab.sh"


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError, OverflowError):
        return default


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError, OverflowError):
        return default


TELEGRAM_MIN_SCORE = safe_float(os.environ.get("TELEGRAM_MIN_SCORE", "70"), 70.0)
RUNTIME_HEALTH_FRESH_MAX_MIN = safe_int(
    os.environ.get("RUNTIME_HEALTH_FRESH_MAX_MIN", "10"),
    10,
)
TWELVE_DATA_DAILY_LIMIT = max(
    0,
    safe_int(os.environ.get("TWELVE_DATA_DAILY_LIMIT", "800"), 800),
)
TWELVE_DATA_RESERVE = max(
    0,
    safe_int(os.environ.get("TWELVE_DATA_RESERVE_CREDITS", "100"), 100),
)


def load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError):
        return default


def parse_utc(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except (TypeError, ValueError, OverflowError):
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def age_minutes_from_timestamp(value: Any) -> int | None:
    timestamp = parse_utc(value)
    if timestamp is None:
        return None
    return int((datetime.now(timezone.utc) - timestamp).total_seconds() // 60)


def file_age_minutes(path: Path) -> int | None:
    try:
        age = int((datetime.now(timezone.utc).timestamp() - path.stat().st_mtime) // 60)
        return max(0, age)
    except OSError:
        return None


def fmt_age(value: int | None) -> str:
    if value is None:
        return "N/A"
    if value < 0:
        return f"future {abs(value)}m"
    if value < 60:
        return f"{value}m"
    return f"{value // 60}h{value % 60:02d}m"


def compact_reasons(reasons: list[str], limit: int = 280) -> str:
    unique: list[str] = []
    for reason in reasons:
        cleaned = " ".join(str(reason).replace(str(ROOT), "<ROOT>").split())
        if cleaned and cleaned not in unique:
            unique.append(cleaned)
    if not unique:
        return "none"
    rendered = "; ".join(unique)
    return rendered if len(rendered) <= limit else rendered[:limit].rstrip() + "..."


def runtime_truth() -> dict[str, Any]:
    health_age = file_age_minutes(RUNTIME_HEALTH)
    try:
        health = json.loads(RUNTIME_HEALTH.read_text(encoding="utf-8"))
        if not isinstance(health, dict):
            raise ValueError("runtime health is not an object")
    except FileNotFoundError:
        return {
            "effective": "UNKNOWN",
            "reported": "UNKNOWN",
            "health_age": health_age,
            "supervisor_age": None,
            "control_owned": 0,
            "control_required": 7,
            "pipeline_healthy": None,
            "market_open": None,
            "market_state": "unknown",
            "market_reason": "runtime_health missing",
            "components": {},
            "reasons": ["runtime_health missing"],
        }
    except (OSError, UnicodeError, ValueError):
        return {
            "effective": "DEGRADED",
            "reported": "UNKNOWN",
            "health_age": health_age,
            "supervisor_age": None,
            "control_owned": 0,
            "control_required": 7,
            "pipeline_healthy": None,
            "market_open": None,
            "market_state": "unknown",
            "market_reason": "runtime_health corrupt",
            "components": {},
            "reasons": ["runtime_health corrupt"],
        }

    reported = str(health.get("bot_mode", "UNKNOWN")).upper()
    supervisor_age = age_minutes_from_timestamp(health.get("last_supervisor_run_utc"))
    control = health.get("control_plane") if isinstance(health.get("control_plane"), dict) else {}
    pipeline = health.get("pipeline_progress") if isinstance(health.get("pipeline_progress"), dict) else {}
    market_gate = health.get("market_gate") if isinstance(health.get("market_gate"), dict) else {}

    control_healthy = control.get("healthy") is True
    control_owned = safe_int(control.get("owned"), 0)
    control_required = safe_int(control.get("required"), 7)
    pipeline_healthy = pipeline.get("healthy")
    market_open = pipeline.get("market_open")
    components = pipeline.get("components") if isinstance(pipeline.get("components"), dict) else {}

    reasons: list[str] = []
    if health_age is None:
        reasons.append("runtime_health age unknown")
    elif health_age > RUNTIME_HEALTH_FRESH_MAX_MIN:
        reasons.append(f"runtime_health stale:{health_age}m")

    if supervisor_age is None:
        reasons.append("supervisor timestamp missing")
    elif supervisor_age < -2:
        reasons.append(f"supervisor timestamp future:{supervisor_age}m")
    elif supervisor_age > RUNTIME_HEALTH_FRESH_MAX_MIN:
        reasons.append(f"supervisor stale:{supervisor_age}m")

    if reported != "HEALTHY":
        reasons.append(f"reported mode:{reported}")
    if not control_healthy:
        reasons.append("control plane unhealthy")
    if pipeline_healthy is not True:
        reasons.append("pipeline progress unhealthy")

    for reason in health.get("failure_reasons") or []:
        reasons.append(f"runtime:{reason}")
    for reason in pipeline.get("failure_reasons") or []:
        reasons.append(f"pipeline:{reason}")

    effective = "HEALTHY" if not reasons else "DEGRADED"
    return {
        "effective": effective,
        "reported": reported,
        "health_age": health_age,
        "supervisor_age": supervisor_age,
        "control_owned": control_owned,
        "control_required": control_required,
        "pipeline_healthy": pipeline_healthy,
        "market_open": market_open,
        "market_state": str(health.get("market_state", market_gate.get("state", "unknown"))),
        "market_reason": str(market_gate.get("reason", "unknown")),
        "components": components,
        "reasons": reasons,
    }


def canonical_truth() -> dict[str, str]:
    unknown = {
        "status": "UNKNOWN",
        "hash": "UNKNOWN",
        "source": "unknown",
        "reason": "canonical verifier missing",
    }
    if not VERIFY_CANONICAL.exists():
        return unknown

    environment = os.environ.copy()
    if environment.get("DAILY_SUMMARY_ALLOW_CRONTAB_SOURCE_FILE") != "1":
        environment.pop("CRONTAB_SOURCE_FILE", None)

    try:
        result = subprocess.run(
            ["bash", str(VERIFY_CANONICAL)],
            cwd=str(ROOT),
            env=environment,
            text=True,
            capture_output=True,
            timeout=10,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {**unknown, "reason": "canonical verifier timeout"}
    except OSError as exc:
        return {**unknown, "reason": f"canonical verifier error:{type(exc).__name__}"}

    output = ((result.stdout or "") + "\n" + (result.stderr or ""))[-16000:]
    source = (
        "file"
        if "CRONTAB_READ_SOURCE=file" in output
        else "live"
        if "CRONTAB_READ_SOURCE=live" in output
        else "unknown"
    )
    pass_yes = "PHASE2_VERIFY_PASS=YES" in output
    pass_no = "PHASE2_VERIFY_PASS=NO" in output
    hash_yes = "BOTA_BLOCK_HASH_MATCH=YES" in output
    hash_no = "BOTA_BLOCK_HASH_MATCH=NO" in output

    if pass_yes and hash_yes:
        return {"status": "PASS", "hash": "YES", "source": source, "reason": "none"}
    if pass_no or hash_no:
        return {
            "status": "FAIL",
            "hash": "NO" if hash_no else "UNKNOWN",
            "source": source,
            "reason": "canonical verification failed",
        }
    return {
        "status": "UNKNOWN",
        "hash": "UNKNOWN",
        "source": source,
        "reason": f"canonical verifier rc={result.returncode}",
    }


def provider_truth() -> dict[str, Any]:
    data = load_json(PROVIDER_USAGE, {})
    if not isinstance(data, dict):
        data = {}
    state_day = str(data.get("utc_date", "unknown"))
    providers = data.get("providers") if isinstance(data.get("providers"), dict) else {}

    def counters(name: str) -> dict[str, Any]:
        value = providers.get(name)
        return value if isinstance(value, dict) else {}

    oanda = counters("oanda")
    yahoo = counters("yahoo")
    twelve = counters("twelvedata")
    current = state_day == TODAY

    return {
        "state_day": state_day,
        "current": current,
        "oanda_requests": safe_int(oanda.get("requests"), 0) if current else 0,
        "yahoo_requests": safe_int(yahoo.get("requests"), 0) if current else 0,
        "twelve_requests": safe_int(twelve.get("requests"), 0) if current else 0,
        "twelve_credits": safe_int(twelve.get("credits_consumed"), 0) if current else 0,
    }


def row_is_today(value: str) -> bool:
    text = str(value or "").strip()
    if text.startswith(TODAY):
        return True
    parsed = parse_utc(text)
    return bool(parsed and parsed.strftime("%Y-%m-%d") == TODAY)


def alert_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not ALERTS.exists():
        return rows
    try:
        with ALERTS.open("r", encoding="utf-8", errors="ignore", newline="") as handle:
            reader = csv.reader(handle)
            for row in reader:
                if not row or len(row) < 13:
                    continue
                if row[0].lower().startswith(("timestamp", "ts")):
                    continue
                if not row_is_today(row[0]):
                    continue
                direction = str(row[3]).strip().upper()
                rejected = str(row[10]).strip().lower() in {"true", "1", "yes", "y"}
                rows.append(
                    {
                        "pair": str(row[1]).strip(),
                        "timeframe": str(row[2]).strip(),
                        "direction": direction,
                        "score": safe_float(row[4], 0.0),
                        "rejected": rejected,
                        "filters": " ".join(str(row[11]).replace(" | ", " / ").split()) or "none",
                    }
                )
    except (OSError, UnicodeError, csv.Error):
        return rows
    return rows


def crond_status() -> str:
    try:
        result = subprocess.run(
            ["pgrep", "-x", "crond"],
            text=True,
            capture_output=True,
            timeout=3,
            check=False,
        )
        return "running" if result.returncode == 0 else "not_running"
    except (OSError, subprocess.TimeoutExpired):
        return "unknown"


def component_line(runtime: dict[str, Any]) -> str:
    if runtime["market_open"] is False:
        return "Pipeline jobs: market closed — freshness checks correctly suspended"
    components = runtime["components"]
    if not components:
        return "Pipeline jobs: no component detail"
    rendered: list[str] = []
    for name in sorted(components):
        value = components[name]
        if isinstance(value, dict):
            status = value.get("status") or ("PASS" if value.get("healthy") is True else "FAIL")
        else:
            status = value
        rendered.append(f"{name}={status}")
    return "Pipeline jobs: " + " | ".join(rendered[:8])


def best_line(row: dict[str, Any] | None) -> str:
    if row is None:
        return "none"
    state = "filter-rejected" if row["rejected"] else "filter-accepted"
    return (
        f"{row['pair']} {row['direction']} score={row['score']:.2f} "
        f"{state} filters={row['filters']}"
    )


runtime = runtime_truth()
canonical = canonical_truth()
provider = provider_truth()
rows = alert_rows()

tradeable = [row for row in rows if row["direction"] in {"BUY", "SELL"}]
holds = [row for row in rows if row["direction"] not in {"BUY", "SELL"}]
accepted = [row for row in tradeable if not row["rejected"]]
eligible = [row for row in accepted if row["score"] >= TELEGRAM_MIN_SCORE]
best = max(tradeable, key=lambda row: row["score"], default=None)

runtime_icon = {"HEALTHY": "✅", "DEGRADED": "⚠️", "UNKNOWN": "❓"}.get(
    runtime["effective"],
    "❓",
)
schedule_icon = (
    "✅"
    if canonical["status"] == "PASS" and canonical["hash"] == "YES"
    else "⚠️"
)
pipeline_label = (
    "PASS"
    if runtime["pipeline_healthy"] is True
    else "FAIL"
    if runtime["pipeline_healthy"] is False
    else "UNKNOWN"
)

clock = load_json(CLOCK_STATE, {})
if not isinstance(clock, dict):
    clock = {}

reasons = list(runtime["reasons"])
if canonical["status"] != "PASS" or canonical["hash"] != "YES":
    reasons.append(canonical["reason"])

lines: list[str] = [
    f"{runtime_icon} BotA Daily Proof — {TODAY}",
    f"Generated: {NOW_UTC}",
    "",
    (
        f"Runtime: {runtime_icon} {runtime['effective']} | reported={runtime['reported']} | "
        f"control={runtime['control_owned']}/{runtime['control_required']} | "
        f"pipeline={pipeline_label}"
    ),
    (
        f"Supervisor: {fmt_age(runtime['supervisor_age'])} ago | "
        f"health file: {fmt_age(runtime['health_age'])} ago"
    ),
    f"Market: {runtime['market_state']} | reason={runtime['market_reason']}",
    component_line(runtime),
    (
        f"Runtime schedule: {schedule_icon} {canonical['status']} | "
        f"hash={canonical['hash']} | source={canonical['source']} | "
        f"crond={crond_status()}"
    ),
    "",
    (
        f"Scans: {len(rows)} | actionable BUY/SELL: {len(tradeable)} | "
        f"HOLD/no-trade: {len(holds)} | Telegram eligible: {len(eligible)}"
    ),
    f"Best candidate: {best_line(best)}",
    "",
    (
        f"Provider usage: OANDA {provider['oanda_requests']} req | "
        f"Yahoo {provider['yahoo_requests']} req | "
        f"Twelve Data {provider['twelve_credits']}/{TWELVE_DATA_DAILY_LIMIT} credits "
        f"({provider['twelve_requests']} req; reserve {TWELVE_DATA_RESERVE})"
    ),
    (
        f"Clock: {clock.get('status', 'UNKNOWN')} | "
        f"drift={clock.get('drift_seconds', 'UNKNOWN')}s | "
        f"server_ok={str(clock.get('server_clock_ok', 'UNKNOWN')).lower()} | "
        f"local_unsafe={str(clock.get('local_clock_unsafe', 'UNKNOWN')).lower()}"
    ),
    f"Reasons: {compact_reasons(reasons)}",
    "",
    "Strategy unchanged | thresholds unchanged | production trading behavior unchanged",
]

print("\n".join(lines))
PY
)"

echo "$SUMMARY"

SEND_RESULT="$(tg_send_plain "$SUMMARY" || true)"

{
  echo "[$(ts_utc)] DAILY_PROOF_OF_WORK"
  echo "$SEND_RESULT"
  echo "$SUMMARY"
  echo
} >> "${LOGDIR}/daily_summary.log"

echo "$SEND_RESULT"

exit 0
