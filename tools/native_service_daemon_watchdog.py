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


def crond_rows(table):
    """Return exact foreground crond rows used by the runit service."""
    return [(pid, row) for pid, row in table.items()
            if name(row) == "crond"
            and "-n" in (row.get("argv") or [])
            and "-s" in (row.get("argv") or [])]


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


def read_runtime_pidfile(path, label):
    """Read one runtime pidfile without ever deleting it implicitly."""
    if not path.exists():
        return None
    try:
        pid = int(path.read_text().strip())
    except (OSError, ValueError) as exc:
        raise WatchdogError(f"{label}_pidfile_invalid:{path}") from exc
    if pid <= 0:
        raise WatchdogError(f"{label}_pidfile_invalid:{pid}")
    return pid


def supervised_pid(root, service):
    """Return the child PID recorded by runsv supervise state."""
    path = root / service / "supervise" / "pid"
    try:
        value = path.read_text().strip()
        pid = int(value) if value else 0
    except (OSError, ValueError):
        return None
    return pid if pid > 0 else None


def terminate_pid(pid):
    """Terminate only the exact PID already proven safe by a caller."""
    os.kill(pid, signal.SIGTERM)


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


def crond_ownership(root, manager, crond_pidfile, table_fn, child_pid_fn):
    """Return fail-closed ownership evidence for the singleton crond child."""
    table = table_fn()
    row = topology(table, root)["services"]["crond"]
    live = crond_rows(table)
    child = child_pid_fn(root, "crond")
    pidfile_pid = read_runtime_pidfile(crond_pidfile, "crond")
    failures = []

    if row["runsv_count"] != 1 or row["owner"] != "manager":
        failures.append(f"runsv_owner:{row['owner']}:count={row['runsv_count']}")
    if len(live) != 1:
        failures.append(f"live_count:{len(live)}")
    if child is None:
        failures.append("supervised_child_missing")
    if pidfile_pid is None:
        failures.append("pidfile_missing")

    if len(live) == 1:
        live_pid, live_row = live[0]
        if child is not None and child != live_pid:
            failures.append(f"supervised_child_mismatch:{child}:{live_pid}")
        if row["runsv_pid"] is not None and live_row["ppid"] != row["runsv_pid"]:
            failures.append(f"parent_mismatch:{live_row['ppid']}:{row['runsv_pid']}")
        if pidfile_pid is not None and pidfile_pid != live_pid:
            failures.append(f"pidfile_mismatch:{pidfile_pid}:{live_pid}")

    return {
        "healthy": not failures,
        "runsv_pid": row["runsv_pid"],
        "runsv_owner": row["owner"],
        "supervised_child_pid": child,
        "pidfile_pid": pidfile_pid,
        "live_crond": [
            {"pid": pid, "ppid": item["ppid"], "argv": item.get("argv") or []}
            for pid, item in live
        ],
        "failure_reasons": failures,
        "manager_pid": manager,
    }


def _stale_crond_candidate(root, manager, crond_pidfile, table_fn, child_pid_fn):
    """Return the exact stale PID-1 crond candidate or fail closed on ambiguity."""
    table = table_fn()
    row = topology(table, root)["services"]["crond"]
    live = crond_rows(table)
    child = child_pid_fn(root, "crond")
    pidfile_pid = read_runtime_pidfile(crond_pidfile, "crond")

    if row["runsv_count"] != 1 or row["owner"] != "manager":
        raise WatchdogError(
            f"crond_repair_runsv_not_manager_owned:{row['owner']}:count={row['runsv_count']}"
        )
    if len(live) != 1:
        raise WatchdogError(f"crond_live_process_ambiguous:count={len(live)}")

    stale_pid, stale_row = live[0]
    if stale_row["ppid"] != 1:
        raise WatchdogError(
            f"crond_live_process_ambiguous:pid={stale_pid}:ppid={stale_row['ppid']}"
        )
    if child == stale_pid:
        raise WatchdogError(f"crond_repair_refuses_supervised_child:{stale_pid}")
    if child is not None:
        raise WatchdogError(
            f"crond_live_process_ambiguous:supervised_child={child}:stale={stale_pid}"
        )
    if pidfile_pid != stale_pid:
        raise WatchdogError(
            f"crond_pidfile_not_stale_candidate:pidfile={pidfile_pid}:candidate={stale_pid}"
        )
    if manager is None:
        raise WatchdogError("crond_repair_manager_missing")
    return stale_pid, row["runsv_pid"], list(stale_row.get("argv") or [])


