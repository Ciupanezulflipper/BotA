#!/usr/bin/env python3
"""Build and deliver BotA's process heartbeat with monotonic retry control.

The heartbeat confirms Telegram reachability and reports the latest local runtime
summary. It does not determine trading eligibility and does not mutate services.
"""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


SUCCESS_INTERVAL_SEC = 3600.0
FAILURE_BACKOFF_BASE_SEC = 300.0
FAILURE_BACKOFF_MAX_SEC = 3600.0
DEFAULT_TIMEOUT_SEC = 15.0
MAX_DETAIL_CHARS = 300


def utc_timestamp() -> str:
    """Return a log timestamp in UTC."""
    return time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())


def append_log(path: Path, message: str) -> None:
    """Append one heartbeat log line."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"[{utc_timestamp()}] {message}\n")


def finite_number(value: Any) -> float | None:
    """Convert a value to a finite non-negative float."""
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if number < 0.0 or number != number or number in (float("inf"), float("-inf")):
        return None
    return number


def parse_env_file(path: Path) -> dict[str, str]:
    """Read simple KEY=VALUE entries without executing shell content."""
    values: dict[str, str] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        return values

    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key or not key.replace("_", "A").isalnum() or key[0].isdigit():
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        values[key] = value
    return values


def build_summary(path: Path) -> str:
    """Build a stable summary from the latest runtime-health document."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return "mode=UNKNOWN | runtime_health.json missing or unreadable"
    if not isinstance(data, dict):
        return "mode=UNKNOWN | runtime_health.json invalid"

    mode = str(data.get("bot_mode") or "UNKNOWN")
    market = str(data.get("market_state") or "unknown")
    control_value = data.get("control_plane")
    pipeline_value = data.get("pipeline_progress")
    control = control_value if isinstance(control_value, dict) else {}
    pipeline = pipeline_value if isinstance(pipeline_value, dict) else {}

    owned = control.get("owned", "?")
    required = control.get("required", 7)
    running = control.get("running", "?")
    orphaned = control.get("orphaned", "?")
    progress_ok = pipeline.get("healthy")
    if progress_ok is True:
        progress = "PASS"
    elif progress_ok is False:
        progress = "FAIL"
    else:
        progress = "UNKNOWN"

    parts = [
        f"mode={mode}",
        f"market={market}",
        f"owned={owned}/{required}",
        f"running={running}/{required}",
        f"orphaned={orphaned}",
        f"useful_progress={progress}",
    ]

    failures = data.get("failure_reasons")
    if isinstance(failures, list) and failures:
        parts.append("failures=" + "|".join(str(item) for item in failures[:4]))
    return " | ".join(parts)


def default_state() -> dict[str, Any]:
    """Return a new heartbeat-delivery state document."""
    return {
        "schema_version": "1.0",
        "delivery_failure": False,
        "consecutive_failures": 0,
        "last_attempt_monotonic": 0.0,
        "last_success_monotonic": 0.0,
        "next_retry_monotonic": 0.0,
        "last_error": "",
    }


