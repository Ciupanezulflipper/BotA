#!/usr/bin/env python3
"""Launch BotA heartbeat with boot-time and signal-first notification policy.

Android's CLOCK_BOOTTIME includes suspended time. The active shadow service
persists useful-progress timestamps in that domain, so deadman age must be
computed against the same clock.

Routine hourly heartbeat evidence is recorded locally only. Deadman alerts and
recovery messages remain delegated to the unified runtime and its existing
bounded Telegram delivery state. This adapter never changes trading strategy,
services, crontab, providers, or Supabase.
"""

from __future__ import annotations

import argparse
import os
import time
from pathlib import Path
from types import ModuleType
from typing import Callable

try:
    from tools import heartbeat_runtime
except ModuleNotFoundError:  # Direct execution from tools/ on Termux.
    import heartbeat_runtime  # type: ignore[no-redef]


class _BootTimeClock:
    """Expose the monotonic interface expected by heartbeat_runtime."""

    @staticmethod
    def monotonic() -> float:
        """Return CLOCK_BOOTTIME when available, else standard monotonic time."""
        clock = getattr(time, "CLOCK_BOOTTIME", None)
        if clock is None:
            return time.monotonic()
        return time.clock_gettime(clock)


def record_local_heartbeat(
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
    """Record an hourly heartbeat bucket locally without Telegram delivery."""
    del root, state_path, now_monotonic, current_boot_id

    bucket = heartbeat_runtime.utc_bucket(server_epoch)
    try:
        last_bucket = bucket_path.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError):
        last_bucket = ""

    if bucket == last_bucket:
        heartbeat_runtime.emit(log_path, "HB_UTC_RESULT=BUCKET_UNCHANGED")
        return

    if dry_run:
        heartbeat_runtime.emit(log_path, "HB_UTC_RESULT=DRY_RUN_LOG_ONLY")
        return

    heartbeat_runtime.atomic_write_text(bucket_path, f"{bucket}\n")
    heartbeat_runtime.emit(
        log_path,
        f"HB_UTC_RESULT=LOG_ONLY sources={source_count}",
    )


def run(root: Path) -> int:
    """Run one clock-consistent cycle with routine heartbeat delivery muted."""
    original_clock: ModuleType = heartbeat_runtime.time
    original_heartbeat: Callable[..., None] = heartbeat_runtime.handle_heartbeat
    try:
        heartbeat_runtime.time = _BootTimeClock()  # type: ignore[assignment]
        heartbeat_runtime.handle_heartbeat = record_local_heartbeat
        return heartbeat_runtime.run_cycle(root)
    finally:
        heartbeat_runtime.handle_heartbeat = original_heartbeat
        heartbeat_runtime.time = original_clock


def main() -> int:
    """Parse the BotA root and run one signal-first heartbeat cycle."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(
            os.environ.get("BOTA_MUTABLE_ROOT")
            or os.environ.get("BOTA_CODE_ROOT")
            or os.environ.get("BOTA_ROOT")
            or Path.home() / "BotA"
        ),
    )
    args = parser.parse_args()
    return run(args.root.expanduser())


if __name__ == "__main__":
    raise SystemExit(main())
