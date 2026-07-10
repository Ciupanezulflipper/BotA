from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping

from .path_guard import ensure_within_root
from .raw_artifact import write_once


def _canonical_without_hash(report: Mapping[str, Any]) -> bytes:
    payload = dict(report)
    payload.pop("report_sha256", None)
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def verify_replay_report(report: Mapping[str, Any]) -> dict[str, Any]:
    """Verify the self-hash and minimal structural invariants of a replay report."""
    if report.get("schema_version") != 1:
        raise ValueError("unsupported replay report schema_version")
    rows = report.get("rows")
    summary = report.get("summary")
    if not isinstance(rows, list) or not isinstance(summary, dict):
        raise ValueError("replay report rows or summary missing")
    if report.get("cycle_count") != len(rows):
        raise ValueError("replay report cycle_count mismatch")

    cycle_ids: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("replay report row must be an object")
        cycle_id = str(row.get("cycle_id", ""))
        if not cycle_id or cycle_id in cycle_ids:
            raise ValueError("replay report cycle ids must be non-empty and unique")
        cycle_ids.add(cycle_id)

    expected = sha256(_canonical_without_hash(report)).hexdigest()
    if report.get("report_sha256") != expected:
        raise ValueError("replay report sha256 mismatch")
    if sum(int(value) for value in summary.values()) != len(rows):
        raise ValueError("replay report summary total mismatch")

    return {
        "status": "PASS",
        "cycle_count": len(rows),
        "report_sha256": expected,
    }


def persist_replay_report(root: Path, run_id: str, report: Mapping[str, Any]) -> dict[str, Any]:
    """Verify and immutably persist one deterministic replay report."""
    if not run_id or any(ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_." for ch in run_id):
        raise ValueError("invalid run_id")
    root = root.resolve()
    ensure_within_root(root, root)
    verification = verify_replay_report(report)
    encoded = json.dumps(report, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8") + b"\n"
    artifact = write_once(root, f"evidence/{run_id}/cycle-replay-report.json", encoded)
    return {
        **verification,
        "path": artifact.relative_path,
        "artifact_sha256": artifact.sha256,
        "bytes": artifact.bytes,
    }
