#!/usr/bin/env python3
"""Normalize BotA market-gate and clock observability for the supervisor.

This module reports clock availability separately from control-plane and pipeline
health. It never decides whether a trade may execute and never mutates services.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


MAX_DETAIL_CHARS = 240


def compact_detail(value: Any) -> str:
    """Return a bounded single-line diagnostic."""
    return str(value).replace("\r", " ").replace("\n", "|")[:MAX_DETAIL_CHARS]


def finite_number(value: Any) -> float | None:
    """Return a finite float, or ``None``."""
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if math.isfinite(number) else None


def optional_bool(value: Any) -> bool | None:
    """Return a real boolean, or ``None`` for unknown values."""
    return value if isinstance(value, bool) else None


def read_text(path: Path) -> str:
    """Read a small text file without failing the caller."""
    try:
        return path.read_text(encoding="utf-8", errors="replace")[:4096]
    except OSError:
        return ""


def load_clock_file(path: Path) -> tuple[dict[str, Any], bool, bool]:
    """Load the clock status object and return data/present/valid flags."""
    if not path.exists():
        return {}, False, False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}, True, False
    if not isinstance(data, dict):
        return {}, True, False
    return data, True, True


def classify_market_gate(
    exit_code: int,
    stdout: str,
    stderr: str,
) -> dict[str, Any]:
    """Classify the live market gate without changing its fail-closed result."""
    output = stdout.strip()
    diagnostic = compact_detail(stderr.strip())

    if exit_code == 0 and output == "Open":
        return {
            "state": "open",
            "reason": "market_open",
            "exit_code": 0,
            "trusted_server_clock_available": True,
            "diagnostic": diagnostic,
        }

    lowered = stderr.lower()
    if "server_clock_unavailable" in lowered or "clock_unavailable" in lowered:
        return {
            "state": "clock_unavailable",
            "reason": "server_clock_unavailable",
            "exit_code": exit_code,
            "trusted_server_clock_available": False,
            "diagnostic": diagnostic,
        }

    if exit_code != 0 and output == "Closed":
        return {
            "state": "closed",
            "reason": "market_closed",
            "exit_code": exit_code,
            "trusted_server_clock_available": True,
            "diagnostic": diagnostic,
        }

    return {
        "state": "error",
        "reason": "market_gate_error",
        "exit_code": exit_code,
        "trusted_server_clock_available": None,
        "diagnostic": diagnostic or compact_detail(output),
    }


def normalize_clock_observability(
    clock_path: Path,
    market_gate: dict[str, Any],
) -> dict[str, Any]:
    """Build the non-fatal clock observability object."""
    data, present, valid = load_clock_file(clock_path)

    if not present:
        snapshot_status = "MISSING"
    elif not valid:
        snapshot_status = "INVALID"
    else:
        snapshot_status = compact_detail(data.get("status") or "UNKNOWN")

    server_clock_ok = optional_bool(data.get("server_clock_ok")) if valid else None
    local_clock_unsafe = optional_bool(data.get("local_clock_unsafe")) if valid else None
    drift_seconds = finite_number(data.get("drift_seconds")) if valid else None
    server_reason = compact_detail(data.get("server_reason") or "") if valid else ""
    generated_utc = compact_detail(data.get("generated_utc") or "") if valid else ""

    gate_clock = market_gate.get("trusted_server_clock_available")
    if isinstance(gate_clock, bool):
        trading_clock_available: bool | None = gate_clock
    else:
        trading_clock_available = server_clock_ok

    if trading_clock_available is True:
        status = "AVAILABLE"
    elif trading_clock_available is False:
        status = "UNAVAILABLE"
    else:
        status = "UNKNOWN"

    live_gate_overrode_snapshot = (
        isinstance(gate_clock, bool)
        and isinstance(server_clock_ok, bool)
        and gate_clock is not server_clock_ok
    )

    return {
        "status": status,
        "snapshot_status": snapshot_status,
        "source_file_present": present,
        "source_file_valid": valid,
        "server_clock_ok": server_clock_ok,
        "trading_clock_available": trading_clock_available,
        "live_gate_overrode_snapshot": live_gate_overrode_snapshot,
        "local_clock_unsafe": local_clock_unsafe,
        "local_clock_warning": server_clock_ok is True and local_clock_unsafe is True,
        "drift_seconds": drift_seconds,
        "server_reason": server_reason,
        "generated_utc": generated_utc,
        "runtime_failure": False,
    }


def build_report(
    clock_path: Path,
    market_exit_code: int,
    market_stdout_path: Path,
    market_stderr_path: Path,
) -> dict[str, Any]:
    """Build the complete supervisor clock report."""
    market_gate = classify_market_gate(
        market_exit_code,
        read_text(market_stdout_path),
        read_text(market_stderr_path),
    )
    return {
        "schema_version": "1.0",
        "market_gate": market_gate,
        "clock_observability": normalize_clock_observability(clock_path, market_gate),
        "service_mutation_performed": False,
        "strategy_changed": False,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--clock-file", type=Path, required=True)
    parser.add_argument("--market-exit-code", type=int, required=True)
    parser.add_argument("--market-stdout-file", type=Path, required=True)
    parser.add_argument("--market-stderr-file", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Print normalized clock and market-gate observability JSON."""
    args = parse_args(argv)
    report = build_report(
        args.clock_file,
        args.market_exit_code,
        args.market_stdout_file,
        args.market_stderr_file,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
