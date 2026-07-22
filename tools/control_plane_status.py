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
    """Return runsvdir processes managing the standard Termux service root."""
    root_text = str(service_root)
    return [
        pid
        for pid, row in table.items()
        if basename(row) == "runsvdir"
        and root_text in " ".join(row.get("argv", [])[1:])
    ]


def runsv_candidates(
    table: dict[int, dict[str, Any]],
    service: str,
) -> list[tuple[int, dict[str, Any]]]:
    """Return exact runsv processes for one service name."""
    return [
        (pid, row)
        for pid, row in table.items()
        if basename(row) == "runsv"
        and (row.get("argv") or [])[-1:] == [service]
    ]


def wrapper_pid(service_root: Path, service: str) -> int | None:
    """Read the current supervised child PID when available."""
    try:
        value = (service_root / service / "supervise" / "pid").read_text().strip()
        return int(value) if value else None
    except (OSError, ValueError):
        return None


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
    child_alive = bool(child_pid and Path(f"/proc/{child_pid}").is_dir())
    return {
        "runsv_count": len(candidates),
        "runsv_pid": runsv_pid,
        "runsv_ppid": runsv_ppid,
        "owner": owner,
        "service_running": is_running,
        "sv_status": status_text,
        "wrapper_pid": child_pid,
        "wrapper_alive": child_alive,
    }


def crond_processes(table: dict[int, dict[str, Any]]) -> list[dict[str, Any]]:
    """Return live foreground crond processes and parentage."""
    return [
        {
            "pid": pid,
            "ppid": row["ppid"],
            "argv": row.get("argv") or [],
        }
        for pid, row in table.items()
        if basename(row) == "crond"
        and "-n" in (row.get("argv") or [])
        and "-s" in (row.get("argv") or [])
    ]


def topology_failures(
    manager_count: int,
    owned: int,
    running: int,
    orphaned: int,
    duplicates: int,
    rows: dict[str, Any],
    live_crond: list[dict[str, Any]],
) -> list[str]:
    """Build compact acceptance failures from an inspected topology."""
    failures: list[str] = []
    checks = (
        (manager_count != 1, f"manager_count:{manager_count}"),
        (owned != len(SERVICES), f"owned:{owned}/{len(SERVICES)}"),
        (running != len(SERVICES), f"running:{running}/{len(SERVICES)}"),
        (orphaned != 0, f"orphaned:{orphaned}"),
        (duplicates != 0, f"duplicate_service_rows:{duplicates}"),
        (len(live_crond) != 1, f"live_crond_count:{len(live_crond)}"),
    )
    failures.extend(reason for failed, reason in checks if failed)
    if (
        len(live_crond) == 1
        and rows.get("crond", {}).get("wrapper_pid") != live_crond[0]["pid"]
    ):
        failures.append("crond_not_owned_by_current_runsv")
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
    live_crond = crond_processes(table)
    failures = topology_failures(
        len(managers),
        owned,
        running,
        orphaned,
        duplicates,
        rows,
        live_crond,
    )
    return {
        "schema_version": "1.1",
        "healthy": not failures,
        "manager_count": len(managers),
        "manager_pid": manager,
        "owned": owned,
        "required": len(SERVICES),
        "running": running,
        "orphaned": orphaned,
        "duplicate_service_rows": duplicates,
        "services": rows,
        "live_crond": live_crond,
        "failure_reasons": failures,
    }


def main() -> int:
    """Print JSON and return nonzero when topology is not healthy."""
    result = snapshot()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["healthy"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
