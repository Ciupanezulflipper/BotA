#!/usr/bin/env python3
"""Build and deliver BotA's process heartbeat with monotonic retry control.

The heartbeat confirms Telegram reachability and reports the latest local runtime
summary. It does not determine trading eligibility and does not mutate services.
"""

from __future__ import annotations

import argparse
import fcntl
import json
import math
import os
import re
import tempfile
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
MAX_RESPONSE_BYTES = 65536
MAX_FAILURE_COUNT = 1_000_000
BOOT_ID_PATH = Path("/proc/sys/kernel/random/boot_id")
ENV_KEY_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def utc_timestamp() -> str:
    """Return a log timestamp in UTC."""
    return time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())


def compact_detail(value: Any) -> str:
    """Return a single-line bounded diagnostic string."""
    return str(value).replace("\r", " ").replace("\n", "|")[:MAX_DETAIL_CHARS]


def append_log(path: Path, message: str) -> None:
    """Append one heartbeat log line."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"[{utc_timestamp()}] {compact_detail(message)}\n")


def finite_number(value: Any) -> float | None:
    """Convert a value to a finite non-negative float."""
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if number < 0.0 or not math.isfinite(number):
        return None
    return number


def non_negative_int(value: Any) -> int:
    """Convert a value to a bounded non-negative integer, or return zero."""
    try:
        number = int(value)
    except (TypeError, ValueError, OverflowError):
        return 0
    return min(max(0, number), MAX_FAILURE_COUNT)


def boot_identity() -> str:
    """Return the current boot identifier when the platform exposes one."""
    configured = os.environ.get("HEARTBEAT_BOOT_ID", "").strip()
    if configured:
        return configured[:128]
    try:
        return BOOT_ID_PATH.read_text(encoding="ascii").strip()[:128]
    except (OSError, UnicodeError):
        return ""


def parse_env_file(path: Path) -> dict[str, str]:
    """Read simple ASCII KEY=VALUE entries without executing shell content."""
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
        if ENV_KEY_PATTERN.fullmatch(key) is None:
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

    mode = compact_detail(data.get("bot_mode") or "UNKNOWN")
    market = compact_detail(data.get("market_state") or "unknown")
    control_value = data.get("control_plane")
    pipeline_value = data.get("pipeline_progress")
    control = control_value if isinstance(control_value, dict) else {}
    pipeline = pipeline_value if isinstance(pipeline_value, dict) else {}

    owned = compact_detail(control.get("owned", "?"))
    required = compact_detail(control.get("required", 7))
    running = compact_detail(control.get("running", "?"))
    orphaned = compact_detail(control.get("orphaned", "?"))
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
        summarized = [compact_detail(item)[:80] for item in failures[:4]]
        parts.append("failures=" + "|".join(summarized))
    return " | ".join(parts)


def default_state() -> dict[str, Any]:
    """Return a new heartbeat-delivery state document."""
    return {
        "schema_version": "1.0",
        "boot_id": "",
        "delivery_failure": False,
        "consecutive_failures": 0,
        "last_attempt_monotonic": 0.0,
        "last_success_monotonic": 0.0,
        "next_retry_monotonic": 0.0,
        "last_error": "",
    }


def normalize_state(data: dict[str, Any]) -> dict[str, Any]:
    """Return a typed, internally consistent delivery-state document."""
    last_attempt = finite_number(data.get("last_attempt_monotonic")) or 0.0
    last_success = finite_number(data.get("last_success_monotonic")) or 0.0
    next_retry = finite_number(data.get("next_retry_monotonic")) or 0.0
    if last_attempt == 0.0:
        next_retry = 0.0
    elif next_retry < last_attempt:
        next_retry = last_attempt

    delivery_failure = data.get("delivery_failure") is True
    consecutive_failures = non_negative_int(data.get("consecutive_failures"))
    last_error = compact_detail(data.get("last_error") or "")
    if not delivery_failure:
        consecutive_failures = 0
        last_error = ""

    return {
        "schema_version": "1.0",
        "boot_id": compact_detail(data.get("boot_id") or "")[:128],
        "delivery_failure": delivery_failure,
        "consecutive_failures": consecutive_failures,
        "last_attempt_monotonic": last_attempt,
        "last_success_monotonic": last_success,
        "next_retry_monotonic": next_retry,
        "last_error": last_error,
    }


def load_state(path: Path) -> dict[str, Any]:
    """Load persisted retry state, resetting corrupt content safely."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return default_state()
    if not isinstance(data, dict):
        return default_state()
    return normalize_state(data)


def reset_after_reboot(
    state: dict[str, Any],
    now_monotonic: float,
    current_boot_id: str,
) -> dict[str, Any]:
    """Reset persisted monotonic values when a new Android boot is detected."""
    normalized = normalize_state(state)
    recorded_boot_id = str(normalized.get("boot_id") or "")
    if recorded_boot_id and current_boot_id and recorded_boot_id != current_boot_id:
        return default_state()

    latest_recorded = max(
        float(normalized["last_attempt_monotonic"]),
        float(normalized["last_success_monotonic"]),
    )
    if now_monotonic < latest_recorded:
        return default_state()
    return normalized


