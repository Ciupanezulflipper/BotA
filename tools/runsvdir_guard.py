#!/usr/bin/env python3
"""Keep one detached Termux runsvdir manager and repair orphaned BotA supervisors."""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable, Sequence

SERVICES = (
    "bota-updater",
    "bota-watcher",
    "bota-closer",
    "bota-shadow",
    "bota-heartbeat",
    "bota-supervisor",
    "crond",
)


class GuardError(RuntimeError):
    """Raised when a safe control-plane recovery cannot proceed."""


def process_table() -> dict[int, dict[str, Any]]:
    """Return readable process parentage and argv from procfs."""
    table: dict[int, dict[str, Any]] = {}
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            raw = (entry / "stat").read_text(errors="replace")
            fields = raw[raw.rfind(")") + 2 :].split()
            argv = [
                item.decode(errors="replace")
                for item in (entry / "cmdline").read_bytes().split(b"\0")
                if item
            ]
            table[int(entry.name)] = {"ppid": int(fields[1]), "argv": argv}
        except (OSError, ValueError, IndexError):
            continue
    return table


def basename(row: dict[str, Any]) -> str:
    """Return process executable basename."""
    argv = row.get("argv") or []
    return Path(argv[0]).name if argv else ""


def manager_pids(
    table: dict[int, dict[str, Any]],
    service_root: Path,
) -> list[int]:
    """Return exact standard runsvdir managers for the service root."""
    root_text = str(service_root)
    return [
        pid
        for pid, row in table.items()
        if basename(row) == "runsvdir"
        and root_text in " ".join(row.get("argv", [])[1:])
    ]


def runsv_rows(
    table: dict[int, dict[str, Any]],
    service: str,
) -> list[tuple[int, dict[str, Any]]]:
    """Return exact runsv rows for one service."""
    return [
        (pid, row)
        for pid, row in table.items()
        if basename(row) == "runsv"
        and (row.get("argv") or [])[-1:] == [service]
    ]


def topology(
    table: dict[int, dict[str, Any]],
    service_root: Path,
    services: Sequence[str] = SERVICES,
) -> dict[str, Any]:
    """Classify manager ownership without mutating the runtime."""
    managers = manager_pids(table, service_root)
    manager = managers[0] if len(managers) == 1 else None
    rows: dict[str, dict[str, Any]] = {}
    for service in services:
        candidates = runsv_rows(table, service)
        pid = candidates[0][0] if len(candidates) == 1 else None
        ppid = candidates[0][1]["ppid"] if len(candidates) == 1 else None
        if manager is not None and ppid == manager:
            owner = "manager"
        elif ppid == 1:
            owner = "pid1_orphan"
        else:
            owner = "other_or_missing"
        rows[service] = {
            "runsv_count": len(candidates),
            "runsv_pid": pid,
            "runsv_ppid": ppid,
            "owner": owner,
        }
    return {
        "manager_count": len(managers),
        "manager_pid": manager,
        "services": rows,
        "owned": sum(row["owner"] == "manager" for row in rows.values()),
        "orphaned": sum(row["owner"] == "pid1_orphan" for row in rows.values()),
        "invalid": sum(row["owner"] == "other_or_missing" for row in rows.values()),
        "duplicates": sum(row["runsv_count"] > 1 for row in rows.values()),
    }


def read_boot_id() -> str:
    """Return the current Android/Linux boot identifier."""
    try:
        return Path("/proc/sys/kernel/random/boot_id").read_text().strip()
    except OSError:
        return "unknown"


def monotonic_ns() -> int:
    """Return boot-relative monotonic nanoseconds."""
    clock = getattr(time, "CLOCK_BOOTTIME", time.CLOCK_MONOTONIC)
    return time.clock_gettime_ns(clock)


def append_event(log_path: Path, event: str, **details: Any) -> None:
    """Append a compact JSON event."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "event": event,
        "boot_id": read_boot_id(),
        "monotonic_ns": monotonic_ns(),
        **details,
    }
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")


def run_sv(
    sv_binary: Path,
    service_root: Path,
    service: str,
    command: str,
    timeout: int,
) -> subprocess.CompletedProcess[str]:
    """Run one bounded sv command."""
    return subprocess.run(
        [
            str(sv_binary),
            "-w",
            str(timeout),
            command,
            str(service_root / service),
        ],
        text=True,
        capture_output=True,
        check=False,
        timeout=timeout + 5,
    )


def service_running(
    sv_binary: Path,
    service_root: Path,
    service: str,
) -> bool:
    """Return whether sv reports the service wrapper as running."""
    try:
        result = subprocess.run(
            [str(sv_binary), "status", str(service_root / service)],
            text=True,
            capture_output=True,
            check=False,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0 and (result.stdout or "").startswith("run:")


def wait_for(
    predicate: Callable[[], bool],
    timeout: float,
    interval: float = 0.25,
) -> bool:
    """Wait using monotonic time only."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return predicate()


