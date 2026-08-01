#!/usr/bin/env python3
"""Append-only BotA pipeline progress and decision ledger.

The ledger answers the operational question that heartbeat messages cannot:
Did updater/watcher work advance, and what terminal outcome did each pair and
timeframe reach? Events carry both UTC display time and CLOCK_BOOTTIME-derived
monotonic time so same-boot freshness is independent of Android wall-clock
changes.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import sys
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

SCHEMA_VERSION = "1.0"


def root_dir() -> Path:
    """Resolve BotA root, allowing temporary roots in tests."""
    configured = os.environ.get("BOTA_ROOT", "").strip()
    return Path(configured).expanduser() if configured else Path(__file__).resolve().parent.parent


def boot_id() -> str:
    """Return the Android/Linux boot identifier when available."""
    try:
        return Path("/proc/sys/kernel/random/boot_id").read_text(encoding="utf-8").strip()
    except OSError:
        return "unknown"


def monotonic_ns() -> int:
    """Return a suspend-aware monotonic timestamp when the platform exposes it."""
    clock = getattr(time, "CLOCK_BOOTTIME", None)
    return time.clock_gettime_ns(clock) if clock is not None else time.monotonic_ns()


def event_time(server_epoch: int | None) -> str:
    """Return trusted server UTC when supplied, otherwise local UTC for display only."""
    if server_epoch and server_epoch > 1_000_000_000:
        return datetime.fromtimestamp(server_epoch, tz=timezone.utc).isoformat()
    return datetime.now(timezone.utc).isoformat()


def state_path() -> Path:
    """Return the compact latest-progress state path."""
    return root_dir() / "state" / "pipeline_progress.json"


def events_path() -> Path:
    """Return the append-only event path."""
    return root_dir() / "logs" / "pipeline_events.jsonl"


def lock_path() -> Path:
    """Return the shared lock path."""
    return root_dir() / "state" / "pipeline_progress.lock"


def empty_state() -> dict[str, Any]:
    """Create a fresh state document."""
    return {
        "schema_version": SCHEMA_VERSION,
        "boot_id": boot_id(),
        "components": {},
        "decisions": {},
        "last_event_id": None,
        "updated_at_utc": None,
    }


def load_state_unlocked(path: Path) -> dict[str, Any]:
    """Load state and reset same-boot progress after reboot."""
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(state, dict):
            raise ValueError("state is not an object")
    except Exception:
        state = empty_state()

    current_boot = boot_id()
    if state.get("boot_id") != current_boot:
        state = empty_state()
    state.setdefault("schema_version", SCHEMA_VERSION)
    state.setdefault("components", {})
    state.setdefault("decisions", {})
    return state


def save_state_unlocked(path: Path, state: dict[str, Any]) -> None:
    """Atomically persist the latest-progress snapshot."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def append_event_unlocked(event: dict[str, Any]) -> None:
    """Append one durable compact event while holding the shared lock."""
    path = events_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, separators=(",", ":"), sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


@contextmanager
def locked_state() -> Iterator[tuple[Path, dict[str, Any]]]:
    """Yield state under an exclusive process-shared lock."""
    lock = lock_path()
    lock.parent.mkdir(parents=True, exist_ok=True)
    with lock.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        path = state_path()
        state = load_state_unlocked(path)
        try:
            yield path, state
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def common_event(args: argparse.Namespace, event_type: str) -> dict[str, Any]:
    """Build common event fields."""
    server_epoch = int(getattr(args, "server_epoch", 0) or 0)
    return {
        "schema_version": SCHEMA_VERSION,
        "event_id": uuid.uuid4().hex,
        "event_type": event_type,
        "boot_id": boot_id(),
        "monotonic_ns": monotonic_ns(),
        "timestamp_utc": event_time(server_epoch),
        "time_source": "server_epoch" if server_epoch > 1_000_000_000 else "local_utc_display_only",
        "server_epoch": server_epoch or None,
        "component": str(getattr(args, "component", "") or "unknown"),
        "status": str(getattr(args, "status", "") or "unknown"),
        "note": str(getattr(args, "note", "") or "")[:1000],
    }


