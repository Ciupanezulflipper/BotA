#!/usr/bin/env python3
"""
BotA Phase 5 runtime-health sender.

Purpose:
  Build a sanitized BotA runtime-health payload from local Termux state and
  optionally POST it to the Supabase Edge Function.

Security:
  - Does not use or store the privileged Supabase database key on Termux.
  - Uses only the limited BOTA_HEALTH_INGEST_SECRET when --send is explicitly used.
  - Default mode is dry-run.
  - Does not include raw runtime_health.json, env, shell output, tokens, or secrets.
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

BOT_ID = "bota-termux-primary"
DEFAULT_FUNCTION_URL = "https://ozgkeslgjqbqfewojnmr.supabase.co/functions/v1/bot-health-ingest"
DEFAULT_SECRET_ENV = "BOTA_HEALTH_INGEST_SECRET"
MAX_TEXT = 240
ALLOWED_BOT_MODES = {"HEALTHY", "DEGRADED", "UNKNOWN"}

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


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


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


def build_payload(root: Path) -> dict[str, Any]:
    health_path = root / "state" / "runtime_health.json"
    health = load_json(health_path)

    mode = str(health.get("bot_mode") or "UNKNOWN")
    if mode not in ALLOWED_BOT_MODES:
        mode = "UNKNOWN"

    payload: dict[str, Any] = {
        "payload_version": "v1",
        "bot_id": BOT_ID,
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
    args = parser.parse_args()

    root = repo_root()
    payload = build_payload(root)

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