def launch_manager(
    runsvdir_binary: Path,
    service_root: Path,
    manager_log: Path,
) -> int:
    """Launch runsvdir detached from the invoking shell."""
    manager_log.parent.mkdir(parents=True, exist_ok=True)
    handle = manager_log.open("ab", buffering=0)
    try:
        process = subprocess.Popen(
            [str(runsvdir_binary), "-P", str(service_root)],
            stdin=subprocess.DEVNULL,
            stdout=handle,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            close_fds=True,
        )
    finally:
        handle.close()
    return process.pid


def ensure_one_manager(
    service_root: Path,
    runsvdir_binary: Path,
    manager_log: Path,
    settle_seconds: float,
    table_fn: Callable[[], dict[int, dict[str, Any]]] = process_table,
) -> int:
    """Return the manager PID, launching one only when none exists."""
    current = manager_pids(table_fn(), service_root)
    if len(current) > 1:
        raise GuardError(f"multiple_managers:{len(current)}")
    if len(current) == 1:
        return current[0]

    launched_pid = launch_manager(runsvdir_binary, service_root, manager_log)

    def manager_ready() -> bool:
        return len(manager_pids(table_fn(), service_root)) == 1

    if not wait_for(manager_ready, settle_seconds):
        raise GuardError(f"manager_start_timeout:launched_pid={launched_pid}")
    managers = manager_pids(table_fn(), service_root)
    if len(managers) != 1:
        raise GuardError(f"manager_count_after_start:{len(managers)}")
    return managers[0]


def handoff_orphan(
    service: str,
    manager_pid: int,
    service_root: Path,
    sv_binary: Path,
    timeout: int,
    table_fn: Callable[[], dict[int, dict[str, Any]]] = process_table,
) -> None:
    """Stop one orphaned runsv and require manager-owned replacement."""
    before = runsv_rows(table_fn(), service)
    if len(before) != 1 or before[0][1]["ppid"] != 1:
        raise GuardError(f"orphan_precondition_changed:{service}")

    down = run_sv(sv_binary, service_root, service, "down", timeout)
    if down.returncode != 0:
        raise GuardError(
            f"sv_down_failed:{service}:rc={down.returncode}:"
            f"{(down.stdout or down.stderr).strip()}"
        )
    exit_result = run_sv(sv_binary, service_root, service, "exit", timeout)
    if exit_result.returncode != 0:
        raise GuardError(
            f"sv_exit_failed:{service}:rc={exit_result.returncode}:"
            f"{(exit_result.stdout or exit_result.stderr).strip()}"
        )

    def manager_acquired() -> bool:
        rows = runsv_rows(table_fn(), service)
        return len(rows) == 1 and rows[0][1]["ppid"] == manager_pid

    if not wait_for(manager_acquired, timeout):
        raise GuardError(f"manager_acquire_timeout:{service}")

    if not wait_for(
        lambda: service_running(sv_binary, service_root, service),
        timeout,
    ):
        raise GuardError(f"service_restart_timeout:{service}")


def reconcile_once(
    service_root: Path,
    sv_binary: Path,
    runsvdir_binary: Path,
    manager_log: Path,
    settle_seconds: float,
    command_timeout: int,
    table_fn: Callable[[], dict[int, dict[str, Any]]] = process_table,
) -> dict[str, Any]:
    """Repair a missing manager or orphaned required supervisors once."""
    first = topology(table_fn(), service_root)
    if first["manager_count"] > 1:
        raise GuardError(f"multiple_managers:{first['manager_count']}")
    if first["duplicates"]:
        raise GuardError(f"duplicate_runsv_rows:{first['duplicates']}")

    manager = ensure_one_manager(
        service_root,
        runsvdir_binary,
        manager_log,
        settle_seconds,
        table_fn=table_fn,
    )

    for service in SERVICES:
        current = topology(table_fn(), service_root)
        if current["manager_count"] != 1 or current["manager_pid"] != manager:
            raise GuardError("manager_changed_during_recovery")
        row = current["services"][service]
        if row["runsv_count"] > 1:
            raise GuardError(f"duplicate_runsv:{service}")
        if row["owner"] == "pid1_orphan":
            handoff_orphan(
                service,
                manager,
                service_root,
                sv_binary,
                command_timeout,
                table_fn=table_fn,
            )

    final = topology(table_fn(), service_root)
    if (
        final["manager_count"] != 1
        or final["owned"] != len(SERVICES)
        or final["orphaned"] != 0
        or final["invalid"] != 0
        or final["duplicates"] != 0
    ):
        raise GuardError(
            "topology_not_reconciled:"
            f"manager_count={final['manager_count']};"
            f"owned={final['owned']}/{len(SERVICES)};"
            f"orphaned={final['orphaned']};"
            f"invalid={final['invalid']};"
            f"duplicates={final['duplicates']}"
        )
    return final