def load_state(path: Path) -> dict[str, Any]:
    """Load persisted retry state, resetting corrupt content safely."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return default_state()
    if not isinstance(data, dict):
        return default_state()

    state = default_state()
    state.update(data)
    return state


def reset_after_reboot(state: dict[str, Any], now_monotonic: float) -> dict[str, Any]:
    """Reset persisted monotonic values when a new Android boot is detected."""
    last_attempt = finite_number(state.get("last_attempt_monotonic"))
    next_retry = finite_number(state.get("next_retry_monotonic"))
    if last_attempt is None or next_retry is None:
        return default_state()
    if now_monotonic < last_attempt or now_monotonic < next_retry - FAILURE_BACKOFF_MAX_SEC:
        return default_state()
    return state


def retry_delay(consecutive_failures: int) -> float:
    """Return bounded exponential backoff for a failed delivery."""
    exponent = max(0, min(consecutive_failures - 1, 4))
    delay = FAILURE_BACKOFF_BASE_SEC * (2**exponent)
    return min(delay, FAILURE_BACKOFF_MAX_SEC)


def suppression_reason(state: dict[str, Any], now_monotonic: float) -> tuple[str, float]:
    """Return suppression reason and remaining seconds, or empty reason."""
    next_retry = finite_number(state.get("next_retry_monotonic"))
    if next_retry is None or now_monotonic >= next_retry:
        return "", 0.0
    remaining = next_retry - now_monotonic
    reason = "failure_backoff" if state.get("delivery_failure") is True else "success_interval"
    return reason, remaining


def write_state(path: Path, state: dict[str, Any]) -> None:
    """Atomically persist heartbeat delivery state."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    try:
        temporary.write_text(
            json.dumps(state, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, path)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def record_success(state: dict[str, Any], now_monotonic: float) -> dict[str, Any]:
    """Return state after a successful Telegram heartbeat."""
    updated = dict(state)
    updated.update(
        {
            "schema_version": "1.0",
            "delivery_failure": False,
            "consecutive_failures": 0,
            "last_attempt_monotonic": now_monotonic,
            "last_success_monotonic": now_monotonic,
            "next_retry_monotonic": now_monotonic + SUCCESS_INTERVAL_SEC,
            "last_error": "",
        }
    )
    return updated


def record_failure(
    state: dict[str, Any],
    now_monotonic: float,
    detail: str,
) -> dict[str, Any]:
    """Return state after a failed Telegram heartbeat."""
    previous_failures = state.get("consecutive_failures")
    try:
        count = max(0, int(previous_failures)) + 1
    except (TypeError, ValueError, OverflowError):
        count = 1
    delay = retry_delay(count)
    updated = dict(state)
    updated.update(
        {
            "schema_version": "1.0",
            "delivery_failure": True,
            "consecutive_failures": count,
            "last_attempt_monotonic": now_monotonic,
            "next_retry_monotonic": now_monotonic + delay,
            "last_error": detail[:MAX_DETAIL_CHARS],
        }
    )
    return updated


def send_telegram(
    api_url: str,
    chat_id: str,
    text: str,
    timeout_sec: float,
) -> tuple[bool, str]:
    """Perform one bounded Telegram send and return success plus diagnostics."""
    encoded = urllib.parse.urlencode(
        {
            "chat_id": chat_id,
            "disable_web_page_preview": "true",
            "text": text,
        }
    ).encode("utf-8")
    request = urllib.request.Request(api_url, data=encoded, method="POST")

    try:
        with urllib.request.urlopen(request, timeout=timeout_sec) as response:
            status = response.getcode()
            body = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return False, f"http_error:{exc.code}:{body[:MAX_DETAIL_CHARS]}"
    except urllib.error.URLError as exc:
        return False, f"url_error:{str(exc.reason)[:MAX_DETAIL_CHARS]}"
    except TimeoutError:
        return False, "timeout"
    except OSError as exc:
        return False, f"os_error:{type(exc).__name__}:{str(exc)[:MAX_DETAIL_CHARS]}"

    if status != 200:
        return False, f"http_status:{status}:{body[:MAX_DETAIL_CHARS]}"
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return False, f"invalid_json:{body[:MAX_DETAIL_CHARS]}"
    if isinstance(payload, dict) and payload.get("ok") is True:
        return True, f"http_status:{status}"
    return False, f"telegram_rejected:{body[:MAX_DETAIL_CHARS]}"


def timeout_from_env() -> float:
    """Return a bounded Telegram timeout from environment configuration."""
    configured = finite_number(os.environ.get("HEARTBEAT_TELEGRAM_TIMEOUT_SEC"))
    if configured is None:
        return DEFAULT_TIMEOUT_SEC
    return min(max(configured, 1.0), 30.0)


def run_cycle(root: Path) -> int:
    """Run one locked heartbeat summary and optional delivery cycle."""
    log_path = root / "logs" / "cron.heartbeat.log"
    health_path = root / "state" / "runtime_health.json"
    state_path = root / "state" / "heartbeat_delivery.json"
    lock_path = root / "state" / "heartbeat_delivery.lock"
    tele_path = root / "config" / "tele.env"

    state_path.parent.mkdir(parents=True, exist_ok=True)
    summary = build_summary(health_path)
    append_log(log_path, f"heartbeat summary: {summary}")

    if os.environ.get("HEARTBEAT_DRY_RUN") == "1":
        print(summary)
        append_log(log_path, "DRY_RUN: heartbeat rendered; Telegram not called")
        return 0

    with lock_path.open("a+", encoding="utf-8") as lock_handle:
        try:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            append_log(log_path, "delivery cycle skipped: lock_busy")
            return 0

        now_monotonic = time.monotonic()
        state = reset_after_reboot(load_state(state_path), now_monotonic)
        force_send = os.environ.get("HEARTBEAT_FORCE_SEND") == "1"
        reason, remaining = suppression_reason(state, now_monotonic)
        if reason and not force_send:
            append_log(
                log_path,
                f"delivery suppressed: reason={reason} next_retry_in_sec={remaining:.0f}",
            )
            return 0

        env_values = parse_env_file(tele_path)
        token = env_values.get("TELEGRAM_BOT_TOKEN", "")
        chat_id = env_values.get("TELEGRAM_CHAT_ID", "")
        if not token or not chat_id:
            detail = "telegram_config_missing"
            write_state(state_path, record_failure(state, now_monotonic, detail))
            append_log(log_path, f"heartbeat failed: {detail}")
            return 0

        api_url = f"https://api.telegram.org/bot{token}/sendMessage"
        text = (
            f"BotA process heartbeat — {summary}\n"
            "This confirms Telegram reachability only; runtime fields above are local evidence."
        )
        success, detail = send_telegram(api_url, chat_id, text, timeout_from_env())
        if success:
            write_state(state_path, record_success(state, now_monotonic))
            append_log(log_path, f"heartbeat sent: {summary} | {detail}")
        else:
            failed_state = record_failure(state, now_monotonic, detail)
            write_state(state_path, failed_state)
            retry_at = failed_state["next_retry_monotonic"]
            append_log(
                log_path,
                f"heartbeat failed: {detail} | next_retry_monotonic={retry_at}",
            )
    return 0


def main() -> int:
    """Parse arguments and run one heartbeat cycle."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(os.environ.get("BOTA_ROOT", str(Path.home() / "BotA"))),
    )
    args = parser.parse_args()
    return run_cycle(args.root.expanduser())


if __name__ == "__main__":
    raise SystemExit(main())
