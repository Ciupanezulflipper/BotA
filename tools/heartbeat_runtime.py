#!/usr/bin/env python3
"""Run BotA heartbeat, deadman, and recovery delivery through one controller.

The controller preserves authoritative UTC hour buckets and monotonic deadman
semantics while reusing the existing bounded Telegram transport and retry-state
helpers. It never mutates services, crontab, strategy, providers, or Supabase.
"""

from __future__ import annotations

import argparse
import fcntl
import http.client
import os
import statistics
import tempfile
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Literal

try:
    from tools import heartbeat_delivery as delivery
except ModuleNotFoundError:  # Direct execution from tools/ on Termux.
    import heartbeat_delivery as delivery  # type: ignore[no-redef]


DEFAULT_DEADMAN_STALE_SEC = 90 * 60
MIN_DEADMAN_STALE_SEC = 60
MAX_DEADMAN_STALE_SEC = 24 * 60 * 60
DEFAULT_SERVER_TIMEOUT_SEC = 8.0
DEFAULT_SERVER_TARGETS = (
    ("www.google.com", "/"),
    ("api-fxpractice.oanda.com", "/"),
    ("query1.finance.yahoo.com", "/"),
)
ACTIVE_SESSION_START_HOUR_UTC = 7
ACTIVE_SESSION_END_HOUR_UTC = 20

EventOutcome = Literal["sent", "failed", "suppressed", "dry_run"]


def atomic_write_text(path: Path, value: str, mode: int = 0o600) -> None:
    """Atomically write one small text artifact."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.chmod(mode)
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            try:
                temporary.unlink()
            except OSError:
                pass


def emit(log_path: Path, marker: str) -> None:
    """Write one stable result marker to stdout and the heartbeat log."""
    print(marker)
    delivery.append_log(log_path, marker)


def bounded_deadman_stale_seconds() -> float:
    """Return a bounded deadman threshold from environment configuration."""
    configured = delivery.finite_number(os.environ.get("HEARTBEAT_DEADMAN_STALE_SEC"))
    if configured is None:
        return float(DEFAULT_DEADMAN_STALE_SEC)
    return min(max(configured, MIN_DEADMAN_STALE_SEC), MAX_DEADMAN_STALE_SEC)


def server_timeout_seconds() -> float:
    """Return a bounded timeout for authoritative UTC endpoints."""
    configured = delivery.finite_number(os.environ.get("HEARTBEAT_SERVER_TIMEOUT_SEC"))
    if configured is None:
        return DEFAULT_SERVER_TIMEOUT_SEC
    return min(max(configured, 1.0), 15.0)


def _read_server_date(host: str, path: str, timeout: float) -> int | None:
    """Read a Date header from one fixed HTTPS clock target."""
    connection: http.client.HTTPSConnection | None = None
    try:
        connection = http.client.HTTPSConnection(host, timeout=timeout)
        connection.request(
            "GET",
            path,
            headers={"User-Agent": "BotA-heartbeat/1.0"},
        )
        response = connection.getresponse()
        raw_date = str(response.getheader("Date") or "").strip()
        response.read(1)
    except (OSError, http.client.HTTPException, ValueError):
        return None
    finally:
        if connection is not None:
            try:
                connection.close()
            except OSError:
                pass

    if not raw_date:
        return None
    try:
        parsed = parsedate_to_datetime(raw_date)
    except (TypeError, ValueError, OverflowError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return int(parsed.astimezone(timezone.utc).timestamp())


def authoritative_server_epoch() -> tuple[int | None, int]:
    """Return median server UTC epoch and the number of valid fixed endpoints."""
    configured = delivery.finite_number(os.environ.get("HEARTBEAT_SERVER_EPOCH"))
    if configured is not None:
        return int(configured), 1

    epochs = [
        epoch
        for host, path in DEFAULT_SERVER_TARGETS
        if (epoch := _read_server_date(host, path, server_timeout_seconds())) is not None
    ]
    if not epochs:
        return None, 0
    return int(statistics.median(epochs)), len(epochs)


def utc_bucket(epoch: int) -> str:
    """Return the authoritative UTC hour bucket key."""
    return datetime.fromtimestamp(epoch, timezone.utc).strftime("%Y%m%d%H")


def utc_display(epoch: int) -> str:
    """Return a human-readable authoritative UTC timestamp."""
    return datetime.fromtimestamp(epoch, timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def active_session(epoch: int) -> bool:
    """Return whether trusted UTC is inside BotA's 07:00-20:00 weekday session."""
    now = datetime.fromtimestamp(epoch, timezone.utc)
    return (
        now.weekday() < 5
        and ACTIVE_SESSION_START_HOUR_UTC <= now.hour < ACTIVE_SESSION_END_HOUR_UTC
    )


