#!/usr/bin/env python3
"""Ensure the native control-plane watchdog remains alive.

This guard is deliberately narrower than the watchdog itself. It never signals
BotA services and never performs topology reconciliation. In --ensure mode it
may invoke the reviewed watchdog launcher only when there are exactly zero
watchdog processes and zero lock holders. Ambiguous states fail closed.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import math
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


def _fdinfo_flock_row_matches(
    line: str,
    *,
    pid: int,
    fd_num: int,
    target_dev: tuple[int, int],
    target_inode: int,
) -> bool:
    """Validate one fdinfo row and report an exact active FLOCK match."""
    if not line.startswith("lock:"):
        return False
    parts = line.split()
    # "lock: N: FLOCK ADVISORY WRITE <pid> maj:min:ino start end"
    if len(parts) < 8:
        raise GuardError(f"flock_fdinfo_malformed:{pid}:{fd_num}:{line!r}")
    if parts[2] != "FLOCK":
        return False
    try:
        lock_pid = int(parts[5])
    except ValueError as exc:
        raise GuardError(f"flock_fdinfo_malformed:{pid}:{fd_num}:{line!r}") from exc
    if lock_pid != pid:
        raise GuardError(f"flock_pid_mismatch:{pid}:reported={lock_pid}")
    segments = parts[6].split(":")
    if len(segments) != 3:
        raise GuardError(f"flock_fdinfo_malformed:{pid}:{fd_num}:{line!r}")
    try:
        major = int(segments[0], 16)
        minor = int(segments[1], 16)
        inode = int(segments[2])
    except ValueError as exc:
        raise GuardError(f"flock_fdinfo_malformed:{pid}:{fd_num}:{line!r}") from exc
    if (major, minor, inode) != (target_dev[0], target_dev[1], target_inode):
        raise GuardError(f"flock_dev_inode_mismatch:{pid}:{fd_num}:{parts[6]}")
    return True


def _matching_fdinfo_text(
    entry: Path,
    *,
    pid: int,
    target_dev: tuple[int, int],
    target_inode: int,
) -> tuple[int, str] | None:
    """Return ``(fd, fdinfo)`` when ``entry`` is the target lock descriptor."""
    try:
        fd_num = int(entry.name)
    except ValueError:
        return None
    try:
        fd_st = os.stat(entry)
    except FileNotFoundError:
        # fd closed mid-scan; keep scanning other fds.
        return None
    except OSError as exc:
        raise GuardError(f"flock_fd_stat_denied:{pid}:{fd_num}:{exc}") from exc
    if fd_st.st_ino != target_inode:
        return None
    if (os.major(fd_st.st_dev), os.minor(fd_st.st_dev)) != target_dev:
        return None

    info_path = Path(f"/proc/{pid}/fdinfo/{fd_num}")
    try:
        return fd_num, info_path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        # fd closed between listing and fdinfo read; keep scanning.
        return None
    except OSError as exc:
        raise GuardError(f"flock_fdinfo_denied:{pid}:{fd_num}:{exc}") from exc


def _fdinfo_flock_holder(lock_path: Path, pid: int) -> list[int]:
    """Confirm ``pid`` actively holds a FLOCK on ``lock_path`` via fdinfo.

    Walks ``/proc/<pid>/fd/*``, matches by device+inode against
    ``os.stat(lock_path)``, and then requires an active ``lock:`` row in
    ``/proc/<pid>/fdinfo/<fd>`` whose type is FLOCK and whose recorded pid
    and dev:inode agree with the watchdog process and lock file.

    Returns ``[pid]`` on confirmation. Raises :class:`GuardError` for every
    other outcome — missing lock file, unreadable/denied fd or fdinfo,
    malformed row, pid/dev/inode mismatch, or race disappearance. An open fd
    without an active FLOCK row does not confirm ownership.
    """
    try:
        st = os.stat(lock_path)
    except FileNotFoundError as exc:
        raise GuardError(f"flock_lock_missing:{lock_path}") from exc
    except OSError as exc:
        raise GuardError(f"flock_stat_failed:{lock_path}:{exc}") from exc
    target_dev = (os.major(st.st_dev), os.minor(st.st_dev))
    target_inode = st.st_ino

    fd_dir = Path(f"/proc/{pid}/fd")
    try:
        entries = list(fd_dir.iterdir())
    except FileNotFoundError as exc:
        raise GuardError(f"flock_pid_disappeared:{pid}") from exc
    except OSError as exc:
        raise GuardError(f"flock_fd_scan_denied:{pid}:{exc}") from exc

    for entry in entries:
        matched = _matching_fdinfo_text(
            entry,
            pid=pid,
            target_dev=target_dev,
            target_inode=target_inode,
        )
        if matched is None:
            continue
        fd_num, info_text = matched
        for line in info_text.splitlines():
            if _fdinfo_flock_row_matches(
                line,
                pid=pid,
                fd_num=fd_num,
                target_dev=target_dev,
                target_inode=target_inode,
            ):
                return [pid]
        # Matching fd but no active FLOCK row — not this fd. Keep scanning.
    raise GuardError(f"flock_owner_not_confirmed:pid={pid}:lock={lock_path}")


def _probe_lock_free(lock_path: Path) -> None:
    """Absence probe used only when no watchdog PID exists.

    Missing lock file counts as absent. Otherwise opens the existing lock
    (no create, no truncate) and attempts ``LOCK_EX | LOCK_NB``:

    * acquired → immediately released and returned (absent);
    * ``BlockingIOError`` → contended, fail-closed via :class:`GuardError`;
    * any other ``OSError`` → fail-closed via :class:`GuardError`.

    The probe never leaves the lock held: ``LOCK_UN`` is attempted, and the
    file descriptor is closed unconditionally in ``finally``, which itself
    releases any flock held on it.
    """
    try:
        fd = os.open(lock_path, os.O_RDWR)
    except FileNotFoundError:
        return
    except OSError as exc:
        raise GuardError(f"flock_probe_open_failed:{lock_path}:{exc}") from exc
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise GuardError(f"flock_probe_contended:{lock_path}") from exc
        except OSError as exc:
            raise GuardError(f"flock_probe_failed:{lock_path}:{exc}") from exc
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        except OSError:
            # Best-effort release; the close below drops the lock regardless.
            pass
    finally:
        os.close(fd)


def _finite_float(text: str) -> float:
    """Parse ``text`` as a finite float; reject NaN and +/- infinity.

    Preserves the previously accepted domain of every finite float, including
    zero and negative values. Only non-finite floats are rejected, via
    argparse's standard error path.
    """
    try:
        value = float(text)
    except (TypeError, ValueError) as exc:
        raise argparse.ArgumentTypeError(f"invalid float value: {text!r}") from exc
    if math.isnan(value) or math.isinf(value):
        raise argparse.ArgumentTypeError(
            f"timeout must be a finite float, not {text!r}"
        )
    return value


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


def _emit_failure(log: Path, exc: BaseException) -> int:
    """Emit fail-closed guardian output, tolerating logging failures.

    ``append_event`` may itself raise ``OSError`` (disk full, permissions,
    etc.). Callers still need a controlled ``WATCHDOG_GUARD=FAIL`` line on
    stderr and RC 4.
    """
    try:
        append_event(log, "guard_failed", error=str(exc))
    except OSError:
        pass
    print(f"WATCHDOG_GUARD=FAIL:{exc}", file=sys.stderr)
    return 4


def arguments(argv: list[str] | None = None) -> argparse.Namespace:
    root = Path(os.environ.get("BOTA_ROOT", str(Path.home() / "BotA")))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ensure", action="store_true")
    parser.add_argument("--timeout", type=_finite_float, default=15.0)
    parser.add_argument("--root", type=Path, default=root)
    return parser.parse_args(argv)


def _snapshot_watchdog(
    watchdog: Path, lock: Path
) -> tuple[list[int], list[int], str]:
    pids = migration.process_matches(watchdog)
    unique_pids = sorted(set(pids))
    if len(unique_pids) > 1:
        # state_for raises the ambiguous-process error; holders unused.
        return pids, [], state_for(pids, [])
    if unique_pids:
        holders = _fdinfo_flock_holder(lock, unique_pids[0])
    else:
        _probe_lock_free(lock)
        holders = []
    return pids, holders, state_for(pids, holders)


def _relaunch_timeout_error(watchdog: Path, lock: Path) -> GuardError:
    final_pids = migration.process_matches(watchdog)
    final_unique = sorted(set(final_pids))
    final_holders: list[int] | str
    if len(final_unique) == 1:
        try:
            final_holders = _fdinfo_flock_holder(lock, final_unique[0])
        except GuardError as exc:
            final_holders = f"unknown:{exc}"
    else:
        final_holders = f"unknown:pid_count={len(final_unique)}"
    return GuardError(
        "watchdog_relaunch_timeout:"
        f"pids={final_pids}:holders={final_holders}"
    )


def _recover_watchdog(
    *,
    launcher: Path,
    watchdog: Path,
    lock: Path,
    log: Path,
    timeout: float,
) -> int:
    append_event(log, "guard_relaunch_requested")
    result = subprocess.run(
        [str(launcher)],
        text=True,
        capture_output=True,
        check=False,
        timeout=max(timeout, 1.0),
    )
    if result.returncode:
        detail = (result.stderr or result.stdout).strip()[:240]
        raise GuardError(f"launcher_failed:rc={result.returncode}:detail={detail}")

    def ready() -> bool:
        try:
            current_pids, current_holders, current_state = _snapshot_watchdog(
                watchdog, lock
            )
        except GuardError:
            return False
        return (
            current_state == "healthy"
            and len(current_pids) == 1
            and current_holders == current_pids
        )

    if not wait_until(ready, timeout):
        raise _relaunch_timeout_error(watchdog, lock)

    final_pids, _, _ = _snapshot_watchdog(watchdog, lock)
    append_event(log, "guard_relaunch_success", watchdog_pid=final_pids[0])
    print(f"WATCHDOG_GUARD=RECOVERED:pid={final_pids[0]}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = arguments(argv)
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

    try:
        pids, _, state = _snapshot_watchdog(watchdog, lock)
        if state == "healthy":
            append_event(log, "guard_healthy", watchdog_pid=pids[0])
            print(f"WATCHDOG_GUARD=HEALTHY:pid={pids[0]}")
            return 0
        if not args.ensure:
            append_event(log, "guard_absent_check_only")
            print("WATCHDOG_GUARD=ABSENT")
            return 3
        return _recover_watchdog(
            launcher=launcher,
            watchdog=watchdog,
            lock=lock,
            log=log,
            timeout=args.timeout,
        )
    except (GuardError, OSError, subprocess.TimeoutExpired) as exc:
        return _emit_failure(log, exc)


if __name__ == "__main__":
    raise SystemExit(main())