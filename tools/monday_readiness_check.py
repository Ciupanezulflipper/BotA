#!/usr/bin/env python3
"""Monday-readiness verification harness for the gated watcher cycle.

Runs a controlled sequence of fixture-based scenarios against
``tools/watcher_gated_cycle.sh`` in an isolated temporary ``BOTA_ROOT`` and
verifies that each scenario produces exactly one terminal outcome consistent
with the Phase 1 enum:

    MARKET_CLOSED
    CLOCK_GATE_FAILED
    DATA_FETCH_FAILED
    DATA_STALE
    EVALUATED_REJECTED
    EVALUATED_ACCEPTED
    DEDUP_SUPPRESSED_DELIVERY
    DELIVERY_ATTEMPTED
    INTERNAL_ERROR

The harness deliberately does NOT:
  * consult the live market gate,
  * send Telegram messages,
  * write to Supabase,
  * change strategy thresholds, pairs, or timeframes,
  * mutate the caller's real ``BOTA_ROOT`` or any live crontab / runit state,
  * synthesize signals that could leak into production journals.

Every scenario runs the gated cycle with ``WATCHER_GATED_MARKET_HINT`` and
``WATCHER_GATED_DRY_RUN`` set so the inner watcher is not invoked; the
terminal-outcome contract is exercised purely through the ledger surface.

Exit code: 0 when every scenario matches its expected terminal outcome,
non-zero otherwise. Machine-readable summary is printed to stdout.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = REPO_ROOT / "tools"

TOOL_FILES = (
    "pipeline_ledger.py",
    "pipeline_health.py",
    "watcher_gated_cycle.sh",
    "market_open.sh",
    "run_signal_watcher_with_ledger.sh",
    "watcher_cycle_ledger.py",
)


SCENARIOS: tuple[dict[str, Any], ...] = (
    {
        "name": "market_closed_saturday",
        "market_hint": "MARKET_CLOSED_SATURDAY",
        "dry_run": True,
        "expected_terminal": "MARKET_CLOSED",
        "expected_status": "skipped_market_closed",
    },
    {
        "name": "market_closed_sunday",
        "market_hint": "MARKET_CLOSED_SUNDAY",
        "dry_run": True,
        "expected_terminal": "MARKET_CLOSED",
        "expected_status": "skipped_market_closed",
    },
    {
        "name": "market_closed_friday_post_2000",
        "market_hint": "MARKET_CLOSED_FRIDAY_POST_2000",
        "dry_run": True,
        "expected_terminal": "MARKET_CLOSED",
        "expected_status": "skipped_market_closed",
    },
    {
        "name": "market_closed_asian_pre_0700",
        "market_hint": "MARKET_CLOSED_ASIAN_PRE_0700",
        "dry_run": True,
        "expected_terminal": "MARKET_CLOSED",
        "expected_status": "skipped_market_closed",
    },
    {
        "name": "market_closed_post_ny",
        "market_hint": "MARKET_CLOSED_POST_NY",
        "dry_run": True,
        "expected_terminal": "MARKET_CLOSED",
        "expected_status": "skipped_market_closed",
    },
    {
        "name": "clock_unavailable",
        "market_hint": "CLOCK_UNAVAILABLE",
        "dry_run": True,
        "expected_terminal": "CLOCK_GATE_FAILED",
        "expected_status": "failed",
    },
    {
        "name": "market_gate_error",
        "market_hint": "MARKET_GATE_ERROR",
        "dry_run": True,
        "expected_terminal": "CLOCK_GATE_FAILED",
        "expected_status": "failed",
    },
    {
        "name": "open_dry_run_default_rejected",
        "market_hint": "MARKET_OPEN",
        "dry_run": True,
        "expected_terminal": "EVALUATED_REJECTED",
        "expected_status": "completed",
    },
)


def stage_bota_root(tmp: Path) -> Path:
    """Copy the minimum tool set into a temp root and return that root."""
    (tmp / "tools").mkdir(parents=True, exist_ok=True)
    (tmp / "logs").mkdir(parents=True, exist_ok=True)
    (tmp / "state").mkdir(parents=True, exist_ok=True)
    for name in TOOL_FILES:
        source = TOOLS_DIR / name
        if source.exists():
            shutil.copy2(source, tmp / "tools" / name)
    return tmp


def run_scenario(root: Path, scenario: dict[str, Any]) -> dict[str, Any]:
    """Execute one scenario and read the recorded watcher component event."""
    env = os.environ.copy()
    env["BOTA_ROOT"] = str(root)
    env["WATCHER_GATED_MARKET_HINT"] = scenario["market_hint"]
    if scenario.get("dry_run"):
        env["WATCHER_GATED_DRY_RUN"] = "1"
    else:
        env.pop("WATCHER_GATED_DRY_RUN", None)
    env.pop("BOTA_SERVER_EPOCH", None)

    completed = subprocess.run(
        ["bash", str(root / "tools" / "watcher_gated_cycle.sh")],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    state_path = root / "state" / "pipeline_progress.json"
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        state = {}

    watcher = (
        state.get("components", {}).get("watcher")
        if isinstance(state, dict)
        else None
    )
    if not isinstance(watcher, dict):
        watcher = {}

    actual_terminal = str(watcher.get("terminal_outcome") or "")
    actual_status = str(watcher.get("status") or "")
    matches = (
        actual_terminal == scenario["expected_terminal"]
        and actual_status == scenario["expected_status"]
    )

    return {
        "name": scenario["name"],
        "expected_terminal": scenario["expected_terminal"],
        "actual_terminal": actual_terminal,
        "expected_status": scenario["expected_status"],
        "actual_status": actual_status,
        "market_reason": watcher.get("market_reason", ""),
        "cycle_id": watcher.get("cycle_id", ""),
        "exit_code": completed.returncode,
        "matches": matches,
        "stderr_tail": completed.stderr.strip()[-400:],
    }


def main() -> int:
    """Run the full readiness suite and print a machine-readable summary."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--keep-root",
        action="store_true",
        help="Keep the temporary BOTA_ROOT for post-hoc inspection.",
    )
    args = parser.parse_args()

    tmp_root = Path(tempfile.mkdtemp(prefix="monday_readiness_"))
    try:
        stage_bota_root(tmp_root)
        # Wipe compact state between scenarios so cross-scenario contamination
        # cannot mask a bug.
        results = []
        for scenario in SCENARIOS:
            state_path = tmp_root / "state" / "pipeline_progress.json"
            events_path = tmp_root / "logs" / "pipeline_events.jsonl"
            for path in (state_path, events_path):
                try:
                    path.unlink()
                except FileNotFoundError:
                    pass
            results.append(run_scenario(tmp_root, scenario))
    finally:
        if not args.keep_root:
            shutil.rmtree(tmp_root, ignore_errors=True)

    summary = {
        "healthy": all(item["matches"] for item in results),
        "scenarios": results,
        "root_kept": args.keep_root,
        "root": str(tmp_root) if args.keep_root else None,
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["healthy"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