def telegram_credentials(root: Path) -> tuple[str, str]:
    """Read scoped Telegram credentials without sourcing shell files."""
    runtime = delivery.parse_env_file(root / ".env.runtime")
    configured = delivery.parse_env_file(root / "config" / "tele.env")
    values = {**runtime, **configured}
    return (
        values.get("TELEGRAM_BOT_TOKEN", ""),
        values.get("TELEGRAM_CHAT_ID", ""),
    )


def failure_backoff_remaining(state: dict[str, object], now_monotonic: float) -> float:
    """Return remaining failure backoff while ignoring success-interval state."""
    normalized = delivery.normalize_state(state)
    if normalized["delivery_failure"] is not True:
        return 0.0
    next_retry = float(normalized["next_retry_monotonic"])
    return max(0.0, next_retry - now_monotonic)


def attempt_event(
    *,
    root: Path,
    message: str,
    state_path: Path,
    now_monotonic: float,
    current_boot_id: str,
    dry_run: bool,
) -> tuple[EventOutcome, str]:
    """Attempt one event with its own persisted monotonic backoff state."""
    state = delivery.reset_after_reboot(
        delivery.load_state(state_path),
        now_monotonic,
        current_boot_id,
    )
    remaining = failure_backoff_remaining(state, now_monotonic)
    if remaining > 0.0:
        return "suppressed", f"failure_backoff_remaining_sec={remaining:.0f}"
    if dry_run:
        return "dry_run", "telegram_not_called"

    token, chat_id = telegram_credentials(root)
    if not token or not chat_id:
        detail = "telegram_config_missing"
        delivery.write_state(
            state_path,
            delivery.record_failure(
                state,
                now_monotonic,
                current_boot_id,
                detail,
            ),
        )
        return "failed", detail

    success, detail = delivery.send_telegram(
        f"https://api.telegram.org/bot{token}/sendMessage",
        chat_id,
        message,
        delivery.timeout_from_env(),
    )
    if success:
        delivery.write_state(
            state_path,
            delivery.record_success(state, now_monotonic, current_boot_id),
        )
        return "sent", detail

    delivery.write_state(
        state_path,
        delivery.record_failure(
            state,
            now_monotonic,
            current_boot_id,
            detail,
        ),
    )
    return "failed", detail


def progress_age_seconds(
    path: Path,
    current_boot_id: str,
    now_monotonic: float,
) -> tuple[str, float | None]:
    """Return monotonic progress status and age without using wall-clock time."""
    try:
        fields = path.read_text(encoding="utf-8").split()
    except (OSError, UnicodeError):
        return "missing", None
    if len(fields) < 2:
        return "invalid", None
    progress_boot = fields[0].strip()
    try:
        progress_monotonic = float(fields[1])
    except (TypeError, ValueError, OverflowError):
        return "invalid", None
    if progress_monotonic < 0.0:
        return "invalid", None
    if current_boot_id and progress_boot and progress_boot != current_boot_id:
        return "boot_changed", None
    age = now_monotonic - progress_monotonic
    if age < 0.0:
        return "invalid", None
    return "valid", age


def last_shadow_display(path: Path) -> str:
    """Return the latest shadow-manager display timestamp for local diagnostics."""
    try:
        line = path.read_text(encoding="utf-8").splitlines()[-1]
    except (OSError, UnicodeError, IndexError):
        return "display timestamp unavailable"
    value = line.split("|", 1)[0].strip()
    return value or "display timestamp unavailable"


