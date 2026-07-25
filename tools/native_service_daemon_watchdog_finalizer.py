#!/usr/bin/env python3
"""Finalize an already healthy native manager by starting its watchdog only."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

if __package__:
    from tools import native_service_daemon_migration as migration
    from tools import native_service_daemon_watchdog as watchdog
else:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from tools import native_service_daemon_migration as migration
    from tools import native_service_daemon_watchdog as watchdog

MigrationError = migration.MigrationError


def finalizer_preflight(
    table: dict[int, dict[str, Any]],
    service_root: Path,
    pidfile_value: int | None,
    watchdog_count: int,
    legacy_guard_count: int,
    running_services: set[str],
) -> dict[str, Any]:
    """Accept exactly one fully owned, fully running manager with no watchdog."""
    state = watchdog.topology(table, service_root)
    if watchdog_count:
        raise MigrationError(f"preflight_new_watchdog_count:{watchdog_count}")
    if legacy_guard_count:
        raise MigrationError(f"preflight_legacy_guard_count:{legacy_guard_count}")
    if state["manager_count"] != 1 or state["manager_pid"] != pidfile_value:
        raise MigrationError(
            "preflight_native_pidfile_manager_mismatch:"
            f"pidfile={pidfile_value};manager={state['manager_pid']};"
            f"count={state['manager_count']}"
        )
    if (
        state["owned"] != len(watchdog.SERVICES)
        or state["orphaned"] != 0
        or state["invalid"] != 0
        or state["duplicates"] != 0
        or any(
            state["services"][service]["runsv_count"] != 1
            or state["services"][service]["owner"] != "manager"
            for service in watchdog.SERVICES
        )
    ):
        raise MigrationError(
            "preflight_native_fully_owned_topology:"
            f"owned={state['owned']}/{len(watchdog.SERVICES)};"
            f"orphaned={state['orphaned']};invalid={state['invalid']};"
            f"duplicates={state['duplicates']}"
        )
    missing = sorted(set(watchdog.SERVICES) - running_services)
    if missing:
        raise MigrationError("preflight_services_not_running:" + ",".join(missing))
    return state


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
        print("FINALIZER_RESULT=DRY_RUN_ONLY")
        return 2

    root = args.root.resolve()
    prefix = args.prefix.resolve()
    service_root = prefix / "var/service"
    pidfile = prefix / "var/run/service-daemon.pid"
    sv_binary = prefix / "bin/sv"
    watchdog_script = root / "tools/native_service_daemon_watchdog.py"
    watchdog_launcher = root / "tools/start_native_service_daemon_watchdog.sh"
    watchdog_lock = root / "state/native_service_daemon_watchdog.lock"
    audit = args.audit_dir.resolve()
    audit.mkdir(parents=True, exist_ok=True)

    for executable in (sv_binary, watchdog_script, watchdog_launcher):
        if not executable.is_file() or not os.access(executable, os.X_OK):
            raise MigrationError(f"required_executable_missing:{executable}")

    running_services = {
        service
        for service in watchdog.SERVICES
        if watchdog.running(sv_binary, service_root, service)
    }
    before = finalizer_preflight(
        watchdog.process_table(),
        service_root,
        migration.read_pidfile(pidfile),
        len(migration.process_matches(watchdog_script)),
        len(migration.process_matches(root / "tools/runsvdir_guard_runtime.py")),
        running_services,
    )

    try:
        migration.run_checked([str(watchdog_launcher)], 20)
        if not migration.wait_for(
            lambda: len(migration.process_matches(watchdog_script)) == 1, 15
        ):
            raise MigrationError("new_watchdog_start_timeout")
        final = migration.verify_native(
            service_root=service_root,
            pidfile=pidfile,
            sv_binary=sv_binary,
            watchdog_script=watchdog_script,
            watchdog_lock=watchdog_lock,
            require_watchdog=True,
        )
    except Exception:
        migration.stop_exact_watchdogs(watchdog_script)
        raise

    result = {
        "source_state": "native_manager_fully_owned_no_watchdog",
        "before": before,
        "final": final,
    }
    output = audit / "native_watchdog_finalizer_result.json"
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print("FINALIZER_SOURCE_STATE=native_manager_fully_owned_no_watchdog")
    print(
        "FINAL_TOPOLOGY="
        f"MANAGERS={final['manager_count']} "
        f"MANAGER_PID={final['manager_pid']} "
        f"OWNED={final['owned']}/{len(watchdog.SERVICES)} "
        f"RUNNING={len(watchdog.SERVICES) - len(final['down'])}/{len(watchdog.SERVICES)} "
        f"ORPHANED={final['orphaned']} DUPLICATES={final['duplicates']}"
    )
    print(f"WATCHDOG_PID={final['watchdog_pids'][0]}")
    print("NATIVE_WATCHDOG_FINALIZATION=PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except MigrationError as exc:
        print(f"NATIVE_WATCHDOG_FINALIZATION=FAIL:{exc}", file=sys.stderr)
        raise SystemExit(1)
