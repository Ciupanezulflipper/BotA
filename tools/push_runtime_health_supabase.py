#!/usr/bin/env python3
"""
BotA Phase 5 runtime-health sender.

Purpose:
  Build a sanitized BotA runtime-health payload from local runtime state and
  optionally POST it to the Supabase Edge Function. Supports two independent
  producers that share one wire contract:

    - termux:   reads state/runtime_health.json (bota_supervisor.sh output).
    - hetzner:  reads state/vps_orchestrator_health.json (vps_orchestrator.py
                output) and derives an equivalent sanitized payload.

  Source selection is explicit (--source/BOTA_HEALTH_SOURCE) or auto-detected
  from which state file is present. Neither path is removed or weakened by
  the other; this keeps Android control/observation-only operation intact.

Security:
  - Does not use or store the privileged Supabase database key on Termux or
    Hetzner.
  - Uses only the limited BOTA_HEALTH_INGEST_SECRET when --send is explicitly used.
  - Default mode is dry-run.
  - Does not include raw runtime_health.json/vps_orchestrator_health.json,
    env, shell output, tokens, or secrets.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

TERMUX_BOT_ID = "bota-termux-primary"
HETZNER_BOT_ID = "bota-hetzner-primary"
ALLOWED_SOURCES = ("termux", "hetzner")

DEFAULT_FUNCTION_URL = "https://ozgkeslgjqbqfewojnmr.supabase.co/functions/v1/bot-health-ingest"
DEFAULT_SECRET_ENV = "BOTA_HEALTH_INGEST_SECRET"
MAX_TEXT = 240
ALLOWED_BOT_MODES = {"HEALTHY", "DEGRADED", "UNKNOWN"}

# Termux (state/runtime_health.json) field layout — unchanged.
CACHE_FIELDS = [
    "eurusd_m15_cache_age_min",
    "gbpusd_m15_cache_age_min",
    "eurusd_h1_cache_age_min",
    "gbpusd_h1_cache_age_min",
]

AGE_FIELDS = [
    "watcher_log_age_min",
    "updater_log_age_min",
    "shadow_log_age_min",
]

TEXT_FIELDS = [
    "failure_reasons",
    "last_degraded_reason",
]

TIMESTAMP_FIELDS = [
    "last_supervisor_run_utc",
    "last_degraded_utc",
    "last_healthy_utc",
]

# Hetzner (state/vps_orchestrator_health.json) mapping.
#
# Two distinct job sets, deliberately kept separate:
#
# JOB_TO_AGE_FIELD: every job whose freshness is *reported* via the legacy
# Termux *_log_age_min field names. This includes "shadow" purely for
# visibility — shadow is the shadow-reopen measurement/research job, not
# part of live delivery (see vps_orchestrator.py's own comment on
# R5_LIVE_DELIVERY_JOBS: "watcher, profitlab_delivery, closer,
# daily_summary_server_gate" are the only four approved live-delivery jobs;
# shadow is explicitly grouped with heartbeat/runtime_health_push/market_pulse
# as non-delivery). Its age is still worth surfacing, it just must never
# gate bot_mode.
#
# REQUIRED_LIVE_JOBS: the jobs that actually gate bot_mode HEALTHY/DEGRADED.
# This is "updater" (upstream data feeding watcher) plus three of the four
# orchestrator-approved live-delivery jobs — watcher (signal production),
# closer (lifecycle/SL-TP closure), and profitlab_delivery (the job that
# actually publishes to Supabase/ProfitLab, i.e. the consumer of this very
# payload). daily_summary_server_gate is a once-daily batch report, not a
# continuous health signal, so it is intentionally excluded from gating too.
REQUIRED_LIVE_JOBS = ("updater", "watcher", "closer", "profitlab_delivery")
JOB_TO_AGE_FIELD = {
    "updater": "updater_log_age_min",
    "watcher": "watcher_log_age_min",
    "shadow": "shadow_log_age_min",
    "closer": "closer_log_age_min",
}
# Same (pair, timeframe) -> cache file convention actually used in
# production by tools/data_fetch_candles.sh (OUT_JSON="${CACHE_DIR}/${PAIR}_${TF}.json")
# as invoked from tools/indicators_updater.sh, where CACHE_DIR="${MUTABLE_ROOT}/cache".
# root here resolves the same way (repo_root() prefers BOTA_MUTABLE_ROOT), so
# this matches the real writer path, not just tools/sltp_monitor.py's
# same-shaped but differently-rooted (BOTA_ROOT) convention.
CACHE_FIELD_SOURCE = {
    "eurusd_m15_cache_age_min": ("EURUSD", "M15"),
    "gbpusd_m15_cache_age_min": ("GBPUSD", "M15"),
    "eurusd_h1_cache_age_min": ("EURUSD", "H1"),
    "gbpusd_h1_cache_age_min": ("GBPUSD", "H1"),
}
# No Hetzner-native equivalent exists yet for these historical Termux fields.
# Emitting null is preferable to fabricating degraded/healthy reasoning that
# the orchestrator's health file cannot actually support.
HETZNER_NULL_FIELDS = (
    "failure_reasons",
    "last_degraded_utc",
    "last_degraded_reason",
    "last_healthy_utc",
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def repo_root() -> Path:
    configured = os.environ.get("BOTA_MUTABLE_ROOT")
    fallback = os.environ.get("BOTA_CODE_ROOT") or os.environ.get("BOTA_ROOT")
    return Path(configured or fallback or Path(__file__).resolve().parents[1]).expanduser()


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError(f"{path} did not contain a JSON object")

    return data


def file_age_min(path: Path) -> int | None:
    if not path.exists():
        return None

    now = datetime.now(timezone.utc).timestamp()
    age = int((now - path.stat().st_mtime) // 60)

    if age < 0:
        return 0
    if age > 100000:
        return 100000
    return age


def non_negative_int(value: Any) -> int | None:
    if value is None or value == "":
        return None

    try:
        number = int(float(value))
    except (TypeError, ValueError):
        return None

    if number < 0:
        return None
    if number > 100000:
        return 100000
    return number


def parse_timestamp(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None

    text = value.strip()
    if text.endswith("Z"):
        candidate = text.replace("Z", "+00:00")
    else:
        candidate = text

    try:
        dt = datetime.fromisoformat(candidate)
    except ValueError:
        return None

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def age_minutes_from_iso(value: Any, now: datetime | None = None) -> int | None:
    """Minutes elapsed since an ISO-8601 timestamp. None if missing/unparseable.

    Fail-closed: unlike file_age_min (mtime-based), this never guesses an age
    for data that was never produced — a job absent from useful_progress
    yields None, not 0.
    """
    if not isinstance(value, str) or not value.strip():
        return None

    text = value.strip()
    candidate = text[:-1] + "+00:00" if text.endswith("Z") else text

    try:
        dt = datetime.fromisoformat(candidate)
    except ValueError:
        return None

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    reference = now or datetime.now(timezone.utc)
    age = int((reference.astimezone(timezone.utc) - dt.astimezone(timezone.utc)).total_seconds() // 60)

    if age < 0:
        return 0
    if age > 100000:
        return 100000
    return age


def sanitize_text(value: Any) -> str | None:
    if value is None or value == "":
        return None

    if isinstance(value, list):
        text = "|".join(str(x) for x in value)
    else:
        text = str(value)

    text = text[:MAX_TEXT]
    text = re.sub(r"Bearer\s+[A-Za-z0-9._-]+", "Bearer [redacted]", text, flags=re.I)
    text = re.sub(r"eyJ[A-Za-z0-9._-]{20,}", "[redacted-jwt]", text)
    text = re.sub(r"SUPABASE_[A-Z_]+", "[redacted-env-name]", text)
    text = re.sub(r"TELEGRAM_[A-Z_]+", "[redacted-env-name]", text)
    text = text.replace("/data/data/com.termux/files/home/BotA", "$BOTA_ROOT")

    return text or None


def detect_source(root: Path, override: str | None = None) -> str:
    """Resolve which producer to use. Explicit override wins; otherwise the
    presence of each host's state file decides. Fails closed (raises) when
    neither state file exists rather than guessing a producer."""
    if override:
        candidate = override.strip().lower()
        if candidate not in ALLOWED_SOURCES:
            raise ValueError(f"UNKNOWN_HEALTH_SOURCE={candidate}")
        return candidate

    env_override = os.environ.get("BOTA_HEALTH_SOURCE", "").strip().lower()
    if env_override in ALLOWED_SOURCES:
        return env_override

    if (root / "state" / "vps_orchestrator_health.json").exists():
        return "hetzner"
    if (root / "state" / "runtime_health.json").exists():
        return "termux"

    raise RuntimeError("NO_HEALTH_SOURCE_FOUND")


def build_payload_termux(root: Path) -> dict[str, Any]:
    health_path = root / "state" / "runtime_health.json"
    health = load_json(health_path)

    mode = str(health.get("bot_mode") or "UNKNOWN")
    if mode not in ALLOWED_BOT_MODES:
        mode = "UNKNOWN"

    payload: dict[str, Any] = {
        "payload_version": "v1",
        "bot_id": TERMUX_BOT_ID,
        "observed_at_utc": utc_now_iso(),
        "bot_mode": mode,
    }

    for field in TIMESTAMP_FIELDS:
        payload[field] = parse_timestamp(health.get(field))

    for field in AGE_FIELDS:
        payload[field] = non_negative_int(health.get(field))

    payload["closer_log_age_min"] = file_age_min(root / "logs" / "cron.closer.log")

    for field in CACHE_FIELDS:
        payload[field] = non_negative_int(health.get(field))

    for field in TEXT_FIELDS:
        payload[field] = sanitize_text(health.get(field))

    return payload


def derive_hetzner_bot_mode(health: dict[str, Any]) -> tuple[str, list[str]]:
    """Fail-closed bot_mode derivation from vps_orchestrator_health.json.

    HEALTHY is only ever returned when process_liveness is True, lifecycle
    is exactly "RUNNING", and every REQUIRED_LIVE_JOBS entry (updater,
    watcher, closer, profitlab_delivery) is both present and neither stale
    nor terminally failed. "shadow" is deliberately NOT in that gating set —
    it is a research/measurement job, not part of live delivery, and its
    own staleness or failure must never change bot_mode; its age is still
    surfaced separately via shadow_log_age_min. Any missing/malformed
    required field returns UNKNOWN (we don't know); any known-bad condition
    (process not live, lifecycle not running, a required live job stale or
    failed) returns DEGRADED (we know something is wrong). HEALTHY is never
    guessed.
    """
    required_top = ("process_liveness", "lifecycle", "useful_progress", "stale_useful_progress")
    if not isinstance(health, dict) or any(key not in health for key in required_top):
        return "UNKNOWN", ["missing_required_fields"]

    process_liveness = health["process_liveness"]
    lifecycle = health["lifecycle"]
    useful_progress = health["useful_progress"]
    stale = health["stale_useful_progress"]

    if (
        not isinstance(process_liveness, bool)
        or not isinstance(lifecycle, str)
        or not isinstance(useful_progress, dict)
        or not isinstance(stale, dict)
    ):
        return "UNKNOWN", ["malformed_required_fields"]

    if process_liveness is not True:
        return "DEGRADED", ["process_not_live"]

    if lifecycle != "RUNNING":
        return "DEGRADED", [f"lifecycle_{lifecycle.lower()}"]

    reasons: list[str] = []
    for job in REQUIRED_LIVE_JOBS:
        if job not in useful_progress or job not in stale:
            return "UNKNOWN", [f"missing_job_progress:{job}"]

        if stale.get(job) is True:
            reasons.append(f"stale:{job}")
            continue

        record = useful_progress.get(job)
        status = record.get("status") if isinstance(record, dict) else None
        if status not in ("PASS", "RUNNING"):
            reasons.append(f"status:{job}={status}")

    if reasons:
        return "DEGRADED", reasons

    return "HEALTHY", []


def build_payload_hetzner(root: Path) -> dict[str, Any]:
    health_path = root / "state" / "vps_orchestrator_health.json"
    health = load_json(health_path)

    mode, _reasons = derive_hetzner_bot_mode(health)
    useful_progress = health.get("useful_progress")
    if not isinstance(useful_progress, dict):
        useful_progress = {}

    payload: dict[str, Any] = {
        "payload_version": "v1",
        "bot_id": HETZNER_BOT_ID,
        "observed_at_utc": utc_now_iso(),
        "bot_mode": mode,
        "last_supervisor_run_utc": parse_timestamp(health.get("last_loop_progress_utc")),
    }

    for job, field in JOB_TO_AGE_FIELD.items():
        record = useful_progress.get(job)
        finished_at = record.get("finished_at_utc") if isinstance(record, dict) else None
        payload[field] = age_minutes_from_iso(finished_at)

    for field, (pair, timeframe) in CACHE_FIELD_SOURCE.items():
        payload[field] = file_age_min(root / "cache" / f"{pair}_{timeframe}.json")

    for field in HETZNER_NULL_FIELDS:
        payload[field] = None

    return payload


def build_payload(root: Path, source: str | None = None) -> dict[str, Any]:
    resolved = detect_source(root, override=source)
    if resolved == "hetzner":
        return build_payload_hetzner(root)
    return build_payload_termux(root)


def post_payload(url: str, secret: str, payload: dict[str, Any]) -> tuple[int, str]:
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")

    request = urllib.request.Request(
        url=url,
        data=body,
        method="POST",
        headers={
            "content-type": "application/json",
            "x-bota-health-secret": secret,
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            status = int(response.status)
            text = response.read().decode("utf-8", errors="replace")
            return status, text
    except urllib.error.HTTPError as exc:
        text = exc.read().decode("utf-8", errors="replace")
        return int(exc.code), text


def main() -> int:
    parser = argparse.ArgumentParser(description="Build or send BotA runtime health payload.")
    parser.add_argument("--send", action="store_true", help="POST payload to Edge Function. Default is dry-run.")
    parser.add_argument("--url", default=os.environ.get("BOTA_HEALTH_INGEST_URL", DEFAULT_FUNCTION_URL))
    parser.add_argument("--secret-env", default=DEFAULT_SECRET_ENV)
    parser.add_argument(
        "--source",
        choices=("auto", "termux", "hetzner"),
        default=os.environ.get("BOTA_HEALTH_SOURCE", "auto"),
        help="Which producer to read. Default auto-detects from the state file present.",
    )
    args = parser.parse_args()

    root = repo_root()
    source_override = None if args.source == "auto" else args.source
    payload = build_payload(root, source=source_override)

    if not args.send:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0

    secret = os.environ.get(args.secret_env, "")
    if not secret:
        print(f"SEND_BLOCKED_MISSING_ENV={args.secret_env}", file=sys.stderr)
        return 2

    status, text = post_payload(args.url, secret, payload)
    print(json.dumps({"http_status": status, "response": text}, indent=2, sort_keys=True))

    if 200 <= status < 300:
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
