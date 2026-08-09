#!/usr/bin/env python3
"""Fail-closed BotA pre-market production integrity gate.

This gate is read-only. It verifies control-plane ownership, watchdog/boot
persistence, cron ownership, immutable runtime content, production scope,
ProfitLab cursor preservation, trusted server clock availability, and fresh
updater/shadow progress. It does not run the watcher, send Telegram, bootstrap
ProfitLab, or change strategy/configuration.
"""
from __future__ import annotations

import argparse
import json
import os
import shlex
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any

if __package__:
    from tools import clock_drift_check
    from tools import control_plane_status
    from tools import native_service_daemon_migration as migration
    from tools import pipeline_health
else:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from tools import clock_drift_check
    from tools import control_plane_status
    from tools import native_service_daemon_migration as migration
    from tools import pipeline_health

PACKAGE_RUNTIME_PATHS = (
    "tools/native_service_daemon_watchdog.py",
    "tools/start_native_service_daemon_watchdog.sh",
    "tools/native_service_daemon_migration.py",
    "tools/native_service_daemon_watchdog_finalizer.py",
    "tools/native_service_boot_config.py",
    "tools/control_plane_status.py",
    "tools/pre_market_integrity.py",
)
SAFE_CONFIG_KEYS = (
    "PAIRS",
    "TIMEFRAMES",
    "POLICY_B_ENABLED",
    "POLICY_B_SCORE_MIN",
    "POLICY_B_ADX_MAX",
    "NEWS_ON",
    "TELEGRAM_ENABLED",
    "DRY_RUN_MODE",
)
EXPECTED_CONFIG = {
    "PAIRS": "EURUSD GBPUSD USDJPY",
    "TIMEFRAMES": "M15",
    "POLICY_B_ENABLED": "1",
    "POLICY_B_SCORE_MIN": "70",
    "POLICY_B_ADX_MAX": "30",
    "NEWS_ON": "0",
    "TELEGRAM_ENABLED": "1",
    "DRY_RUN_MODE": "0",
}
WATCHER_CRON_TOKENS = (
    "signal_watcher_pro.sh",
    "watcher_gated_cycle.sh",
    "run_signal_watcher_with_ledger.sh",
)
BOOT_BEGIN = "# BEGIN BOTA_NATIVE_SERVICE_WATCHDOG"
BOOT_END = "# END BOTA_NATIVE_SERVICE_WATCHDOG"


class IntegrityError(RuntimeError):
    """Raised when evidence cannot be collected safely."""


def valid_commit(value: str) -> bool:
    return len(value) == 40 and all(char in "0123456789abcdef" for char in value)


def parse_safe_env(path: Path) -> dict[str, str]:
    """Parse only non-secret production-scope keys from the runtime env file."""
    wanted = set(SAFE_CONFIG_KEYS)
    result: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        if "=" not in line:
            continue
        key, raw_value = line.split("=", 1)
        key = key.strip()
        if key not in wanted:
            continue
        try:
            tokens = shlex.split(raw_value, comments=True, posix=True)
        except ValueError as exc:
            raise IntegrityError(f"runtime_env_parse_failed:{key}") from exc
        result[key] = " ".join(tokens).strip()
    return result


def config_check(path: Path) -> dict[str, Any]:
    try:
        values = parse_safe_env(path)
    except (OSError, IntegrityError) as exc:
        return {"healthy": False, "values": {}, "failure_reasons": [str(exc)]}
    failures = [
        f"config_mismatch:{key}:actual={values.get(key)!r}:expected={expected!r}"
        for key, expected in EXPECTED_CONFIG.items()
        if values.get(key) != expected
    ]
    return {"healthy": not failures, "values": values, "failure_reasons": failures}


