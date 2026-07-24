#!/usr/bin/env python3
"""Migrate BotA from a detached runsvdir manager to native Termux service-daemon."""
from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable

if __package__:
    from tools import native_service_daemon_watchdog as watchdog
else:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from tools import native_service_daemon_watchdog as watchdog


class MigrationError(RuntimeError):
    """Raised when the native-manager migration cannot complete safely."""


def detached_preflight(
    table: dict[int, dict[str, Any]],
    service_root: Path,
    pidfile_value: int | None,
    watchdog_count: int,
    legacy_guard_count: int,
) -> int:
    """Return the sole detached manager PID or fail closed."""
    state = watchdog.topology(table, service_root)
    if state["manager_count"] != 1:
        raise MigrationError(f"preflight_manager_count:{state['manager_count']}")
    if state["owned"] != len(watchdog.SERVICES):
        raise MigrationError(f"preflight_owned:{state['owned']}/7")
    if state["orphaned"] or state["invalid"] or state["duplicates"]:
        raise MigrationError(
            "preflight_topology:"
            f"orphaned={state['orphaned']};invalid={state['invalid']};"
            f"duplicates={state['duplicates']}"
        )
    if pidfile_value is not None:
        raise MigrationError(f"preflight_native_pidfile_present:{pidfile_value}")
    if watchdog_count:
        raise MigrationError(f"preflight_new_watchdog_count:{watchdog_count}")
    if legacy_guard_count:
        raise MigrationError(f"preflight_legacy_guard_count:{legacy_guard_count}")

    manager = int(state["manager_pid"])
    argv = table[manager].get("argv") or []
    if "-P" not in argv:
        raise MigrationError(f"preflight_manager_not_detached_p:{manager}")
    return manager


def execute_cutover(
    *,
    preflight_fn: Callable[[], int],
    terminate_fn: Callable[[int], None],
    manager_alive_fn: Callable[[int], bool],
    start_native_fn: Callable[[], None],
    reconcile_native_fn: Callable[[], dict[str, Any]],
    verify_native_fn: Callable[[bool], dict[str, Any]],
    start_watchdog_fn: Callable[[], None],
    rollback_fn: Callable[[], dict[str, Any]],
    wait_fn: Callable[[Callable[[], bool], float], bool],
    term_timeout: float,
) -> dict[str, Any]:
    """Execute one cutover, rolling back only after the old manager exits."""
    old_manager = preflight_fn()
    terminate_fn(old_manager)
    if not wait_fn(lambda: not manager_alive_fn(old_manager), term_timeout):
        raise MigrationError(f"detached_manager_term_timeout:{old_manager}")

    try:
        start_native_fn()
        reconcile = reconcile_native_fn()
        before_watchdog = verify_native_fn(False)
        start_watchdog_fn()
        final = verify_native_fn(True)
    except Exception as exc:
        try:
            rollback = rollback_fn()
        except Exception as rollback_exc:
            raise MigrationError(
                f"cutover_failed:{exc};rollback_failed:{rollback_exc}"
            ) from exc
        raise MigrationError(
            f"cutover_failed:{exc};rollback={json.dumps(rollback, sort_keys=True)}"
        ) from exc

    return {
        "old_manager_pid": old_manager,
        "new_manager_pid": final["manager_pid"],
        "reconcile": reconcile,
        "before_watchdog": before_watchdog,
        "final": final,
    }


def process_matches(script: Path) -> list[int]:
    matches: list[int] = []
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            argv = [
                item.decode(errors="replace")
                for item in (entry / "cmdline").read_bytes().split(b"\0")
                if item
            ]
        except OSError:
            continue
        if len(argv) >= 2 and Path(argv[1]) == script:
            matches.append(int(entry.name))
    return sorted(matches)


def lock_holders(lock_path: Path) -> list[int]:
    holders: list[int] = []
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            fds = list((entry / "fd").iterdir())
        except OSError:
            continue
        for fd in fds:
            try:
                target = os.readlink(fd)
            except OSError:
                continue
            if target.removesuffix(" (deleted)") == str(lock_path):
                holders.append(int(entry.name))
                break
    return sorted(holders)


def read_pidfile(path: Path) -> int | None:
    if not path.exists():
        return None
    try:
        value = int(path.read_text().strip())
    except (OSError, ValueError) as exc:
        raise MigrationError(f"pidfile_invalid:{path}") from exc
    return value


def run_checked(argv: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        argv, text=True, capture_output=True, check=False, timeout=timeout
    )
    if result.returncode:
        detail = (result.stdout or result.stderr).strip()
        raise MigrationError(
            f"command_failed:rc={result.returncode}:argv={argv}:detail={detail}"
        )
    return result


def verify_native(
    *,
    service_root: Path,
    pidfile: Path,
    sv_binary: Path,
    watchdog_script: Path,
    watchdog_lock: Path,
    require_watchdog: bool,
) -> dict[str, Any]:
    table = watchdog.process_table()
    state = watchdog.topology(table, service_root)
    manager = state.get("manager_pid")
    pidfile_value = read_pidfile(pidfile)
    down = [
        service
        for service in watchdog.SERVICES
        if not watchdog.running(sv_binary, service_root, service)
    ]
    watchdogs = process_matches(watchdog_script)
    holders = lock_holders(watchdog_lock)

    healthy = (
        state["manager_count"] == 1
        and manager == pidfile_value
        and state["owned"] == len(watchdog.SERVICES)
        and state["orphaned"] == 0
        and state["invalid"] == 0
        and state["duplicates"] == 0
        and not down
    )
    if require_watchdog:
        healthy = healthy and len(watchdogs) == 1 and holders == watchdogs
    elif watchdogs or holders:
        healthy = False

    result = {
        **state,
        "pidfile_value": pidfile_value,
        "down": down,
        "watchdog_pids": watchdogs,
        "watchdog_lock_holders": holders,
        "healthy": healthy,
    }
    if not healthy:
        raise MigrationError(
            "native_verification_failed:" + json.dumps(result, sort_keys=True)
        )
    return result


