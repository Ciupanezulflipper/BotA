#!/usr/bin/env python3
"""Ensure the native control-plane watchdog remains alive.

This guard is deliberately narrower than the watchdog itself. It never signals
BotA services and never performs topology reconciliation. In --ensure mode it
may invoke the reviewed watchdog launcher only when there are exactly zero
watchdog processes and zero lock holders. Ambiguous states fail closed.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Callable

if __package__:
    from tools import native_service_daemon_migration as migration
else:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from tools import native_service_daemon_migration as migration


class GuardError(RuntimeError):
    """Raised when watchdog liveness cannot be proven or restored safely."""


def state_for(pids: list[int], holders: list[int]) -> str:
    """Classify exact watchdog/lock ownership without mutation."""
    unique_pids = sorted(set(pids))
    unique_holders = sorted(set(holders))
    if len(unique_pids) > 1:
        raise GuardError(f"watchdog_process_ambiguous:{unique_pids}")
    if len(unique_holders) > 1:
        raise GuardError(f"watchdog_lock_ambiguous:{unique_holders}")
    if len(unique_pids) == 1:
        if unique_holders != unique_pids:
            raise GuardError(
                f"watchdog_lock_owner_mismatch:pids={unique_pids}:holders={unique_holders}"
            )
        return "healthy"
    if unique_holders:
        raise GuardError(f"watchdog_lock_without_process:{unique_holders}")
    return "absent"


def wait_until(
    predicate: Callable[[], bool], timeout: float, interval: float = 0.25
) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return predicate()


def append_event(path: Path, event: str, **details: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "event": event,
        "monotonic_ns": time.monotonic_ns(),
        **details,
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")


def arguments() -> argparse.Namespace:
    root = Path(os.environ.get("BOTA_ROOT", str(Path.home() / "BotA")))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ensure", action="store_true")
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--root", type=Path, default=root)
    return parser.parse_args()


def main() -> int:
    args = arguments()
    root = args.root.resolve()
    watchdog = root / "tools/native_service_daemon_watchdog.py"
    launcher = root / "tools/start_native_service_daemon_watchdog.sh"
    lock = root / "state/native_service_daemon_watchdog.lock"
    log = root / "logs/native_watchdog_guard.jsonl"

    if not watchdog.is_file():
        print(f"WATCHDOG_GUARD=FAIL:watchdog_missing:{watchdog}", file=sys.stderr)
        return 2
    if not launcher.is_file() or not os.access(launcher, os.X_OK):
        print(f"WATCHDOG_GUARD=FAIL:launcher_invalid:{launcher}", file=sys.stderr)
        return 2

    def snapshot() -> tuple[list[int], list[int], str]:
        pids = migration.process_matches(watchdog)
        holders = migration.lock_holders(lock)
        return pids, holders, state_for(pids, holders)

    try:
        pids, holders, state = snapshot()
        if state == "healthy":
            append_event(log, "guard_healthy", watchdog_pid=pids[0])
            print(f"WATCHDOG_GUARD=HEALTHY:pid={pids[0]}")
            return 0
        if not args.ensure:
            append_event(log, "guard_absent_check_only")
            print("WATCHDOG_GUARD=ABSENT")
            return 3

        append_event(log, "guard_relaunch_requested")
        result = subprocess.run(
            [str(launcher)],
            text=True,
            capture_output=True,
            check=False,
            timeout=max(args.timeout, 1.0),
        )
        if result.returncode:
            detail = (result.stderr or result.stdout).strip()[:240]
            raise GuardError(
                f"launcher_failed:rc={result.returncode}:detail={detail}"
            )

        def ready() -> bool:
            try:
                current_pids, current_holders, current_state = snapshot()
            except GuardError:
                return False
            return (
                current_state == "healthy"
                and len(current_pids) == 1
                and current_holders == current_pids
            )

        if not wait_until(ready, args.timeout):
            final_pids = migration.process_matches(watchdog)
            final_holders = migration.lock_holders(lock)
            raise GuardError(
                "watchdog_relaunch_timeout:"
                f"pids={final_pids}:holders={final_holders}"
            )

        final_pids, final_holders, _ = snapshot()
        append_event(log, "guard_relaunch_success", watchdog_pid=final_pids[0])
        print(f"WATCHDOG_GUARD=RECOVERED:pid={final_pids[0]}")
        return 0
    except (GuardError, OSError, subprocess.TimeoutExpired) as exc:
        append_event(log, "guard_failed", error=str(exc))
        print(f"WATCHDOG_GUARD=FAIL:{exc}", file=sys.stderr)
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
