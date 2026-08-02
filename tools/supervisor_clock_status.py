#!/usr/bin/env python3
"""Normalize BotA market-gate and clock observability for the supervisor.

This module reports clock availability separately from control-plane and pipeline
health. It consumes bounded data supplied by the supervisor, never opens caller-
provided paths, never decides whether a trade may execute, and never mutates
services.
"""

from __future__ import annotations

import json
import math
import os
from typing import Any


MAX_DETAIL_CHARS = 240
MAX_MARKET_TEXT_CHARS = 4096
MAX_CLOCK_JSON_CHARS = 16384


def compact_detail(value: Any) -> str:
    """Return a bounded single-line diagnostic."""
    return str(value).replace("\r", " ").replace("\n", "|")[:MAX_DETAIL_CHARS]


def bounded_text(value: Any, limit: int) -> str:
    """Return text bounded before parsing or classification."""
    return str(value)[:limit]


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


def parse_exit_code(value: Any) -> int:
    """Return a bounded process exit code, defaulting to an error value."""
    try:
        code = int(value)
    except (TypeError, ValueError, OverflowError):
        return 255
    return min(max(code, 0), 255)


def load_clock_payload(raw_json: str, present: bool) -> tuple[dict[str, Any], bool, bool]:
    """Load clock JSON data and return data/present/valid flags."""
    if not present:
        return {}, False, False
    try:
        data = json.loads(bounded_text(raw_json, MAX_CLOCK_JSON_CHARS))
    except json.JSONDecodeError:
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
    output = bounded_text(stdout, MAX_MARKET_TEXT_CHARS).strip()
    bounded_stderr = bounded_text(stderr, MAX_MARKET_TEXT_CHARS)
    diagnostic = compact_detail(bounded_stderr.strip())

    if exit_code == 0 and output == "Open":
        return {
            "state": "open",
            "reason": "market_open",
            "exit_code": 0,
            "trusted_server_clock_available": True,
            "diagnostic": diagnostic,
        }

    lowered = bounded_stderr.lower()
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
    raw_clock_json: str,
    clock_present: bool,
    market_gate: dict[str, Any],
) -> dict[str, Any]:
    """Build the non-fatal clock observability object."""
    data, present, valid = load_clock_payload(raw_clock_json, clock_present)
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
    raw_clock_json: str,
    clock_present: bool,
    market_exit_code: int,
    market_stdout: str,
    market_stderr: str,
) -> dict[str, Any]:
    """Build the complete supervisor clock report from bounded data."""
    market_gate = classify_market_gate(
        market_exit_code,
        market_stdout,
        market_stderr,
    )
    return {
        "schema_version": "1.0",
        "market_gate": market_gate,
        "clock_observability": normalize_clock_observability(
            raw_clock_json,
            clock_present,
            market_gate,
        ),
        "service_mutation_performed": False,
        "strategy_changed": False,
    }


def report_from_environment() -> dict[str, Any]:
    """Build a report from supervisor-owned environment values."""
    return build_report(
        raw_clock_json=bounded_text(
            os.environ.get("SUPERVISOR_CLOCK_JSON", ""),
            MAX_CLOCK_JSON_CHARS,
        ),
        clock_present=os.environ.get("SUPERVISOR_CLOCK_PRESENT") == "1",
        market_exit_code=parse_exit_code(
            os.environ.get("SUPERVISOR_MARKET_EXIT_CODE", "255")
        ),
        market_stdout=bounded_text(
            os.environ.get("SUPERVISOR_MARKET_STDOUT", ""),
            MAX_MARKET_TEXT_CHARS,
        ),
        market_stderr=bounded_text(
            os.environ.get("SUPERVISOR_MARKET_STDERR", ""),
            MAX_MARKET_TEXT_CHARS,
        ),
    )


def main() -> int:
    """Print normalized clock and market-gate observability JSON."""
    print(json.dumps(report_from_environment(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