def stop_exact_watchdogs(script: Path) -> None:
    for pid in process_matches(script):
        os.kill(pid, signal.SIGTERM)


def wait_for(predicate: Callable[[], bool], timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.25)
    return predicate()


def arguments() -> argparse.Namespace:
    prefix = Path(os.environ.get("PREFIX", "/data/data/com.termux/files/usr"))
    root = Path(os.environ.get("BOTA_ROOT", str(Path.home() / "BotA")))
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--audit-dir", type=Path, required=True)
    parser.add_argument("--root", type=Path, default=root)
    parser.add_argument("--prefix", type=Path, default=prefix)
    return parser.parse_args()


def main() -> int:
    args = arguments()
    if not args.apply:
        print("MIGRATION_RESULT=DRY_RUN_ONLY")
        return 2

    root = args.root.resolve()
    prefix = args.prefix.resolve()
    service_root = prefix / "var/service"
    service_daemon = prefix / "etc/init.d/service-daemon"
    pidfile = prefix / "var/run/service-daemon.pid"
    sv_binary = prefix / "bin/sv"
    new_watchdog = root / "tools/native_service_daemon_watchdog.py"
    new_launcher = root / "tools/start_native_service_daemon_watchdog.sh"
    new_lock = root / "state/native_service_daemon_watchdog.lock"
    old_launcher = root / "tools/start_runsvdir_guard.sh"
    audit = args.audit_dir.resolve()
    audit.mkdir(parents=True, exist_ok=True)

    for executable in (
        service_daemon,
        sv_binary,
        new_watchdog,
        new_launcher,
        old_launcher,
    ):
        if not executable.is_file() or not os.access(executable, os.X_OK):
            raise MigrationError(f"required_executable_missing:{executable}")

    def preflight() -> int:
        return detached_preflight(
            watchdog.process_table(),
            service_root,
            read_pidfile(pidfile),
            len(process_matches(new_watchdog)),
            len(process_matches(root / "tools/runsvdir_guard_runtime.py")),
        )

    def terminate(pid: int) -> None:
        os.kill(pid, signal.SIGTERM)

    def manager_alive(pid: int) -> bool:
        return Path(f"/proc/{pid}").exists()

    def start_native() -> None:
        run_checked([str(service_daemon), "start"], 20)

    def reconcile_native() -> dict[str, Any]:
        return watchdog.reconcile_once(
            service_root,
            service_daemon,
            pidfile,
            sv_binary,
            settle=20,
            timeout=30,
        )

    def verify(require_watchdog: bool) -> dict[str, Any]:
        return verify_native(
            service_root=service_root,
            pidfile=pidfile,
            sv_binary=sv_binary,
            watchdog_script=new_watchdog,
            watchdog_lock=new_lock,
            require_watchdog=require_watchdog,
        )

    def start_watchdog() -> None:
        run_checked([str(new_launcher)], 20)
        if not wait_for(lambda: len(process_matches(new_watchdog)) == 1, 15):
            raise MigrationError("new_watchdog_start_timeout")

    def rollback() -> dict[str, Any]:
        stop_exact_watchdogs(new_watchdog)
        if pidfile.exists():
            run_checked([str(service_daemon), "stop"], 20)
        run_checked([str(old_launcher)], 20)

        def old_topology_healthy() -> bool:
            state = watchdog.topology(watchdog.process_table(), service_root)
            return (
                state["manager_count"] == 1
                and state["owned"] == len(watchdog.SERVICES)
                and state["orphaned"] == 0
                and state["invalid"] == 0
                and state["duplicates"] == 0
                and all(
                    watchdog.running(sv_binary, service_root, service)
                    for service in watchdog.SERVICES
                )
            )

        if not wait_for(old_topology_healthy, 60):
            raise MigrationError("old_guard_rollback_timeout")
        return watchdog.topology(watchdog.process_table(), service_root)

    result = execute_cutover(
        preflight_fn=preflight,
        terminate_fn=terminate,
        manager_alive_fn=manager_alive,
        start_native_fn=start_native,
        reconcile_native_fn=reconcile_native,
        verify_native_fn=verify,
        start_watchdog_fn=start_watchdog,
        rollback_fn=rollback,
        wait_fn=wait_for,
        term_timeout=15,
    )
    output = audit / "native_manager_migration_result.json"
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(
        "FINAL_TOPOLOGY="
        f"MANAGERS={result['final']['manager_count']} "
        f"MANAGER_PID={result['final']['manager_pid']} "
        f"OWNED={result['final']['owned']}/7 "
        f"RUNNING={7 - len(result['final']['down'])}/7 "
        f"ORPHANED={result['final']['orphaned']} "
        f"DUPLICATES={result['final']['duplicates']}"
    )
    print(f"WATCHDOG_PID={result['final']['watchdog_pids'][0]}")
    print("NATIVE_MANAGER_MIGRATION=PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except MigrationError as exc:
        print(f"NATIVE_MANAGER_MIGRATION=FAIL:{exc}", file=sys.stderr)
        raise SystemExit(1)
