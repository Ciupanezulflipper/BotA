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


def service_status(service_root: Path, service: str) -> tuple[bool, str]:
    """Read sv status without attempting any mutation."""
    try:
        result = subprocess.run(
            ["sv", "status", str(service_root / service)],
            text=True,
            capture_output=True,
            check=False,
            timeout=5,
        )
        output = (result.stdout or result.stderr).strip()
        return result.returncode == 0 and output.startswith("run:"), output
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, f"status_error:{type(exc).__name__}"


def snapshot() -> dict[str, Any]:
    """Build the exact seven-service ownership snapshot."""
    prefix = Path(os.environ.get("PREFIX", "/data/data/com.termux/files/usr"))
    service_root = prefix / "var" / "service"
    table = process_table()
    root_text = str(service_root)

    managers = [
        pid
        for pid, row in table.items()
        if basename(row) == "runsvdir" and root_text in " ".join(row.get("argv", [])[1:])
    ]
    manager = managers[0] if len(managers) == 1 else None
    rows: dict[str, Any] = {}
    owned = orphaned = running = duplicate = 0

    for service in SERVICES:
        candidates = [
            (pid, row)
            for pid, row in table.items()
            if basename(row) == "runsv" and (row.get("argv") or [])[-1:] == [service]
        ]
        if len(candidates) > 1:
            duplicate += 1
        runsv_pid = candidates[0][0] if len(candidates) == 1 else None
        runsv_ppid = candidates[0][1]["ppid"] if len(candidates) == 1 else None
        if manager is not None and runsv_ppid == manager:
            owner = "manager"
            owned += 1
        elif runsv_ppid == 1:
            owner = "pid1_orphan"
            orphaned += 1
        else:
            owner = "other_or_missing"

        is_running, status_text = service_status(service_root, service)
        running += int(is_running)
        try:
            wrapper_text = (service_root / service / "supervise" / "pid").read_text().strip()
            wrapper_pid = int(wrapper_text) if wrapper_text else None
        except (OSError, ValueError):
            wrapper_pid = None
        wrapper_alive = bool(wrapper_pid and Path(f"/proc/{wrapper_pid}").is_dir())

        rows[service] = {
            "runsv_count": len(candidates),
            "runsv_pid": runsv_pid,
            "runsv_ppid": runsv_ppid,
            "owner": owner,
            "service_running": is_running,
            "sv_status": status_text,
            "wrapper_pid": wrapper_pid,
            "wrapper_alive": wrapper_alive,
        }

    live_crond = [
        {
            "pid": pid,
            "ppid": row["ppid"],
            "argv": row.get("argv") or [],
        }
        for pid, row in table.items()
        if basename(row) == "crond" and "-n" in (row.get("argv") or []) and "-s" in (row.get("argv") or [])
    ]

    healthy = (
        len(managers) == 1
        and owned == len(SERVICES)
        and orphaned == 0
        and duplicate == 0
        and running == len(SERVICES)
        and len(live_crond) == 1
        and rows["crond"]["wrapper_pid"] == live_crond[0]["pid"]
    )

    return {
        "schema_version": "1.0",
        "healthy": healthy,
        "manager_count": len(managers),
        "manager_pid": manager,
        "owned": owned,
        "required": len(SERVICES),
        "running": running,
        "orphaned": orphaned,
        "duplicate_service_rows": duplicate,
        "services": rows,
        "live_crond": live_crond,
        "failure_reasons": [
            reason
            for condition, reason in (
                (len(managers) != 1, f"manager_count:{len(managers)}"),
                (owned != len(SERVICES), f"owned:{owned}/{len(SERVICES)}"),
                (running != len(SERVICES), f"running:{running}/{len(SERVICES)}"),
                (orphaned != 0, f"orphaned:{orphaned}"),
                (duplicate != 0, f"duplicate_service_rows:{duplicate}"),
                (len(live_crond) != 1, f"live_crond_count:{len(live_crond)}"),
                (
                    len(live_crond) == 1 and rows["crond"]["wrapper_pid"] != live_crond[0]["pid"],
                    "crond_not_owned_by_current_runsv",
                ),
            )
            if condition
        ],
    }


def main() -> int:
    """Print JSON and return nonzero when topology is not healthy."""
    result = snapshot()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["healthy"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
