#!/usr/bin/env python3
"""Keep BotA on one native Termux service-daemon control plane."""
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

SERVICES = (
    "bota-updater", "bota-watcher", "bota-closer", "bota-shadow",
    "bota-heartbeat", "bota-supervisor", "crond",
)


class WatchdogError(RuntimeError):
    pass


def process_table():
    table = {}
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            raw = (entry / "stat").read_text(errors="replace")
            fields = raw[raw.rfind(")") + 2:].split()
            argv = [x.decode(errors="replace") for x in
                    (entry / "cmdline").read_bytes().split(b"\0") if x]
            table[int(entry.name)] = {"ppid": int(fields[1]), "argv": argv}
        except (OSError, ValueError, IndexError):
            pass
    return table


def name(row):
    argv = row.get("argv") or []
    return Path(argv[0]).name if argv else ""


def managers(table, root):
    root = str(root)
    return sorted(pid for pid, row in table.items()
                  if name(row) == "runsvdir"
                  and root in " ".join((row.get("argv") or [])[1:]))


def runsv_rows(table, service):
    return [(pid, row) for pid, row in table.items()
            if name(row) == "runsv"
            and (row.get("argv") or [])[-1:] == [service]]


def topology(table, root):
    manager_set = managers(table, root)
    manager = manager_set[0] if len(manager_set) == 1 else None
    services = {}
    for service in SERVICES:
        rows = runsv_rows(table, service)
        pid = rows[0][0] if len(rows) == 1 else None
        ppid = rows[0][1]["ppid"] if len(rows) == 1 else None
        owner = "manager" if manager is not None and ppid == manager else (
            "pid1_orphan" if ppid == 1 else "other_or_missing")
        services[service] = {
            "runsv_count": len(rows), "runsv_pid": pid,
            "runsv_ppid": ppid, "owner": owner,
        }
    return {
        "manager_count": len(manager_set), "manager_pid": manager,
        "services": services,
        "owned": sum(x["owner"] == "manager" for x in services.values()),
        "orphaned": sum(x["owner"] == "pid1_orphan" for x in services.values()),
        "invalid": sum(x["owner"] == "other_or_missing" for x in services.values()),
        "duplicates": sum(x["runsv_count"] > 1 for x in services.values()),
    }


def read_pidfile(path):
    if not path.exists():
        return None
    try:
        pid = int(path.read_text().strip())
    except (OSError, ValueError) as exc:
        raise WatchdogError(f"native_pidfile_invalid:{path}") from exc
    if pid <= 0:
        raise WatchdogError(f"native_pidfile_invalid:{pid}")
    return pid


def run(argv, timeout):
    return subprocess.run(argv, text=True, capture_output=True, check=False,
                          timeout=timeout)


def wait(predicate, timeout, interval=.25):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return predicate()


def running(sv, root, service):
    try:
        result = run([str(sv), "status", str(root / service)], 5)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0 and (result.stdout or "").startswith("run:")


def sv_cmd(sv, root, service, command, timeout):
    return run([str(sv), "-w", str(timeout), command, str(root / service)],
               timeout + 5)


def require_native(root, pidfile, table_fn):
    manager_set = managers(table_fn(), root)
    if len(manager_set) != 1:
        raise WatchdogError(f"manager_count:{len(manager_set)}")
    pid = read_pidfile(pidfile)
    if pid is None:
        raise WatchdogError("native_pidfile_missing")
    if pid != manager_set[0]:
        raise WatchdogError(
            f"native_pidfile_manager_mismatch:pidfile={pid}:manager={manager_set[0]}")
    return pid


def start_native(root, daemon, pidfile, settle, timeout, table_fn, run_fn, wait_fn):
    table = table_fn()
    if managers(table, root):
        raise WatchdogError("manager_precondition_changed")
    stale = read_pidfile(pidfile)
    if stale is not None:
        if stale in table:
            raise WatchdogError(f"native_pidfile_points_live_process:{stale}")
        pidfile.unlink()
    result = run_fn([str(daemon), "start"], timeout)
    if result.returncode:
        detail = (result.stdout or result.stderr).strip()
        raise WatchdogError(
            f"native_service_daemon_start_failed:rc={result.returncode}:{detail}")

    def ready():
        return _native_ready(root, pidfile, table_fn)

    if not wait_fn(ready, settle):
        raise WatchdogError("native_service_daemon_start_timeout")
    return require_native(root, pidfile, table_fn), stale