def retry_delay(consecutive_failures: int) -> float:
    """Return bounded exponential backoff for a failed delivery."""
    exponent = max(0, min(consecutive_failures - 1, 4))
    delay = FAILURE_BACKOFF_BASE_SEC * (2**exponent)
    return min(delay, FAILURE_BACKOFF_MAX_SEC)


def suppression_reason(state: dict[str, Any], now_monotonic: float) -> tuple[str, float]:
    """Return suppression reason and remaining seconds, or empty reason."""
    normalized = normalize_state(state)
    next_retry = float(normalized["next_retry_monotonic"])
    if now_monotonic >= next_retry:
        return "", 0.0
    remaining = next_retry - now_monotonic
    reason = "failure_backoff" if normalized["delivery_failure"] is True else "success_interval"
    return reason, remaining


def write_state(path: Path, state: dict[str, Any]) -> None:
    """Atomically persist normalized heartbeat delivery state."""
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = normalize_state(state)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f"{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary_path = Path(handle.name)
            json.dump(normalized, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
        temporary_path = None
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink()
            except OSError:
                pass


def record_success(
    state: dict[str, Any],
    now_monotonic: float,
    current_boot_id: str,
) -> dict[str, Any]:
    """Return state after a successful Telegram heartbeat."""
    updated = normalize_state(state)
    updated.update(
        {
            "boot_id": current_boot_id,
            "delivery_failure": False,
            "consecutive_failures": 0,
            "last_attempt_monotonic": now_monotonic,
            "last_success_monotonic": now_monotonic,
            "next_retry_monotonic": now_monotonic + SUCCESS_INTERVAL_SEC,
            "last_error": "",
        }
    )
    return normalize_state(updated)


def record_failure(
    state: dict[str, Any],
    now_monotonic: float,
    current_boot_id: str,
    detail: str,
) -> dict[str, Any]:
    """Return state after a failed Telegram heartbeat."""
    updated = normalize_state(state)
    count = min(int(updated["consecutive_failures"]) + 1, MAX_FAILURE_COUNT)
    delay = retry_delay(count)
    updated.update(
        {
            "boot_id": current_boot_id,
            "delivery_failure": True,
            "consecutive_failures": count,
            "last_attempt_monotonic": now_monotonic,
            "next_retry_monotonic": now_monotonic + delay,
            "last_error": compact_detail(detail),
        }
    )
    return normalize_state(updated)


def read_response_body(response: Any) -> str:
    """Read and bound a Telegram response body."""
    raw = response.read(MAX_RESPONSE_BYTES + 1)
    truncated = len(raw) > MAX_RESPONSE_BYTES
    body = raw[:MAX_RESPONSE_BYTES].decode("utf-8", errors="replace")
    if truncated:
        body += "...[truncated]"
    return body


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
    request = urllib.request.Request(
        api_url,
        data=encoded,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout_sec) as response:
            status = response.getcode()
            body = read_response_body(response)
    except urllib.error.HTTPError as exc:
        body = read_response_body(exc)
        return False, compact_detail(f"http_error:{exc.code}:{body}")
    except urllib.error.URLError as exc:
        return False, compact_detail(f"url_error:{exc.reason}")
    except TimeoutError:
        return False, "timeout"
    except OSError as exc:
        return False, compact_detail(f"os_error:{type(exc).__name__}:{exc}")

    if status != 200:
        return False, compact_detail(f"http_status:{status}:{body}")
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return False, compact_detail(f"invalid_json:{body}")
    if isinstance(payload, dict) and payload.get("ok") is True:
        return True, f"http_status:{status}"
    return False, compact_detail(f"telegram_rejected:{body}")


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
        current_boot_id = boot_identity()
        state = reset_after_reboot(load_state(state_path), now_monotonic, current_boot_id)
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
            failed_state = record_failure(state, now_monotonic, current_boot_id, detail)
            write_state(state_path, failed_state)
            append_log(
                log_path,
                f"heartbeat failed: {detail} | next_retry_monotonic={failed_state['next_retry_monotonic']}",
            )
            return 0

        api_url = f"https://api.telegram.org/bot{token}/sendMessage"
        text = (
            f"BotA process heartbeat — {summary}\n"
            "This confirms Telegram reachability only; runtime fields above are local evidence."
        )
        success, detail = send_telegram(api_url, chat_id, text, timeout_from_env())
        if success:
            write_state(state_path, record_success(state, now_monotonic, current_boot_id))
            append_log(log_path, f"heartbeat sent: {summary} | {detail}")
        else:
            failed_state = record_failure(state, now_monotonic, current_boot_id, detail)
            write_state(state_path, failed_state)
            append_log(
                log_path,
                f"heartbeat failed: {detail} | next_retry_monotonic={failed_state['next_retry_monotonic']}",
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