def handle_heartbeat(
    *,
    root: Path,
    log_path: Path,
    bucket_path: Path,
    state_path: Path,
    server_epoch: int,
    source_count: int,
    now_monotonic: float,
    current_boot_id: str,
    dry_run: bool,
) -> None:
    """Evaluate and deliver one authoritative UTC heartbeat bucket."""
    bucket = utc_bucket(server_epoch)
    try:
        last_bucket = bucket_path.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError):
        last_bucket = ""
    if bucket == last_bucket:
        emit(log_path, "HB_UTC_RESULT=BUCKET_UNCHANGED")
        return

    summary = delivery.build_summary(root / "state" / "runtime_health.json")
    message = f"💓 Heartbeat — BotA alive at {utc_display(server_epoch)}\n{summary}"
    outcome, detail = attempt_event(
        root=root,
        message=message,
        state_path=state_path,
        now_monotonic=now_monotonic,
        current_boot_id=current_boot_id,
        dry_run=dry_run,
    )
    if outcome == "sent":
        atomic_write_text(bucket_path, f"{bucket}\n")
        emit(log_path, f"HB_UTC_RESULT=PASS sources={source_count}")
    elif outcome == "dry_run":
        emit(log_path, "HB_UTC_RESULT=DRY_RUN")
    elif outcome == "suppressed":
        emit(log_path, f"HB_UTC_RESULT=RETRY_SUPPRESSED {detail}")
    else:
        emit(log_path, f"HB_UTC_RESULT=DELIVERY_FAILED {delivery.compact_detail(detail)}")


def emit_progress_error(log_path: Path, status: str) -> bool:
    """Emit one progress error marker and return whether evaluation must stop."""
    markers = {
        "missing": "DEADMAN_UTC_RESULT=MONOTONIC_PROGRESS_MISSING",
        "boot_changed": "DEADMAN_UTC_RESULT=BOOT_CHANGED_WAITING_FOR_PROGRESS",
        "invalid": "DEADMAN_UTC_RESULT=MONOTONIC_PROGRESS_INVALID",
    }
    marker = markers.get(status)
    if marker is None:
        return False
    emit(log_path, marker)
    return True