def active_cron_lines(text: str) -> list[str]:
    return [
        line.strip()
        for line in text.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def cron_check(text: str) -> dict[str, Any]:
    active = active_cron_lines(text)
    watcher = [
        line for line in active if any(token in line for token in WATCHER_CRON_TOKENS)
    ]
    profitlab = [line for line in active if "profitlab_delivery.py" in line]
    failures: list[str] = []
    if watcher:
        failures.append(f"active_direct_watcher_cron:{len(watcher)}")
    if len(profitlab) != 1:
        failures.append(f"profitlab_cron_count:{len(profitlab)}")
    return {
        "healthy": not failures,
        "active_direct_watcher_cron_count": len(watcher),
        "active_profitlab_cron_count": len(profitlab),
        "failure_reasons": failures,
    }


def boot_check(text: str) -> dict[str, Any]:
    lines = text.splitlines()
    begin = [i for i, line in enumerate(lines) if line.strip() == BOOT_BEGIN]
    end = [i for i, line in enumerate(lines) if line.strip() == BOOT_END]
    active = active_cron_lines(text)
    legacy = [line for line in active if "start_runsvdir_guard.sh" in line]
    watchdog = [
        line for line in active if "start_native_service_daemon_watchdog.sh" in line
    ]
    failures: list[str] = []
    if len(begin) != 1 or len(end) != 1 or begin[0] >= end[0]:
        failures.append(f"boot_managed_block:begin={len(begin)}:end={len(end)}")
    if legacy:
        failures.append(f"boot_active_legacy_guard:{len(legacy)}")
    if len(watchdog) != 1:
        failures.append(f"boot_active_native_watchdog:{len(watchdog)}")
    return {
        "healthy": not failures,
        "managed_block_count": 1 if not failures or (len(begin) == len(end) == 1) else 0,
        "active_legacy_guard_count": len(legacy),
        "active_native_watchdog_count": len(watchdog),
        "failure_reasons": failures,
    }


def run_text(argv: list[str], timeout: int = 15) -> str:
    try:
        result = subprocess.run(
            argv,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise IntegrityError(f"command_error:{argv[0]}:{type(exc).__name__}") from exc
    if result.returncode:
        detail = (result.stderr or result.stdout).strip()
        raise IntegrityError(
            f"command_failed:{argv[0]}:rc={result.returncode}:{detail[:240]}"
        )
    return result.stdout.strip()


def blob_for_commit(root: Path, commit: str, repo_path: str) -> str:
    return run_text(["git", "-C", str(root), "rev-parse", f"{commit}:{repo_path}"])


def blob_for_file(root: Path, runtime_path: Path) -> str:
    return run_text(["git", "-C", str(root), "hash-object", str(runtime_path)])


def parity_check(root: Path, commit: str) -> dict[str, Any]:
    results: dict[str, Any] = {}
    failures: list[str] = []
    for repo_path in PACKAGE_RUNTIME_PATHS:
        runtime_path = root / repo_path
        try:
            expected = blob_for_commit(root, commit, repo_path)
            actual = blob_for_file(root, runtime_path)
            mode = stat.S_IMODE(runtime_path.stat().st_mode)
        except (IntegrityError, OSError) as exc:
            results[repo_path] = {"healthy": False, "error": str(exc)}
            failures.append(f"runtime_parity_unreadable:{repo_path}:{exc}")
            continue
        healthy = expected == actual and mode == 0o755
        results[repo_path] = {
            "healthy": healthy,
            "expected_blob": expected,
            "actual_blob": actual,
            "mode": f"{mode:o}",
            "expected_runtime_mode": "755",
        }
        if expected != actual:
            failures.append(f"runtime_blob_mismatch:{repo_path}")
        if mode != 0o755:
            failures.append(f"runtime_mode_mismatch:{repo_path}:{mode:o}:755")

    wrapper_path = Path.home() / ".config/bota-sv/bota-watcher/run"
    try:
        expected = blob_for_commit(root, commit, "ops/runit/bota-watcher.run")
        actual = blob_for_file(root, wrapper_path)
        mode = stat.S_IMODE(wrapper_path.stat().st_mode)
        wrapper_healthy = expected == actual and mode == 0o755
        results["active_watcher_wrapper"] = {
            "healthy": wrapper_healthy,
            "path": str(wrapper_path),
            "expected_blob": expected,
            "actual_blob": actual,
            "mode": f"{mode:o}",
        }
        if not wrapper_healthy:
            failures.append("active_watcher_wrapper_parity")
    except (IntegrityError, OSError) as exc:
        results["active_watcher_wrapper"] = {"healthy": False, "error": str(exc)}
        failures.append(f"active_watcher_wrapper_unreadable:{exc}")

    return {"healthy": not failures, "files": results, "failure_reasons": failures}


def profitlab_check(root: Path) -> dict[str, Any]:
    cursor_path = root / "state/profitlab_delivery_cursor.json"
    alerts = root / "logs/alerts.csv"
    failures: list[str] = []
    try:
        cursor = json.loads(cursor_path.read_text(encoding="utf-8"))
        offset = int(cursor.get("offset"))
        size = alerts.stat().st_size
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        return {
            "healthy": False,
            "failure_reasons": [f"profitlab_state_unreadable:{type(exc).__name__}"],
        }
    pending = size - offset
    if offset < 0 or pending < 0:
        failures.append(f"profitlab_cursor_invalid:offset={offset}:size={size}")
    if pending != 0:
        failures.append(f"profitlab_pending_bytes:{pending}")
    return {
        "healthy": not failures,
        "cursor_offset": offset,
        "alerts_csv_size": size,
        "pending_bytes": pending,
        "failure_reasons": failures,
    }


def progress_check(root: Path) -> dict[str, Any]:
    path = root / "state/pipeline_progress.json"
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "healthy": False,
            "components": {},
            "failure_reasons": [f"pipeline_progress_unreadable:{type(exc).__name__}"],
        }
    current_boot = pipeline_health.boot_id()
    now_ns = pipeline_health.monotonic_ns()
    failures: list[str] = []
    if state.get("boot_id") != current_boot:
        failures.append("pipeline_progress_missing_for_current_boot")
    components = state.get("components") if isinstance(state.get("components"), dict) else {}
    results: dict[str, Any] = {}
    thresholds = {
        "updater": int(os.environ.get("MAX_UPDATER_PROGRESS_AGE_SECS", "1500")),
        "shadow": int(os.environ.get("MAX_SHADOW_PROGRESS_AGE_SECS", "1500")),
    }
    start_grace = int(os.environ.get("MAX_COMPONENT_START_GRACE_SECS", "300"))
    for name, maximum in thresholds.items():
        event = pipeline_health.event_map(components, name)
        result = pipeline_health.component_health(
            name, event, now_ns, maximum, start_grace
        )
        results[name] = result
        if not result["healthy"]:
            failures.append(
                f"{name}_progress_stale_or_failed:"
                f"{result['age_seconds']}:{result['status']}:{result['evaluation']}"
            )
        for counter in ("fetch_fail_count", "build_fail_count"):
            value = event.get(counter)
            if value is None:
                continue
            try:
                numeric = int(value)
            except (TypeError, ValueError):
                failures.append(f"{name}_{counter}_invalid:{value}")
                continue
            if numeric:
                failures.append(f"{name}_{counter}:{numeric}")
    return {
        "healthy": not failures,
        "boot_id": current_boot,
        "components": results,
        "failure_reasons": failures,
    }


def clock_check(timeout: int) -> dict[str, Any]:
    result = clock_drift_check.compute_server_clock(
        clock_drift_check.DEFAULT_URLS,
        timeout=timeout,
        max_spread_seconds=int(os.environ.get("CLOCK_SERVER_MAX_SPREAD_SECS", "120")),
    )
    failures = [] if result.ok else [f"trusted_server_clock:{result.reason}"]
    return {
        "healthy": result.ok,
        "server_epoch": result.server_epoch,
        "server_iso": result.server_iso,
        "server_sources_count": result.count,
        "server_spread_seconds": result.spread_seconds,
        "reason": result.reason,
        "failure_reasons": failures,
    }


def process_ownership_check(root: Path) -> dict[str, Any]:
    watchdog_script = root / "tools/native_service_daemon_watchdog.py"
    legacy_script = root / "tools/runsvdir_guard_runtime.py"
    watchdog_pids = migration.process_matches(watchdog_script)
    legacy_pids = migration.process_matches(legacy_script)
    failures: list[str] = []
    if len(watchdog_pids) != 1:
        failures.append(f"native_watchdog_count:{len(watchdog_pids)}")
    if legacy_pids:
        failures.append(f"legacy_guard_count:{len(legacy_pids)}")
    return {
        "healthy": not failures,
        "native_watchdog_pids": watchdog_pids,
        "legacy_guard_pids": legacy_pids,
        "failure_reasons": failures,
    }


def flatten_failures(checks: dict[str, dict[str, Any]]) -> list[str]:
    failures: list[str] = []
    for name, result in checks.items():
        for reason in result.get("failure_reasons", []):
            failures.append(f"{name}:{reason}")
    return failures


def collect(root: Path, prefix: Path, source_commit: str, clock_timeout: int) -> dict[str, Any]:
    if not valid_commit(source_commit):
        raise IntegrityError("invalid_source_commit")
    try:
        run_text(["git", "-C", str(root), "cat-file", "-e", f"{source_commit}^{{commit}}"])
    except IntegrityError as exc:
        raise IntegrityError(f"source_commit_not_fetched:{source_commit}") from exc

    try:
        crontab = run_text(["crontab", "-l"])
    except IntegrityError as exc:
        crontab = ""
        cron_result = {
            "healthy": False,
            "active_direct_watcher_cron_count": None,
            "active_profitlab_cron_count": None,
            "failure_reasons": [str(exc)],
        }
    else:
        cron_result = cron_check(crontab)

    boot_path = Path.home() / ".termux/boot/00-termux-services.sh"
    try:
        boot_result = boot_check(boot_path.read_text(encoding="utf-8"))
    except OSError as exc:
        boot_result = {
            "healthy": False,
            "failure_reasons": [f"boot_file_unreadable:{type(exc).__name__}"],
        }

    control = control_plane_status.snapshot()
    control_result = {
        "healthy": bool(control.get("healthy")),
        "snapshot": control,
        "failure_reasons": list(control.get("failure_reasons") or []),
    }
    checks = {
        "control_plane": control_result,
        "watchdog_ownership": process_ownership_check(root),
        "boot_persistence": boot_result,
        "cron_ownership": cron_result,
        "runtime_parity": parity_check(root, source_commit),
        "production_config": config_check(root / ".env.runtime"),
        "profitlab": profitlab_check(root),
        "progress": progress_check(root),
        "trusted_clock": clock_check(clock_timeout),
    }
    failures = flatten_failures(checks)
    return {
        "schema_version": "1.0",
        "healthy": not failures,
        "source_commit": source_commit,
        "root": str(root),
        "prefix": str(prefix),
        "checks": checks,
        "failure_reasons": failures,
        "mutated": False,
        "strategy_changed": False,
    }


def arguments() -> argparse.Namespace:
    prefix = Path(os.environ.get("PREFIX", "/data/data/com.termux/files/usr"))
    root = Path(os.environ.get("BOTA_ROOT", str(Path.home() / "BotA")))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--root", type=Path, default=root)
    parser.add_argument("--prefix", type=Path, default=prefix)
    parser.add_argument("--clock-timeout", type=int, default=6)
    return parser.parse_args()


def main() -> int:
    args = arguments()
    try:
        result = collect(
            args.root.resolve(),
            args.prefix.resolve(),
            args.source_commit,
            args.clock_timeout,
        )
    except IntegrityError as exc:
        result = {
            "schema_version": "1.0",
            "healthy": False,
            "failure_reasons": [str(exc)],
            "mutated": False,
            "strategy_changed": False,
        }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["healthy"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
