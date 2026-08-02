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


def snapshot_status(present: bool, valid: bool, data: dict[str, Any]) -> str:
    """Return the status recorded by the periodic clock snapshot."""
    if not present:
        return "MISSING"
    if not valid:
        return "INVALID"
    return compact_detail(data.get("status") or "UNKNOWN")


def snapshot_values(data: dict[str, Any], valid: bool) -> dict[str, Any]:
    """Extract typed values from a valid clock snapshot."""
    if not valid:
        return {
            "server_clock_ok": None,
            "local_clock_unsafe": None,
            "drift_seconds": None,
            "server_reason": "",
            "generated_utc": "",
        }
    return {
        "server_clock_ok": optional_bool(data.get("server_clock_ok")),
        "local_clock_unsafe": optional_bool(data.get("local_clock_unsafe")),
        "drift_seconds": finite_number(data.get("drift_seconds")),
        "server_reason": compact_detail(data.get("server_reason") or ""),
        "generated_utc": compact_detail(data.get("generated_utc") or ""),
    }


def effective_clock_available(
    market_gate: dict[str, Any],
    server_clock_ok: bool | None,
) -> bool | None:
    """Prefer live market-gate clock evidence over the periodic snapshot."""
    gate_clock = market_gate.get("trusted_server_clock_available")
    if isinstance(gate_clock, bool):
        return gate_clock
    return server_clock_ok


def availability_status(available: bool | None) -> str:
    """Map effective clock availability to a stable status string."""
    if available is True:
        return "AVAILABLE"
    if available is False:
        return "UNAVAILABLE"
    return "UNKNOWN"


def gate_overrode_snapshot(
    market_gate: dict[str, Any],
    server_clock_ok: bool | None,
) -> bool:
    """Return whether current live evidence contradicts the older snapshot."""
    gate_clock = market_gate.get("trusted_server_clock_available")
    return (
        isinstance(gate_clock, bool)
        and isinstance(server_clock_ok, bool)
        and gate_clock is not server_clock_ok
    )


def normalize_clock_observability(
    clock_path: Path,
    market_gate: dict[str, Any],
) -> dict[str, Any]:
    """Build the non-fatal clock observability object."""
    data, present, valid = load_clock_file(clock_path)
    values = snapshot_values(data, valid)
    server_clock_ok = values["server_clock_ok"]
    trading_clock_available = effective_clock_available(
        market_gate,
        server_clock_ok,
    )

    return {
        "status": availability_status(trading_clock_available),
        "snapshot_status": snapshot_status(present, valid, data),
        "source_file_present": present,
        "source_file_valid": valid,
        "server_clock_ok": server_clock_ok,
        "trading_clock_available": trading_clock_available,
        "live_gate_overrode_snapshot": gate_overrode_snapshot(
            market_gate,
            server_clock_ok,
        ),
        "local_clock_unsafe": values["local_clock_unsafe"],
        "local_clock_warning": (
            server_clock_ok is True and values["local_clock_unsafe"] is True
        ),
        "drift_seconds": values["drift_seconds"],
        "server_reason": values["server_reason"],
        "generated_utc": values["generated_utc"],
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
