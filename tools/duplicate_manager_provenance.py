#!/usr/bin/env python3
"""Read-only provenance collector for duplicate Termux runsvdir managers.

This tool does not signal processes, mutate pidfiles, restart services, or write
runtime state. It prints one JSON document to stdout containing the evidence
needed to attribute a native service-daemon manager to a creator path.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Any, Iterable

RELEVANT_PATTERNS = (
    "service-daemon",
    "runsvdir",
    "native_service_daemon",
    "start_native_service_daemon_watchdog",
    "native_manager_started",
    "new_manager_pid",
    "manager_pid",
)


def read_text(path: Path, limit: int = 2_000_000) -> str | None:
    try:
        data = path.read_bytes()
    except (OSError, PermissionError):
        return None
    if len(data) > limit:
        data = data[-limit:]
    return data.decode("utf-8", errors="replace")


def stat_record(path: Path) -> dict[str, Any]:
    try:
        st = path.stat()
    except OSError as exc:
        return {"path": str(path), "exists": False, "error": str(exc)}
    return {
        "path": str(path),
        "exists": True,
        "size": st.st_size,
        "mode": oct(st.st_mode & 0o7777),
        "mtime_ns": st.st_mtime_ns,
        "mtime_epoch": st.st_mtime,
        "ctime_ns": st.st_ctime_ns,
    }


def proc_status_value(pid: int, key: str) -> int | None:
    text = read_text(Path(f"/proc/{pid}/status"), limit=256_000)
    if text is None:
        return None
    prefix = f"{key}:"
    for line in text.splitlines():
        if line.startswith(prefix):
            parts = line.split()
            if len(parts) >= 2 and parts[1].isdigit():
                return int(parts[1])
    return None


def proc_cmdline(pid: int) -> list[str]:
    try:
        raw = Path(f"/proc/{pid}/cmdline").read_bytes()
    except OSError:
        return []
    return [part.decode("utf-8", errors="replace") for part in raw.split(b"\0") if part]


def proc_start_ticks(pid: int) -> int | None:
    """Return Linux /proc/<pid>/stat field 22 safely around '(comm)' spaces."""
    text = read_text(Path(f"/proc/{pid}/stat"), limit=64_000)
    if not text:
        return None
    close = text.rfind(")")
    if close < 0:
        return None
    fields_after_comm = text[close + 2 :].split()
    # field 3 is fields_after_comm[0], therefore field 22 is index 19.
    if len(fields_after_comm) <= 19:
        return None
    try:
        return int(fields_after_comm[19])
    except ValueError:
        return None


def process_record(pid: int) -> dict[str, Any]:
    proc = Path(f"/proc/{pid}")
    record: dict[str, Any] = {"pid": pid, "alive": proc.is_dir()}
    if not record["alive"]:
        return record

    record.update(
        {
            "ppid": proc_status_value(pid, "PPid"),
            "argv": proc_cmdline(pid),
            "start_ticks": proc_start_ticks(pid),
        }
    )
    for name in ("cwd", "exe"):
        try:
            record[name] = os.readlink(proc / name)
        except OSError:
            record[name] = None
    return record


def iter_numeric_proc() -> Iterable[int]:
    try:
        entries = Path("/proc").iterdir()
    except OSError:
        return []
    result = []
    for entry in entries:
        if entry.name.isdigit():
            result.append(int(entry.name))
    return sorted(result)


def matching_processes(service_root: Path) -> dict[str, list[dict[str, Any]]]:
    managers: list[dict[str, Any]] = []
    runsv: list[dict[str, Any]] = []
    watchdogs: list[dict[str, Any]] = []
    migrations: list[dict[str, Any]] = []
    root = str(service_root)

    for pid in iter_numeric_proc():
        argv = proc_cmdline(pid)
        if not argv:
            continue
        exe_name = Path(argv[0]).name
        joined = " ".join(argv)
        if exe_name == "runsvdir" and root in argv:
            managers.append(process_record(pid))
        elif exe_name == "runsv":
            row = process_record(pid)
            if len(argv) > 1:
                row["service"] = argv[1]
            runsv.append(row)
        if "native_service_daemon_watchdog.py" in joined:
            watchdogs.append(process_record(pid))
        if "native_service_daemon_migration.py" in joined:
            migrations.append(process_record(pid))

    return {
        "managers": managers,
        "runsv": runsv,
        "watchdogs": watchdogs,
        "migrations": migrations,
    }


def relevant_lines(path: Path, patterns: Iterable[str] = RELEVANT_PATTERNS) -> dict[str, Any]:
    text = read_text(path)
    if text is None:
        return {**stat_record(path), "matching_lines": []}
    lowered = tuple(pattern.lower() for pattern in patterns)
    matches = []
    for number, line in enumerate(text.splitlines(), start=1):
        low = line.lower()
        if any(pattern in low for pattern in lowered):
            matches.append({"line": number, "text": line[:2000]})
    return {**stat_record(path), "matching_lines": matches[-300:]}


def jsonl_records(path: Path) -> list[dict[str, Any]]:
    text = read_text(path)
    if text is None:
        return []
    rows = []
    for number, line in enumerate(text.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            value = dict(value)
            value["_line"] = number
            rows.append(value)
    return rows


def candidate_files(root: Path, home: Path, prefix: Path) -> list[Path]:
    candidates = [
        root / "logs/native_service_daemon_watchdog.jsonl",
        root / "logs/native_service_daemon_watchdog.launch.log",
        root / "logs/runsvdir_guard.log",
        root / "logs/runsvdir_guard_runtime.log",
        home / ".termux/boot/00-termux-services.sh",
        home / ".bash_history",
        home / ".zsh_history",
        prefix / "bin/service-daemon",
        prefix / "etc/profile.d/start-services.sh",
        root / "tools/start_native_service_daemon_watchdog.sh",
        root / "tools/start_runsvdir_guard.sh",
        root / "tools/native_service_daemon_watchdog.py",
        root / "tools/native_service_daemon_migration.py",
    ]

    for base in (root / "audits", root / "logs", home / ".termux/boot", prefix / "etc/profile.d"):
        try:
            entries = sorted(base.iterdir())
        except OSError:
            continue
        for entry in entries:
            name = entry.name.lower()
            if entry.is_file() and any(token in name for token in ("service", "runsv", "watchdog", "migration", "boot")):
                candidates.append(entry)
            elif entry.is_dir() and base.name == "audits":
                try:
                    nested = sorted(entry.rglob("*"))
                except OSError:
                    continue
                for nested_path in nested:
                    if nested_path.is_file() and nested_path.stat().st_size <= 5_000_000:
                        candidates.append(nested_path)

    deduped = []
    seen = set()
    for path in candidates:
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        if path.exists() and path.is_file():
            deduped.append(path)
    return deduped


def find_lock_holders(lock_path: Path) -> list[int]:
    holders = []
    target = str(lock_path.resolve()) if lock_path.exists() else str(lock_path)
    for pid in iter_numeric_proc():
        fd_dir = Path(f"/proc/{pid}/fd")
        try:
            fds = list(fd_dir.iterdir())
        except OSError:
            continue
        for fd in fds:
            try:
                linked = os.readlink(fd)
            except OSError:
                continue
            if linked == target:
                holders.append(pid)
                break
    return holders


def git_read_only(root: Path) -> dict[str, Any]:
    commands = {
        "status": ["git", "status", "--short", "--branch"],
        "recent_service_daemon_commits": [
            "git", "log", "--all", "--date=iso", "--pretty=format:%H%x09%ad%x09%s",
            "-n", "40", "--", "tools/native_service_daemon_watchdog.py",
            "tools/native_service_daemon_migration.py", "tools/runsvdir_guard.py",
        ],
    }
    result: dict[str, Any] = {}
    for name, argv in commands.items():
        try:
            completed = subprocess.run(
                argv,
                cwd=root,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=10,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            result[name] = {"error": str(exc)}
            continue
        result[name] = {
            "returncode": completed.returncode,
            "stdout": completed.stdout[-100_000:],
            "stderr": completed.stderr[-20_000:],
        }
    return result


def direct_pid_evidence(paths: Iterable[Path], target_pid: int) -> list[dict[str, Any]]:
    needle = str(target_pid)
    hits = []
    for path in paths:
        text = read_text(path)
        if text is None or needle not in text:
            continue
        lines = []
        for number, line in enumerate(text.splitlines(), start=1):
            if needle in line:
                lines.append({"line": number, "text": line[:2000]})
        if lines:
            hits.append({"path": str(path), "lines": lines[-100:]})
    return hits


def infer_attribution(
    target_pid: int,
    watchdog_log: Path,
    files: Iterable[Path],
) -> dict[str, Any]:
    evidence: list[dict[str, Any]] = []

    for row in jsonl_records(watchdog_log):
        if row.get("manager_pid") == target_pid:
            evidence.append(
                {
                    "source": str(watchdog_log),
                    "kind": "watchdog_jsonl_manager_pid",
                    "record": row,
                }
            )
            if row.get("native_manager_started") is True:
                return {
                    "status": "PROVEN",
                    "creator_class": "native_service_daemon_watchdog",
                    "evidence": evidence,
                }

    for path in files:
        if not path.name.endswith(".json"):
            continue
        text = read_text(path)
        if text is None:
            continue
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue

        direct_values = {
            "new_manager_pid": payload.get("new_manager_pid"),
            "manager_pid": payload.get("manager_pid"),
        }
        final = payload.get("final")
        if isinstance(final, dict):
            direct_values["final.manager_pid"] = final.get("manager_pid")
        if target_pid in direct_values.values():
            evidence.append(
                {
                    "source": str(path),
                    "kind": "structured_result_manager_pid",
                    "matching_fields": [key for key, value in direct_values.items() if value == target_pid],
                }
            )
            low = str(path).lower()
            if "migration" in low:
                return {
                    "status": "PROVEN",
                    "creator_class": "native_service_daemon_migration",
                    "evidence": evidence,
                }
            if "finalizer" in low:
                return {
                    "status": "PROVEN",
                    "creator_class": "native_service_daemon_finalizer",
                    "evidence": evidence,
                }

    pid_hits = direct_pid_evidence(files, target_pid)
    if pid_hits:
        evidence.extend(
            {"source": hit["path"], "kind": "target_pid_text_hit", "lines": hit["lines"]}
            for hit in pid_hits
        )
        return {"status": "PARTIAL", "creator_class": "UNRESOLVED", "evidence": evidence}

    return {"status": "UNKNOWN", "creator_class": "UNRESOLVED", "evidence": evidence}


def timing_record(pid: int, pidfile: Path) -> dict[str, Any]:
    ticks = proc_start_ticks(pid)
    try:
        hz = os.sysconf(os.sysconf_names["SC_CLK_TCK"])
    except (ValueError, OSError, KeyError):
        hz = None
    clock = getattr(time, "CLOCK_BOOTTIME", time.CLOCK_MONOTONIC)
    boottime_now = time.clock_gettime(clock)
    wall_now = time.time()
    result: dict[str, Any] = {
        "pid": pid,
        "start_ticks": ticks,
        "clock_ticks_per_second": hz,
        "boottime_now_seconds": boottime_now,
        "wall_now_epoch": wall_now,
        "wall_time_warning": "wall-clock values are display/correlation only; do not use for trading semantics",
        "pidfile": stat_record(pidfile),
    }
    if ticks is not None and hz:
        start_boot_seconds = ticks / hz
        result["process_start_boottime_seconds"] = start_boot_seconds
        result["process_age_seconds"] = boottime_now - start_boot_seconds
        result["estimated_process_start_epoch"] = wall_now - (boottime_now - start_boot_seconds)
        if result["pidfile"].get("exists"):
            result["pidfile_mtime_minus_estimated_start_seconds"] = (
                result["pidfile"]["mtime_epoch"] - result["estimated_process_start_epoch"]
            )
    return result


def arguments() -> argparse.Namespace:
    prefix = Path(os.environ.get("PREFIX", "/data/data/com.termux/files/usr"))
    home = Path.home()
    root = Path(os.environ.get("BOTA_ROOT", str(home / "BotA")))
    parser = argparse.ArgumentParser()
    parser.add_argument("--target-pid", type=int, default=31140)
    parser.add_argument("--peer-pid", type=int, default=16360)
    parser.add_argument("--root", type=Path, default=root)
    parser.add_argument("--prefix", type=Path, default=prefix)
    parser.add_argument("--home", type=Path, default=home)
    return parser.parse_args()


def main() -> int:
    args = arguments()
    root = args.root.resolve()
    prefix = args.prefix.resolve()
    home = args.home.resolve()
    service_root = prefix / "var/service"
    pidfile = prefix / "var/run/service-daemon.pid"
    watchdog_log = root / "logs/native_service_daemon_watchdog.jsonl"
    lock_path = root / "state/native_service_daemon_watchdog.lock"

    files = candidate_files(root, home, prefix)
    snapshots = [relevant_lines(path) for path in files]
    pidfile_text = read_text(pidfile, limit=4096)

    payload = {
        "schema_version": "1.0",
        "mutation_performed": False,
        "target_pid": args.target_pid,
        "peer_pid": args.peer_pid,
        "target_process": process_record(args.target_pid),
        "peer_process": process_record(args.peer_pid),
        "target_timing": timing_record(args.target_pid, pidfile),
        "pidfile": {
            **stat_record(pidfile),
            "content": pidfile_text.strip() if pidfile_text is not None else None,
        },
        "process_topology": matching_processes(service_root),
        "watchdog_lock": {
            **stat_record(lock_path),
            "holders": find_lock_holders(lock_path),
        },
        "creator_attribution": infer_attribution(args.target_pid, watchdog_log, files),
        "evidence_files": snapshots,
        "git": git_read_only(root),
        "safety": {
            "signals_sent": False,
            "services_restarted": False,
            "pidfile_changed": False,
            "files_written": False,
        },
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