def reconcile_stale_crond(manager, root, native_pidfile, crond_pidfile, sv,
                          timeout, table_fn, sv_fn, running_fn, wait_fn,
                          child_pid_fn, terminate_fn):
    """Repair only the production-proven stale PID-1 crond singleton state."""
    if require_native(root, native_pidfile, table_fn) != manager:
        raise WatchdogError("manager_changed_before_crond_repair")
    stale_pid, runsv_pid, stale_argv = _stale_crond_candidate(
        root, manager, crond_pidfile, table_fn, child_pid_fn
    )

    down = sv_fn(sv, root, "crond", "down", timeout)
    if down.returncode:
        detail = (down.stdout or down.stderr).strip()
        raise WatchdogError(f"sv_down_failed:crond:rc={down.returncode}:{detail}")

    if require_native(root, native_pidfile, table_fn) != manager:
        raise WatchdogError("manager_changed_during_crond_repair")
    confirm_pid, confirm_runsv, confirm_argv = _stale_crond_candidate(
        root, manager, crond_pidfile, table_fn, child_pid_fn
    )
    if (confirm_pid, confirm_runsv, confirm_argv) != (stale_pid, runsv_pid, stale_argv):
        raise WatchdogError("crond_stale_identity_changed_after_quiesce")

    try:
        terminate_fn(stale_pid)
    except OSError as exc:
        raise WatchdogError(
            f"crond_stale_sigterm_failed:{stale_pid}:{type(exc).__name__}"
        ) from exc

    def stale_gone():
        return stale_pid not in table_fn()

    if not wait_fn(stale_gone, timeout):
        raise WatchdogError(f"crond_stale_term_timeout:{stale_pid}")

    remaining_pidfile = read_runtime_pidfile(crond_pidfile, "crond")
    if remaining_pidfile is not None:
        raise WatchdogError(f"crond_pidfile_not_cleared_after_term:{remaining_pidfile}")

    up = sv_fn(sv, root, "crond", "up", timeout)
    if up.returncode:
        detail = (up.stdout or up.stderr).strip()
        raise WatchdogError(f"sv_up_failed:crond:rc={up.returncode}:{detail}")

    def crond_ready():
        if not running_fn(sv, root, "crond"):
            return False
        try:
            evidence = crond_ownership(
                root, manager, crond_pidfile, table_fn, child_pid_fn
            )
        except WatchdogError:
            return False
        return evidence["healthy"]

    if not wait_fn(crond_ready, timeout):
        raise WatchdogError("crond_replacement_ownership_timeout")
    evidence = crond_ownership(root, manager, crond_pidfile, table_fn, child_pid_fn)
    return {
        "stale_pid": stale_pid,
        "runsv_pid": runsv_pid,
        "replacement_pid": evidence["live_crond"][0]["pid"],
        "replacement_parent": evidence["live_crond"][0]["ppid"],
        "pidfile_pid": evidence["pidfile_pid"],
    }


