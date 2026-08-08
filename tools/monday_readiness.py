#!/usr/bin/env python3
"""Read-only BotA production reconciliation before market-open acceptance.

This command performs no Telegram, provider, Supabase, service, or crontab writes.
It deliberately consumes existing local truth rather than probing external APIs.
Use --market-open or --market-closed to make the expected market state explicit.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

PRODUCTION_PAIRS = ("EURUSD", "GBPUSD", "USDJPY")
PRODUCTION_TIMEFRAME = "M15"


def root_dir() -> Path:
    configured = os.environ.get("BOTA_ROOT", "").strip()
    return (
        Path(configured).expanduser().resolve()
        if configured
        else Path(__file__).resolve().parent.parent
    )


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} did not contain a JSON object")
    return value


def run_command(command: list[str], root: Path) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["BOTA_ROOT"] = str(root)
    return subprocess.run(
        command,
        cwd=root,
        env=environment,
        stdin=subprocess.DEVNULL,
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )


def append_check(
    checks: list[dict[str, Any]],
    name: str,
    healthy: bool,
    detail: Any,
) -> None:
    checks.append({"name": name, "healthy": bool(healthy), "detail": detail})


def check_production_scope(root: Path, checks: list[dict[str, Any]]) -> None:
    path = root / "ops" / "bota_crontab.canonical"
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        append_check(checks, "production_scope", False, type(exc).__name__)
        return
    markers = (
        'PAIRS="EURUSD GBPUSD USDJPY"',
        'TIMEFRAMES="M15"',
        "POLICY_B_ENABLED=1",
        "POLICY_B_SCORE_MIN=70",
        "POLICY_B_ADX_MAX=30",
    )
    missing = [marker for marker in markers if marker not in text]
    append_check(
        checks,
        "production_scope",
        not missing,
        {"pairs": list(PRODUCTION_PAIRS), "timeframe": PRODUCTION_TIMEFRAME, "missing": missing},
    )


def check_runtime_truth(
    root: Path,
    checks: list[dict[str, Any]],
    expected_market: str,
) -> None:
    path = root / "state" / "runtime_health.json"
    try:
        health = load_object(path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        append_check(checks, "runtime_truth", False, type(exc).__name__)
        return

    clock = health.get("clock_observability")
    clock_data = clock if isinstance(clock, dict) else {}
    bot_mode = str(health.get("bot_mode") or "UNKNOWN")
    market_state = str(health.get("market_state") or "error")
    clock_ok = (
        clock_data.get("server_clock_ok") is True
        and clock_data.get("trading_clock_available") is True
    )
    healthy = bot_mode == "HEALTHY" and market_state == expected_market and clock_ok
    append_check(
        checks,
        "runtime_truth",
        healthy,
        {
            "bot_mode": bot_mode,
            "market_state": market_state,
            "expected_market": expected_market,
            "server_clock_ok": clock_data.get("server_clock_ok"),
            "trading_clock_available": clock_data.get("trading_clock_available"),
            "local_clock_unsafe": clock_data.get("local_clock_unsafe"),
        },
    )


def check_control_plane(root: Path, checks: list[dict[str, Any]]) -> None:
    tool = root / "tools" / "control_plane_status.py"
    result = run_command([sys.executable, str(tool)], root)
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        data = {}
    healthy = result.returncode == 0 and isinstance(data, dict) and data.get("healthy") is True
    append_check(
        checks,
        "control_plane",
        healthy,
        {
            "returncode": result.returncode,
            "manager_count": data.get("manager_count") if isinstance(data, dict) else None,
            "owned": data.get("owned") if isinstance(data, dict) else None,
            "running": data.get("running") if isinstance(data, dict) else None,
            "orphaned": data.get("orphaned") if isinstance(data, dict) else None,
            "duplicate_service_rows": data.get("duplicate_service_rows") if isinstance(data, dict) else None,
        },
    )


def check_canonical_cron(root: Path, checks: list[dict[str, Any]]) -> None:
    tool = root / "tools" / "verify_canonical_crontab.sh"
    result = run_command(["bash", str(tool)], root)
    append_check(
        checks,
        "canonical_crontab",
        result.returncode == 0,
        {
            "returncode": result.returncode,
            "hash_match": "BOTA_BLOCK_HASH_MATCH=YES" in result.stdout,
            "phase2_verify": "PHASE2_VERIFY_PASS=YES" in result.stdout,
        },
    )


def check_pipeline(
    root: Path,
    checks: list[dict[str, Any]],
    market_open: bool,
) -> None:
    tool = root / "tools" / "pipeline_health.py"
    flag = "--market-open" if market_open else "--market-closed"
    result = run_command([sys.executable, str(tool), flag], root)
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        data = {}
    healthy = result.returncode == 0 and isinstance(data, dict) and data.get("healthy") is True
    append_check(
        checks,
        "pipeline_progress",
        healthy,
        {
            "returncode": result.returncode,
            "required_decisions": data.get("required_decisions") if isinstance(data, dict) else None,
            "failure_reasons": data.get("failure_reasons") if isinstance(data, dict) else None,
            "components": data.get("components") if isinstance(data, dict) else None,
        },
    )


def check_d1_caches(root: Path, checks: list[dict[str, Any]]) -> None:
    failures: list[str] = []
    details: dict[str, Any] = {}
    for pair in PRODUCTION_PAIRS:
        path = root / "cache" / f"d1_trend_{pair}.json"
        try:
            data = load_object(path)
            identity_ok = str(data.get("pair") or "").upper() == pair
            trend = str(data.get("trend") or "").upper()
            healthy = identity_ok and trend in {"BUY", "SELL"} and not data.get("error")
            details[pair] = {
                "healthy": healthy,
                "trend": trend,
                "source": data.get("source"),
            }
            if not healthy:
                failures.append(pair)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            failures.append(pair)
            details[pair] = {"healthy": False, "error": type(exc).__name__}
    append_check(checks, "d1_cache_identity", not failures, details)


def check_profitlab_cursor(root: Path, checks: list[dict[str, Any]]) -> None:
    alerts = root / "logs" / "alerts.csv"
    cursor = root / "state" / "profitlab_delivery_cursor.json"
    try:
        source_size = alerts.stat().st_size
        data = load_object(cursor)
        offset = int(data["offset"])
        state_source_size = int(data.get("source_size", source_size))
        healthy = 0 <= offset <= source_size and 0 <= state_source_size <= source_size
        detail = {
            "offset": offset,
            "source_size": source_size,
            "state_source_size": state_source_size,
            "pending_bytes": source_size - offset,
        }
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        healthy = False
        detail = {"error": type(exc).__name__}
    append_check(checks, "profitlab_cursor", healthy, detail)


def check_provider_accounting(root: Path, checks: list[dict[str, Any]]) -> None:
    path = root / "state" / "provider_usage.json"
    try:
        data = load_object(path)
        providers = data.get("providers")
        healthy = isinstance(providers, dict)
        detail = {
            "utc_date": data.get("utc_date"),
            "providers": sorted(providers) if isinstance(providers, dict) else None,
        }
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        healthy = False
        detail = {"error": type(exc).__name__}
    append_check(checks, "provider_accounting", healthy, detail)


def check_closer_files(root: Path, checks: list[dict[str, Any]]) -> None:
    required = (
        root / "tools" / "signal_closer.py",
        root / "tools" / "run_signal_closer_live.sh",
    )
    missing = [str(path.relative_to(root)) for path in required if not path.is_file()]
    append_check(checks, "closer_files", not missing, {"missing": missing})


def evaluate(market_open: bool) -> dict[str, Any]:
    root = root_dir()
    checks: list[dict[str, Any]] = []
    expected_market = "open" if market_open else "closed"

    check_production_scope(root, checks)
    check_runtime_truth(root, checks, expected_market)
    check_control_plane(root, checks)
    check_canonical_cron(root, checks)
    check_pipeline(root, checks, market_open)
    check_d1_caches(root, checks)
    check_profitlab_cursor(root, checks)
    check_provider_accounting(root, checks)
    check_closer_files(root, checks)

    failures = [check["name"] for check in checks if not check["healthy"]]
    return {
        "schema_version": "1.0",
        "read_only": True,
        "network_calls_requested": False,
        "service_mutation_performed": False,
        "crontab_mutation_performed": False,
        "strategy_changed": False,
        "expected_market_state": expected_market,
        "production_pairs": list(PRODUCTION_PAIRS),
        "production_timeframe": PRODUCTION_TIMEFRAME,
        "healthy": not failures,
        "checks": checks,
        "failure_reasons": failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--market-open", action="store_true")
    group.add_argument("--market-closed", action="store_true")
    args = parser.parse_args()

    result = evaluate(market_open=args.market_open)
    print(json.dumps(result, indent=2, sort_keys=True))
    print(f"MONDAY_READINESS={'PASS' if result['healthy'] else 'FAIL'}")
    return 0 if result["healthy"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