def _native_ready(root, pidfile, table_fn):
    try:
        return require_native(root, pidfile, table_fn) > 0
    except WatchdogError:
        return False


def handoff(service, manager, root, sv, timeout, table_fn, sv_fn,
            running_fn, wait_fn):
    rows = runsv_rows(table_fn(), service)
    if len(rows) != 1 or rows[0][1]["ppid"] != 1:
        raise WatchdogError(f"orphan_precondition_changed:{service}")
    for command in ("down", "exit"):
        result = sv_fn(sv, root, service, command, timeout)
        if result.returncode:
            detail = (result.stdout or result.stderr).strip()
            raise WatchdogError(
                f"sv_{command}_failed:{service}:rc={result.returncode}:{detail}")

    def acquired():
        rows = runsv_rows(table_fn(), service)
        return len(rows) == 1 and rows[0][1]["ppid"] == manager

    if not wait_fn(acquired, timeout):
        raise WatchdogError(f"manager_acquire_timeout:{service}")

    def service_ready():
        return running_fn(sv, root, service)

    if not wait_fn(service_ready, timeout):
        raise WatchdogError(f"service_restart_timeout:{service}")


def manager_owned(service, manager, root, pidfile, table_fn):
    try:
        if require_native(root, pidfile, table_fn) != manager:
            return False
    except WatchdogError:
        return False
    row = topology(table_fn(), root)["services"][service]
    return row["runsv_count"] == 1 and row["owner"] == "manager"


def reconcile_service(service, manager, root, pidfile, sv, timeout, table_fn,
                      sv_fn, running_fn, wait_fn):
    if require_native(root, pidfile, table_fn) != manager:
        raise WatchdogError("manager_changed")
    row = topology(table_fn(), root)["services"][service]
    if row["runsv_count"] > 1:
        raise WatchdogError(f"duplicate_runsv:{service}")

    handed = False
    if row["owner"] == "pid1_orphan":
        handoff(service, manager, root, sv, timeout, table_fn, sv_fn,
                running_fn, wait_fn)
        handed = True
    elif row["owner"] != "manager":
        def ownership_ready():
            return manager_owned(service, manager, root, pidfile, table_fn)

        if not wait_fn(ownership_ready, timeout):
            raise WatchdogError(
                f"service_not_manager_owned:{service}:{row['owner']}")

    if running_fn(sv, root, service):
        return handed, False
    result = sv_fn(sv, root, service, "up", timeout)
    if result.returncode:
        detail = (result.stdout or result.stderr).strip()
        raise WatchdogError(
            f"sv_up_failed:{service}:rc={result.returncode}:{detail}")

    def service_ready():
        return running_fn(sv, root, service)

    if not wait_fn(service_ready, timeout):
        raise WatchdogError(f"service_up_timeout:{service}")
    return handed, True


def reconcile_services(manager, root, pidfile, sv, timeout, table_fn, sv_fn,
                       running_fn, wait_fn):
    restarted, handed = [], []
    for service in SERVICES:
        was_handed, was_restarted = reconcile_service(
            service, manager, root, pidfile, sv, timeout, table_fn, sv_fn,
            running_fn, wait_fn)
        if was_handed:
            handed.append(service)
        if was_restarted:
            restarted.append(service)

    final = topology(table_fn(), root)
    down = [s for s in SERVICES if not running_fn(sv, root, s)]
    if (require_native(root, pidfile, table_fn) != manager
            or final["owned"] != 7 or final["orphaned"]
            or final["invalid"] or final["duplicates"] or down):
        raise WatchdogError(
            "topology_not_healthy:"
            f"owned={final['owned']}/7;orphaned={final['orphaned']};"
            f"invalid={final['invalid']};duplicates={final['duplicates']};"
            f"down={','.join(down)}")
    final.update(running=7, restarted_services=restarted,
                 handed_off_services=handed)
    return final