def reconcile_service(service, manager, root, pidfile, crond_pidfile, sv,
                      timeout, table_fn, sv_fn, running_fn, wait_fn,
                      child_pid_fn, terminate_fn):
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
            raise WatchdogError(f"service_not_manager_owned:{service}:{row['owner']}")

    if running_fn(sv, root, service):
        if service == "crond":
            evidence = crond_ownership(
                root, manager, crond_pidfile, table_fn, child_pid_fn
            )
            if not evidence["healthy"]:
                raise WatchdogError(
                    "crond_ownership_invalid:" + ",".join(evidence["failure_reasons"])
                )
        return handed, False, None

    if service == "crond" and crond_rows(table_fn()):
        repair = reconcile_stale_crond(
            manager, root, pidfile, crond_pidfile, sv, timeout, table_fn,
            sv_fn, running_fn, wait_fn, child_pid_fn, terminate_fn
        )
        return handed, True, repair

    result = sv_fn(sv, root, service, "up", timeout)
    if result.returncode:
        detail = (result.stdout or result.stderr).strip()
        raise WatchdogError(
            f"sv_up_failed:{service}:rc={result.returncode}:{detail}")

    def service_ready():
        return running_fn(sv, root, service)

    if not wait_fn(service_ready, timeout):
        raise WatchdogError(f"service_up_timeout:{service}")

    if service == "crond":
        def ownership_ready():
            try:
                return crond_ownership(
                    root, manager, crond_pidfile, table_fn, child_pid_fn
                )["healthy"]
            except WatchdogError:
                return False

        if not wait_fn(ownership_ready, timeout):
            raise WatchdogError("crond_ownership_timeout_after_start")
    return handed, True, None


def reconcile_services(manager, root, pidfile, crond_pidfile, sv, timeout,
                       table_fn, sv_fn, running_fn, wait_fn, child_pid_fn,
                       terminate_fn):
    restarted, handed = [], []
    singleton_repairs = {}
    for service in SERVICES:
        was_handed, was_restarted, singleton_repair = reconcile_service(
            service, manager, root, pidfile, crond_pidfile, sv, timeout,
            table_fn, sv_fn, running_fn, wait_fn, child_pid_fn, terminate_fn)
        if was_handed:
            handed.append(service)
        if was_restarted:
            restarted.append(service)
        if singleton_repair is not None:
            singleton_repairs[service] = singleton_repair

    final = topology(table_fn(), root)
    down = [s for s in SERVICES if not running_fn(sv, root, s)]
    crond_evidence = crond_ownership(
        root, manager, crond_pidfile, table_fn, child_pid_fn
    )
    if (require_native(root, pidfile, table_fn) != manager
            or final["owned"] != 7 or final["orphaned"]
            or final["invalid"] or final["duplicates"] or down
            or not crond_evidence["healthy"]):
        raise WatchdogError(
            "topology_not_healthy:"
            f"owned={final['owned']}/7;orphaned={final['orphaned']};"
            f"invalid={final['invalid']};duplicates={final['duplicates']};"
            f"down={','.join(down)};"
            f"crond={','.join(crond_evidence['failure_reasons'])}")
    final.update(running=7, restarted_services=restarted,
                 handed_off_services=handed,
                 singleton_repairs=singleton_repairs,
                 crond_ownership=crond_evidence)
    return final


def reconcile_once(root, daemon, pidfile, sv, settle, timeout,
                   table_fn=process_table, command_fn=run, run_sv_fn=sv_cmd,
                   service_running_fn=running, wait_fn=wait,
                   crond_pidfile=None, child_pid_fn=supervised_pid,
                   terminate_fn=terminate_pid):
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

    if crond_pidfile is None:
        crond_pidfile = pidfile.parent / "crond.pid"
    final = reconcile_services(
        manager, root, pidfile, crond_pidfile, sv, timeout, table_fn,
        run_sv_fn, service_running_fn, wait_fn, child_pid_fn, terminate_fn)
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
    parser.add_argument("--crond-pidfile", type=Path,
                        default=prefix / "var/run/crond.pid")
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
                final = reconcile_once(
                    args.service_root, args.service_daemon, args.pidfile,
                    args.sv, args.settle, args.timeout,
                    crond_pidfile=args.crond_pidfile)
                state = (
                    "healthy", final["manager_pid"],
                    json.dumps(final.get("singleton_repairs", {}), sort_keys=True),
                )
                if state != last:
                    event(
                        args.log, "topology_healthy",
                        manager_pid=final["manager_pid"], owned=7, running=7,
                        native_manager_started=final["native_manager_started"],
                        stale_pidfile_removed=final["stale_pidfile_removed"],
                        singleton_repairs=final.get("singleton_repairs", {}),
                    )
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