def handle_stale_progress(
    *,
    root: Path,
    log_path: Path,
    deadman_flag: Path,
    deadman_state: Path,
    server_epoch: int,
    age_seconds: float,
    last_display: str,
    now_monotonic: float,
    current_boot_id: str,
    dry_run: bool,
) -> None:
    """Deliver or suppress a deadman alert for stale in-session progress."""
    if deadman_flag.exists():
        emit(log_path, "DEADMAN_UTC_RESULT=ALREADY_ALERTED")
        return
    age_minutes = int(age_seconds // 60)
    message = (
        "⚠️ BOTA · SCAN DELAYED\n"
        f"No fresh pipeline progress for {age_minutes} min.\n"
        "BotA will not present stale data as a valid setup."
    )
    outcome, detail = attempt_event(
        root=root,
        message=message,
        state_path=deadman_state,
        now_monotonic=now_monotonic,
        current_boot_id=current_boot_id,
        dry_run=dry_run,
    )
    if outcome == "sent":
        atomic_write_text(
            deadman_flag,
            f"scan|server_utc={utc_display(server_epoch)}|last_shadow={last_display}\n",
        )
        emit(log_path, "DEADMAN_UTC_RESULT=ALERT_SENT")
    elif outcome == "dry_run":
        emit(log_path, "DEADMAN_UTC_RESULT=DRY_RUN_ALERT")
    elif outcome == "suppressed":
        emit(log_path, f"DEADMAN_UTC_RESULT=RETRY_SUPPRESSED {detail}")
    else:
        emit(log_path, f"DEADMAN_UTC_RESULT=DELIVERY_FAILED {delivery.compact_detail(detail)}")


def handle_recovery(
    *,
    root: Path,
    log_path: Path,
    deadman_flag: Path,
    recovery_state: Path,
    last_display: str,
    now_monotonic: float,
    current_boot_id: str,
    dry_run: bool,
) -> None:
    """Deliver or suppress a concise recovery after a prior deadman alert."""
    if not deadman_flag.exists():
        emit(log_path, "DEADMAN_UTC_RESULT=HEALTHY")
        return
    message = "✅ BOTA · SCAN RESTORED\nFresh pipeline progress has resumed."
    outcome, detail = attempt_event(
        root=root,
        message=message,
        state_path=recovery_state,
        now_monotonic=now_monotonic,
        current_boot_id=current_boot_id,
        dry_run=dry_run,
    )
    if outcome == "sent":
        try:
            deadman_flag.unlink()
        except FileNotFoundError:
            pass
        emit(log_path, "DEADMAN_UTC_RESULT=RECOVERY_SENT")
    elif outcome == "dry_run":
        emit(log_path, "DEADMAN_UTC_RESULT=DRY_RUN_RECOVERY")
    elif outcome == "suppressed":
        emit(log_path, f"DEADMAN_UTC_RESULT=RECOVERY_RETRY_SUPPRESSED {detail}")
    else:
        emit(log_path, f"DEADMAN_UTC_RESULT=RECOVERY_DELIVERY_FAILED {delivery.compact_detail(detail)}")


def handle_deadman(
    *,
    root: Path,
    log_path: Path,
    deadman_flag: Path,
    deadman_state: Path,
    recovery_state: Path,
    progress_path: Path,
    shadow_display_path: Path,
    server_epoch: int,
    now_monotonic: float,
    current_boot_id: str,
    dry_run: bool,
) -> None:
    """Evaluate monotonic useful progress and dispatch deadman or recovery."""
    status, age_seconds = progress_age_seconds(
        progress_path,
        current_boot_id,
        now_monotonic,
    )
    if emit_progress_error(log_path, status):
        return
    if age_seconds is None:
        emit(log_path, "DEADMAN_UTC_RESULT=MONOTONIC_PROGRESS_INVALID")
        return

    last_display = last_shadow_display(shadow_display_path)
    if age_seconds > bounded_deadman_stale_seconds():
        if not active_session(server_epoch):
            emit(log_path, "DEADMAN_UTC_RESULT=SKIP_OUTSIDE_SESSION")
            return
        handle_stale_progress(
            root=root,
            log_path=log_path,
            deadman_flag=deadman_flag,
            deadman_state=deadman_state,
            server_epoch=server_epoch,
            age_seconds=age_seconds,
            last_display=last_display,
            now_monotonic=now_monotonic,
            current_boot_id=current_boot_id,
            dry_run=dry_run,
        )
        return
    handle_recovery(
        root=root,
        log_path=log_path,
        deadman_flag=deadman_flag,
        recovery_state=recovery_state,
        last_display=last_display,
        now_monotonic=now_monotonic,
        current_boot_id=current_boot_id,
        dry_run=dry_run,
    )


def run_cycle(root: Path) -> int:
    """Run one locked heartbeat and deadman/recovery evaluation cycle."""
    logs = root / "logs"
    state = root / "state"
    log_path = logs / "cron.heartbeat.log"
    bucket_path = logs / "state" / "heartbeat_utc_bucket.txt"
    deadman_flag = logs / "state" / "deadman.flag"
    lock_path = state / "heartbeat_delivery.lock"

    state.mkdir(parents=True, exist_ok=True)
    (logs / "state").mkdir(parents=True, exist_ok=True)
    dry_run = os.environ.get("HEARTBEAT_DRY_RUN") == "1"

    with lock_path.open("a+", encoding="utf-8") as lock_handle:
        try:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            emit(log_path, "HEARTBEAT_RUNTIME_RESULT=LOCK_BUSY")
            return 0

        server_epoch, source_count = authoritative_server_epoch()
        if server_epoch is None:
            emit(log_path, "HB_UTC_RESULT=FAIL_SERVER_UTC")
            emit(log_path, "DEADMAN_UTC_RESULT=SKIP_SERVER_UTC")
            return 0

        now_monotonic = time.monotonic()
        current_boot_id = delivery.boot_identity()
        handle_heartbeat(
            root=root,
            log_path=log_path,
            bucket_path=bucket_path,
            state_path=state / "heartbeat_delivery.json",
            server_epoch=server_epoch,
            source_count=source_count,
            now_monotonic=now_monotonic,
            current_boot_id=current_boot_id,
            dry_run=dry_run,
        )
        handle_deadman(
            root=root,
            log_path=log_path,
            deadman_flag=deadman_flag,
            deadman_state=state / "deadman_delivery.json",
            recovery_state=state / "recovery_delivery.json",
            progress_path=state / "shadow_progress.monotonic",
            shadow_display_path=logs / "shadow_manager_heartbeat.txt",
            server_epoch=server_epoch,
            now_monotonic=now_monotonic,
            current_boot_id=current_boot_id,
            dry_run=dry_run,
        )
    return 0


def main() -> int:
    """Parse arguments and run one heartbeat-runtime cycle."""
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
