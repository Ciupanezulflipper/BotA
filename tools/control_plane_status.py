#!/usr/bin/env python3
"""Read-only BotA runit control-plane topology inspection."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

SERVICES = (
    "bota-updater",
    "bota-watcher",
    "bota-closer",
    "bota-shadow",
    "bota-heartbeat",
    "bota-supervisor",
    "crond",
)


def process_table() -> dict[int, dict[str, Any]]:
    """Return readable process parentage, state, comm and argv from procfs."""
    table: dict[int, dict[str, Any]] = {}
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            raw = (entry / "stat").read_text(errors="replace")
            open_paren = raw.find("(")
            close_paren = raw.rfind(")")
            if open_paren < 0 or close_paren <= open_paren:
                continue
            comm = raw[open_paren + 1 : close_paren]
            fields = raw[close_paren + 2 :].split()
            state = fields[0]
            ppid = int(fields[1])
            argv = [
                item.decode(errors="replace")
                for item in (entry / "cmdline").read_bytes().split(b"\0")
                if item
            ]
            table[int(entry.name)] = {
                "ppid": ppid,
                "state": state,
                "comm": comm,
                "argv": argv,
            }
        except (OSError, ValueError, IndexError):
            continue
    return table


def basename(row: dict[str, Any]) -> str:
    """Return process executable basename, falling back to /proc stat comm."""
    argv = row.get("argv") or []
    if argv:
        return Path(argv[0]).name
    return Path(str(row.get("comm") or "")).name


def is_zombie(row: dict[str, Any] | None) -> bool:
    return bool(row and row.get("state") == "Z")


def service_status(
    sv_binary: Path,
    service_root: Path,
    service: str,
) -> tuple[bool, str]:
    """Read sv status without attempting any mutation."""
    if not sv_binary.is_file():
        return False, f"sv_binary_missing:{sv_binary}"
    try:
        result = subprocess.run(
            [str(sv_binary), "status", str(service_root / service)],
            text=True,
            capture_output=True,
            check=False,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, f"status_error:{type(exc).__name__}"
    output = (result.stdout or result.stderr).strip()
    return result.returncode == 0 and output.startswith("run:"), output


def standard_managers(
    table: dict[int, dict[str, Any]],
    service_root: Path,
) -> list[int]:
    """Return non-zombie runsvdir processes managing the Termux service root."""
    root_text = str(service_root)
    return [
        pid
        for pid, row in table.items()
        if basename(row) == "runsvdir"
        and not is_zombie(row)
        and root_text in " ".join(row.get("argv", [])[1:])
    ]


def runsv_candidates(
    table: dict[int, dict[str, Any]],
    service: str,
) -> list[tuple[int, dict[str, Any]]]:
    """Return non-zombie exact runsv processes for one service name."""
    return [
        (pid, row)
        for pid, row in table.items()
        if basename(row) == "runsv"
        and not is_zombie(row)
        and (row.get("argv") or [])[-1:] == [service]
    ]


def zombie_runsv_children(
    table: dict[int, dict[str, Any]],
    manager_pids: set[int],
) -> list[dict[str, Any]]:
    """Return defunct runsv children of the standard Termux runsvdir manager(s).

    Zombie cmdlines are empty, so the exact service name cannot be recovered
    reliably from /proc/<pid>/cmdline. Restricting by parent manager catches the
    observed production defect without treating unrelated PID-1 runsv zombies as
    BotA control-plane failures.
    """
    return [
        {
            "pid": pid,
            "ppid": int(row.get("ppid", 0)),
            "state": row.get("state"),
            "comm": row.get("comm"),
        }
        for pid, row in table.items()
        if basename(row) == "runsv"
        and is_zombie(row)
        and int(row.get("ppid", 0)) in manager_pids
    ]


def wrapper_pid(service_root: Path, service: str) -> int | None:
    """Read the current supervised child PID when available."""
    try:
        value = (service_root / service / "supervise" / "pid").read_text().strip()
        return int(value) if value else None
    except (OSError, ValueError):
        return None


def runtime_pidfile(path: Path) -> tuple[int | None, str | None]:
    """Return a positive runtime PID and a compact parse error when invalid."""
    try:
        value = path.read_text().strip()
    except FileNotFoundError:
        return None, "missing"
    except OSError as exc:
        return None, f"read_error:{type(exc).__name__}"
    try:
        pid = int(value)
    except ValueError:
        return None, "invalid"
    return (pid, None) if pid > 0 else (None, "invalid")


def inspect_service(
    table: dict[int, dict[str, Any]],
    sv_binary: Path,
    service_root: Path,
    manager: int | None,
    service: str,
) -> dict[str, Any]:
    """Return exact ownership, status, and wrapper evidence for one service."""
    candidates = runsv_candidates(table, service)
    runsv_pid = candidates[0][0] if len(candidates) == 1 else None
    runsv_ppid = candidates[0][1]["ppid"] if len(candidates) == 1 else None
    if manager is not None and runsv_ppid == manager:
        owner = "manager"
    elif runsv_ppid == 1:
        owner = "pid1_orphan"
    else:
        owner = "other_or_missing"

    is_running, status_text = service_status(
        sv_binary,
        service_root,
        service,
    )
    child_pid = wrapper_pid(service_root, service)
    child_row = table.get(child_pid) if child_pid else None
    child_alive = bool(child_pid and child_row and not is_zombie(child_row))
    return {
        "runsv_count": len(candidates),
        "runsv_pid": runsv_pid,
        "runsv_ppid": runsv_ppid,
        "owner": owner,
        "service_running": is_running,
        "sv_status": status_text,
        "wrapper_pid": child_pid,
        "wrapper_alive": child_alive,
        "wrapper_state": child_row.get("state") if child_row else None,
    }


def crond_processes(table: dict[int, dict[str, Any]]) -> list[dict[str, Any]]:
    """Return live non-zombie foreground crond processes and parentage."""
    return [
        {
            "pid": pid,
            "ppid": row["ppid"],
            "argv": row.get("argv") or [],
        }
        for pid, row in table.items()
        if basename(row) == "crond"
        and not is_zombie(row)
        and "-n" in (row.get("argv") or [])
        and "-s" in (row.get("argv") or [])
    ]


def topology_failures(
    manager_count: int,
    owned: int,
    running: int,
    orphaned: int,
    duplicates: int,
    *evidence: Any,
    zombie_runsv: list[dict[str, Any]] | None = None,
) -> list[str]:
    """Build compact acceptance failures from an inspected topology.

    Backward compatibility is deliberate:
    - historical callers pass: rows, live_crond, pidfile_pid, pidfile_error
    - the first zombie regression passed: zombies, rows, live_crond, pidfile_pid, pidfile_error
    Production uses the historical shape plus keyword ``zombie_runsv=...``.
    Any other positional shape fails explicitly instead of shifting silently.
    """
    if len(evidence) == 4:
        rows, live_crond, crond_pidfile_pid, crond_pidfile_error = evidence
        zombies = zombie_runsv or []
    elif len(evidence) == 5 and zombie_runsv is None:
        zombies, rows, live_crond, crond_pidfile_pid, crond_pidfile_error = evidence
    else:
        raise TypeError("unexpected topology_failures evidence shape")
    if not isinstance(rows, dict) or not isinstance(live_crond, list) or not isinstance(zombies, list):
        raise TypeError("invalid topology_failures evidence types")

    failures: list[str] = []
    checks = (
        (manager_count != 1, f"manager_count:{manager_count}"),
        (owned != len(SERVICES), f"owned:{owned}/{len(SERVICES)}"),
        (running != len(SERVICES), f"running:{running}/{len(SERVICES)}"),
        (orphaned != 0, f"orphaned:{orphaned}"),
        (duplicates != 0, f"duplicate_service_rows:{duplicates}"),
        (len(zombies) != 0, f"zombie_runsv_count:{len(zombies)}"),
        (len(live_crond) != 1, f"live_crond_count:{len(live_crond)}"),
    )
    failures.extend(reason for failed, reason in checks if failed)
    dead_wrappers = [
        name for name, row in rows.items()
        if row.get("service_running") and not row.get("wrapper_alive")
    ]
    if dead_wrappers:
        failures.append("wrapper_not_alive:" + ",".join(sorted(dead_wrappers)))
    if crond_pidfile_error is not None:
        failures.append(f"crond_pidfile:{crond_pidfile_error}")

    if len(live_crond) == 1:
        crond = live_crond[0]
        crond_service = rows.get("crond", {})
        if crond_service.get("wrapper_pid") != crond["pid"]:
            failures.append("crond_not_owned_by_current_runsv")
        if crond_service.get("runsv_pid") != crond["ppid"]:
            failures.append("crond_parent_not_current_runsv")
        if crond_pidfile_pid is not None and crond_pidfile_pid != crond["pid"]:
            failures.append("crond_pidfile_not_live_crond")
    return failures


def snapshot() -> dict[str, Any]:
    """Build the exact seven-service ownership snapshot."""
    prefix = Path(os.environ.get("PREFIX", "/data/data/com.termux/files/usr"))
    service_root = prefix / "var" / "service"
    sv_binary = prefix / "bin" / "sv"
    table = process_table()
    managers = standard_managers(table, service_root)
    manager = managers[0] if len(managers) == 1 else None
    rows = {
        service: inspect_service(
            table,
            sv_binary,
            service_root,
            manager,
            service,
        )
        for service in SERVICES
    }
    owned = sum(row["owner"] == "manager" for row in rows.values())
    orphaned = sum(row["owner"] == "pid1_orphan" for row in rows.values())
    running = sum(bool(row["service_running"]) for row in rows.values())
    duplicates = sum(int(row["runsv_count"] > 1) for row in rows.values())
    zombies = zombie_runsv_children(table, set(managers))
    live_crond = crond_processes(table)
    crond_pidfile_pid, crond_pidfile_error = runtime_pidfile(
        prefix / "var" / "run" / "crond.pid"
    )
    failures = topology_failures(
        len(managers),
        owned,
        running,
        orphaned,
        duplicates,
        rows,
        live_crond,
        crond_pidfile_pid,
        crond_pidfile_error,
        zombie_runsv=zombies,
    )
    return {
        "schema_version": "1.3",
        "healthy": not failures,
        "manager_count": len(managers),
        "manager_pid": manager,
        "owned": owned,
        "required": len(SERVICES),
        "running": running,
        "orphaned": orphaned,
        "duplicate_service_rows": duplicates,
        "zombie_runsv": zombies,
        "services": rows,
        "live_crond": live_crond,
        "crond_pidfile": {
            "pid": crond_pidfile_pid,
            "error": crond_pidfile_error,
        },
        "failure_reasons": failures,
    }


def main() -> int:
    """Print JSON and return nonzero when topology is not healthy."""
    result = snapshot()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["healthy"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
