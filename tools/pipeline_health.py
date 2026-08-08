#!/usr/bin/env python3
"""Evaluate BotA useful progress from the monotonic pipeline ledger."""
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any

# Safe production defaults. These are consulted when neither a complete
# PAIRS/TIMEFRAMES environment nor BOTA_REQUIRED_DECISIONS provides a scope.
# They intentionally match the current three-pair production configuration so
# health evaluation cannot silently drop USDJPY.
DEFAULT_PAIRS = ("EURUSD", "GBPUSD", "USDJPY")
DEFAULT_TIMEFRAMES = ("M15",)

TERMINAL_COMPONENT_STATUSES = {"completed", "progress", "skipped_market_closed"}
OPEN_MARKET_FAILURE_OUTCOMES = frozenset(
    {"CLOCK_GATE_FAILED", "INTERNAL_ERROR", "DATA_FETCH_FAILED"}
)


def _split_scope(raw: str) -> tuple[str, ...]:
    """Return the whitespace/comma separated, upper-cased tokens in ``raw``."""
    if not raw:
        return ()
    tokens = [item.strip().upper() for item in raw.replace(",", " ").split()]
    return tuple(token for token in tokens if token)


def required_decisions() -> tuple[str, ...]:
    """Derive the required pair:timeframe scope from configuration.

    Precedence:
        1. ``BOTA_REQUIRED_DECISIONS`` — explicit comma/space list of
           ``PAIR:TIMEFRAME`` entries, used verbatim.
        2. Cartesian product of ``PAIRS`` x ``TIMEFRAMES`` when BOTH are
           present and non-empty.
        3. Cartesian product of ``DEFAULT_PAIRS`` x ``DEFAULT_TIMEFRAMES``.

    Partial or malformed PAIRS/TIMEFRAMES configuration fails closed to the
    full safe production default. Silently filling only the missing dimension
    can narrow or expand health scope in ways that disagree with the watcher.
    The evaluator must never report healthy after checking an accidental
    partial scope.
    """
    explicit = os.environ.get("BOTA_REQUIRED_DECISIONS", "").strip()
    if explicit:
        entries = [item for item in _split_scope(explicit) if ":" in item]
        if entries:
            return tuple(entries)

    pairs = _split_scope(os.environ.get("PAIRS", ""))
    timeframes = _split_scope(os.environ.get("TIMEFRAMES", ""))
    if pairs and timeframes:
        return tuple(
            f"{pair}:{timeframe}" for pair in pairs for timeframe in timeframes
        )
    return tuple(
        f"{pair}:{timeframe}"
        for pair in DEFAULT_PAIRS
        for timeframe in DEFAULT_TIMEFRAMES
    )


# Backward-compatible module attribute used by callers that expect the old
# tuple. It is intentionally re-computed lazily inside evaluate().
REQUIRED_DECISIONS = required_decisions()


def root_dir() -> Path:
    """Resolve BotA root."""
    value = os.environ.get("BOTA_ROOT", "").strip()
    return Path(value).expanduser() if value else Path(__file__).resolve().parent.parent


def boot_id() -> str:
    """Read current boot ID."""
    try:
        return Path("/proc/sys/kernel/random/boot_id").read_text().strip()
    except OSError:
        return "unknown"


def monotonic_ns() -> int:
    """Read suspend-aware monotonic time."""
    clock = getattr(time, "CLOCK_BOOTTIME", None)
    return time.clock_gettime_ns(clock) if clock is not None else time.monotonic_ns()


def load_progress() -> dict[str, Any]:
    """Load compact pipeline progress state."""
    path = root_dir() / "state" / "pipeline_progress.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def event_map(container: dict[str, Any], key: str) -> dict[str, Any]:
    """Return one event object while rejecting non-dictionary JSON values."""
    value = container.get(key)
    if not isinstance(value, dict):
        return {}
    return {str(item_key): item_value for item_key, item_value in value.items()}


def age_seconds(event: dict[str, Any], now_ns: int) -> int | None:
    """Calculate non-negative same-boot event age."""
    try:
        event_ns = int(event["monotonic_ns"])
    except (KeyError, TypeError, ValueError):
        return None
    delta = now_ns - event_ns
    return None if delta < 0 else delta // 1_000_000_000


def component_health(
    name: str,
    event: dict[str, Any],
    now_ns: int,
    maximum: int,
    start_grace: int,
) -> dict[str, Any]:
    """Evaluate a component, allowing only a short explicit in-progress grace."""
    age = age_seconds(event, now_ns)
    status = str(event.get("status") or "missing")
    if status == "started":
        healthy = age is not None and age <= start_grace
        maximum_used = start_grace
        state = "in_progress_grace" if healthy else "stuck_started"
    else:
        healthy = (
            age is not None
            and age <= maximum
            and status in TERMINAL_COMPONENT_STATUSES
        )
        maximum_used = maximum
        state = "terminal_progress" if healthy else "missing_stale_or_failed"
    return {
        "component": name,
        "healthy": healthy,
        "age_seconds": age,
        "max_age_seconds": maximum_used,
        "status": status,
        "evaluation": state,
        "cycle_id": event.get("cycle_id"),
        "event_id": event.get("event_id"),
    }