def acquire_lock(lock_path: Path) -> Any:
    """Acquire an exclusive nonblocking process-lifetime lock."""
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    handle = lock_path.open("a+")
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        handle.close()
        raise GuardError("guard_already_running") from None
    return handle


def which(command: str) -> str | None:
    """Return an executable from PATH."""
    for directory in os.environ.get("PATH", "").split(os.pathsep):
        candidate = Path(directory) / command
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def request_wake_lock() -> None:
    """Request a best-effort Termux wake lock."""
    command = which("termux-wake-lock")
    if not command:
        return
    subprocess.run(
        [command],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
        timeout=10,
    )


def parse_args() -> argparse.Namespace:
    """Parse runtime options."""
    prefix = Path(os.environ.get("PREFIX", "/data/data/com.termux/files/usr"))
    root = Path(os.environ.get("BOTA_ROOT", str(Path.home() / "BotA")))
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--service-root",
        type=Path,
        default=prefix / "var" / "service",
    )
    parser.add_argument(
        "--sv-binary",
        type=Path,
        default=prefix / "bin" / "sv",
    )
    parser.add_argument(
        "--runsvdir-binary",
        type=Path,
        default=prefix / "bin" / "runsvdir",
    )
    parser.add_argument(
        "--lock",
        type=Path,
        default=root / "state" / "runsvdir_guard.lock",
    )
    parser.add_argument(
        "--log",
        type=Path,
        default=root / "logs" / "runsvdir_guard.jsonl",
    )
    parser.add_argument(
        "--manager-log",
        type=Path,
        default=root / "logs" / "runsvdir_manager.log",
    )
    parser.add_argument("--poll-seconds", type=float, default=5.0)
    parser.add_argument("--settle-seconds", type=float, default=15.0)
    parser.add_argument("--command-timeout", type=int, default=30)
    parser.add_argument("--once", action="store_true")
    return parser.parse_args()


def main() -> int:
    """Run the durable guard loop."""
    args = parse_args()
    for path in (args.sv_binary, args.runsvdir_binary):
        if not path.is_file() or not os.access(path, os.X_OK):
            print(f"GUARD_BINARY_INVALID={path}", file=sys.stderr)
            return 2

    try:
        lock_handle = acquire_lock(args.lock)
    except GuardError as exc:
        print(f"RUNSVDIR_GUARD={exc}", file=sys.stderr)
        return 0 if str(exc) == "guard_already_running" else 3

    stop = False

    def stop_handler(_signum: int, _frame: Any) -> None:
        nonlocal stop
        stop = True

    signal.signal(signal.SIGTERM, stop_handler)
    signal.signal(signal.SIGINT, stop_handler)

    exit_code = 0
    last_state: tuple[str, str | int | None] | None = None
    try:
        request_wake_lock()
        append_event(args.log, "guard_started", pid=os.getpid())
        while not stop:
            try:
                final = reconcile_once(
                    args.service_root,
                    args.sv_binary,
                    args.runsvdir_binary,
                    args.manager_log,
                    args.settle_seconds,
                    args.command_timeout,
                )
                state = ("healthy", final["manager_pid"])
                if state != last_state:
                    append_event(
                        args.log,
                        "topology_healthy",
                        manager_pid=final["manager_pid"],
                        owned=final["owned"],
                    )
                last_state = state
            except GuardError as exc:
                state = ("failed", str(exc))
                if state != last_state:
                    append_event(args.log, "recovery_failed", error=str(exc))
                last_state = state
                if args.once:
                    exit_code = 4
            if args.once:
                break
            time.sleep(max(args.poll_seconds, 1.0))
    finally:
        append_event(args.log, "guard_stopped", pid=os.getpid())
        lock_handle.close()
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