def commit_event(event: dict[str, Any], state_update: callable) -> None:
    """Commit one event and its compact state update atomically under the lock."""
    with locked_state() as (path, state):
        state_update(state)
        state["last_event_id"] = event["event_id"]
        state["updated_at_utc"] = event["timestamp_utc"]
        append_event_unlocked(event)
        save_state_unlocked(path, state)


def command_component(args: argparse.Namespace) -> int:
    """Record component start, progress, completion, degradation, or failure."""
    event = common_event(args, "component")
    event["cycle_id"] = str(args.cycle_id or "")
    event["details"] = str(args.details or "")[:2000]

    def update(state: dict[str, Any]) -> None:
        state.setdefault("components", {})[event["component"]] = event

    commit_event(event, update)
    print(json.dumps(event, sort_keys=True))
    return 0


def command_decision(args: argparse.Namespace) -> int:
    """Record one terminal pair/timeframe decision outcome."""
    event = common_event(args, "decision")
    event.update(
        {
            "cycle_id": str(args.cycle_id or ""),
            "pair": str(args.pair or "").upper(),
            "timeframe": str(args.timeframe or "").upper(),
            "outcome": str(args.outcome or "unknown"),
            "provider": str(args.provider or "unknown").lower(),
            "candle_timestamp_utc": str(args.candle_timestamp or ""),
            "candle_age_seconds": int(args.candle_age) if args.candle_age is not None else None,
            "score": float(args.score) if args.score is not None else None,
            "filter_rejected": str(args.filter_rejected).lower() == "true",
            "rejection_gate": str(args.rejection_gate or "")[:1000],
            "alerts_csv_persisted": str(args.alerts_csv_persisted).lower() == "true",
            "telegram_result": str(args.telegram_result or "not_attempted"),
            "supabase_result": str(args.supabase_result or "not_attempted"),
        }
    )
    key = f"{event['pair']}:{event['timeframe']}"

    def update(state: dict[str, Any]) -> None:
        state.setdefault("decisions", {})[key] = event
        state.setdefault("components", {})[event["component"]] = event

    commit_event(event, update)
    print(json.dumps(event, sort_keys=True))
    return 0


def command_status(args: argparse.Namespace) -> int:
    """Print the current compact progress state."""
    with locked_state() as (path, state):
        save_state_unlocked(path, state)
        output = json.loads(json.dumps(state))
    print(json.dumps(output, indent=2 if args.pretty else None, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    component = sub.add_parser("component")
    component.add_argument("--component", required=True)
    component.add_argument("--status", required=True)
    component.add_argument("--cycle-id", default="")
    component.add_argument("--details", default="")
    component.add_argument("--note", default="")
    component.add_argument("--server-epoch", type=int, default=0)
    component.set_defaults(func=command_component)

    decision = sub.add_parser("decision")
    decision.add_argument("--component", default="watcher")
    decision.add_argument("--status", default="completed")
    decision.add_argument("--cycle-id", default="")
    decision.add_argument("--pair", required=True)
    decision.add_argument("--timeframe", required=True)
    decision.add_argument("--outcome", required=True)
    decision.add_argument("--provider", default="unknown")
    decision.add_argument("--candle-timestamp", default="")
    decision.add_argument("--candle-age", type=int)
    decision.add_argument("--score", type=float)
    decision.add_argument("--filter-rejected", choices=("true", "false"), default="false")
    decision.add_argument("--rejection-gate", default="")
    decision.add_argument("--alerts-csv-persisted", choices=("true", "false"), default="false")
    decision.add_argument("--telegram-result", default="not_attempted")
    decision.add_argument("--supabase-result", default="not_attempted")
    decision.add_argument("--note", default="")
    decision.add_argument("--server-epoch", type=int, default=0)
    decision.set_defaults(func=command_decision)

    status = sub.add_parser("status")
    status.add_argument("--pretty", action="store_true")
    status.set_defaults(func=command_status)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Execute a ledger command."""
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except (OSError, ValueError) as exc:
        print(f"PIPELINE_LEDGER_ERROR={type(exc).__name__}:{exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