def _evaluate_components(
    state: dict[str, Any],
    now_ns: int,
    failures: list[str],
) -> dict[str, Any]:
    """Evaluate open-market component freshness and terminal outcomes."""
    thresholds = {
        "updater": int(os.environ.get("MAX_UPDATER_PROGRESS_AGE_SECS", "1500")),
        "watcher": int(os.environ.get("MAX_WATCHER_PROGRESS_AGE_SECS", "1500")),
        "shadow": int(os.environ.get("MAX_SHADOW_PROGRESS_AGE_SECS", "1500")),
    }
    start_grace = int(os.environ.get("MAX_COMPONENT_START_GRACE_SECS", "300"))
    raw_components = state.get("components")
    components: dict[str, Any] = (
        raw_components if isinstance(raw_components, dict) else {}
    )
    results: dict[str, Any] = {}

    for name, maximum in thresholds.items():
        event = event_map(components, name)
        result = component_health(
            name,
            event,
            now_ns,
            maximum,
            start_grace,
        )
        terminal_outcome = str(event.get("terminal_outcome") or "")
        result["terminal_outcome"] = terminal_outcome
        result["market_reason"] = str(event.get("market_reason") or "")
        if name == "watcher" and terminal_outcome in OPEN_MARKET_FAILURE_OUTCOMES:
            result["healthy"] = False
            result["evaluation"] = "open_market_terminal_failure"
            failures.append(
                f"watcher_open_market_terminal_failure:{terminal_outcome}:"
                f"{result.get('market_reason','')}"
            )
        results[name] = result
        if not result["healthy"] and result["evaluation"] != "open_market_terminal_failure":
            failures.append(
                f"{name}_progress_stale_or_failed:"
                f"{result['age_seconds']}:{result['status']}:{result['evaluation']}"
            )

    return results


def _evaluate_decisions(
    state: dict[str, Any],
    now_ns: int,
    failures: list[str],
) -> dict[str, Any]:
    """Evaluate open-market per-pair decision freshness and completion."""
    raw_decisions = state.get("decisions")
    decisions: dict[str, Any] = (
        raw_decisions if isinstance(raw_decisions, dict) else {}
    )
    maximum = int(os.environ.get("MAX_DECISION_AGE_SECS", "1500"))
    results: dict[str, Any] = {}

    for key in required_decisions():
        event = event_map(decisions, key)
        age = age_seconds(event, now_ns)
        outcome = str(event.get("outcome") or "missing")
        status = str(event.get("status") or "missing")
        healthy = (
            age is not None
            and age <= maximum
            and outcome != "missing"
            and status == "completed"
        )
        results[key] = {
            "healthy": healthy,
            "age_seconds": age,
            "max_age_seconds": maximum,
            "outcome": outcome,
            "status": status,
            "event_id": event.get("event_id"),
        }
        if not healthy:
            failures.append(
                f"decision_missing_or_stale:{key}:{age}:{status}:{outcome}"
            )

    return results


def evaluate(market_open: bool) -> dict[str, Any]:
    """Return useful-progress health without filesystem wall-clock mtimes."""
    state = load_progress()
    current_boot = boot_id()
    now_ns = monotonic_ns()
    failures: list[str] = []

    if state.get("boot_id") != current_boot:
        failures.append("pipeline_progress_missing_for_current_boot")

    if market_open:
        component_results = _evaluate_components(state, now_ns, failures)
        decision_results = _evaluate_decisions(state, now_ns, failures)
    else:
        component_results = {
            "market": {
                "healthy": True,
                "status": "closed",
                "note": (
                    "useful-progress freshness gates are suspended while the "
                    "configured market gate is closed"
                ),
            }
        }
        decision_results = {}

    return {
        "schema_version": "1.2",
        "healthy": not failures,
        "market_open": market_open,
        "boot_id": current_boot,
        "monotonic_ns": now_ns,
        "components": component_results,
        "decisions": decision_results,
        "failure_reasons": failures,
    }


def main() -> int:
    """Print health JSON and return nonzero when useful progress is unhealthy."""
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--market-open", action="store_true")
    group.add_argument("--market-closed", action="store_true")
    args = parser.parse_args()
    result = evaluate(market_open=args.market_open)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["healthy"] else 3


if __name__ == "__main__":
    raise SystemExit(main())