def reconcile_once(root, daemon, pidfile, sv, settle, timeout,
                   table_fn=process_table, command_fn=run, run_sv_fn=sv_cmd,
                   service_running_fn=running, wait_fn=wait):
    initial = topology(table_fn(), root)
    if initial["manager_count"] > 1:
        raise WatchdogError(f"multiple_managers:{initial['manager_count']}")
    if initial["duplicates"]:
        raise WatchdogError(f"duplicate_runsv_rows:{initial['duplicates']}")
    started, stale = False, None
    if initial["manager_count"] == 0:
        manager, stale = start_native(root, daemon, pidfile, settle, timeout,
                                      table_fn, command_fn, wait_fn)
        started = True
    else:
        manager = require_native(root, pidfile, table_fn)
    final = reconcile_services(manager, root, pidfile, sv, timeout, table_fn,
                               run_sv_fn, service_running_fn, wait_fn)
    final.update(native_manager_started=started, stale_pidfile_removed=stale)
    return final


def event(log, kind, **details):
    log.parent.mkdir(parents=True, exist_ok=True)
    try:
        boot = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
    except OSError:
        boot = "unknown"
    clock = getattr(time, "CLOCK_BOOTTIME", time.CLOCK_MONOTONIC)
    payload = {"event": kind, "boot_id": boot,
               "monotonic_ns": time.clock_gettime_ns(clock), **details}
    with log.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")


def lock(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.open("a+")
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        handle.close()
        raise WatchdogError("watchdog_already_running") from None
    return handle


def arguments():
    prefix = Path(os.environ.get("PREFIX", "/data/data/com.termux/files/usr"))
    root = Path(os.environ.get("BOTA_ROOT", str(Path.home() / "BotA")))
    parser = argparse.ArgumentParser()
    parser.add_argument("--service-root", type=Path, default=prefix / "var/service")
    parser.add_argument("--service-daemon", type=Path,
                        default=prefix / "etc/init.d/service-daemon")
    parser.add_argument("--pidfile", type=Path,
                        default=prefix / "var/run/service-daemon.pid")
    parser.add_argument("--sv", type=Path, default=prefix / "bin/sv")
    parser.add_argument("--lock", type=Path,
                        default=root / "state/native_service_daemon_watchdog.lock")
    parser.add_argument("--log", type=Path,
                        default=root / "logs/native_service_daemon_watchdog.jsonl")
    parser.add_argument("--poll", type=float, default=5)
    parser.add_argument("--settle", type=float, default=15)
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--once", action="store_true")
    return parser.parse_args()


def main():
    args = arguments()
    for binary in (args.service_daemon, args.sv):
        if not binary.is_file() or not os.access(binary, os.X_OK):
            print(f"WATCHDOG_BINARY_INVALID={binary}", file=sys.stderr)
            return 2
    try:
        handle = lock(args.lock)
    except WatchdogError as exc:
        print(f"NATIVE_WATCHDOG={exc}", file=sys.stderr)
        return 0 if str(exc) == "watchdog_already_running" else 3

    stop = False

    def stop_handler(_sig, _frame):
        nonlocal stop
        stop = True

    signal.signal(signal.SIGTERM, stop_handler)
    signal.signal(signal.SIGINT, stop_handler)

    last, code = None, 0
    try:
        event(args.log, "watchdog_started", pid=os.getpid())
        while not stop:
            try:
                final = reconcile_once(args.service_root, args.service_daemon,
                                       args.pidfile, args.sv, args.settle,
                                       args.timeout)
                state = ("healthy", final["manager_pid"])
                if state != last:
                    event(args.log, "topology_healthy",
                          manager_pid=final["manager_pid"], owned=7, running=7,
                          native_manager_started=final["native_manager_started"],
                          stale_pidfile_removed=final["stale_pidfile_removed"])
                last = state
            except WatchdogError as exc:
                state = ("failed", str(exc))
                if state != last:
                    event(args.log, "recovery_failed", error=str(exc))
                last = state
                if args.once:
                    code = 4
            if args.once:
                break
            time.sleep(max(args.poll, 1))
    finally:
        event(args.log, "watchdog_stopped", pid=os.getpid())
        handle.close()
    return code


if __name__ == "__main__":
    raise SystemExit(main())
