from __future__ import annotations

import json
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from audit.historical_replay_20260601_20260710.src.cycle_replay_orchestrator import (
    RuntimeEpoch,
    build_cycle_replay_report,
)
from audit.historical_replay_20260601_20260710.src.replay_report_persistence import (
    persist_replay_report,
    verify_replay_report,
)

UTC = timezone.utc


def candle(stamp: str, *, available_at: str | None = None):
    row = SimpleNamespace(
        time=datetime.fromisoformat(stamp.replace("Z", "+00:00")),
        complete=True,
        open=1.0,
        high=1.1,
        low=0.9,
        close=1.0,
        volume=1,
    )
    if available_at is not None:
        row.available_at = datetime.fromisoformat(available_at.replace("Z", "+00:00"))
    return row


def report():
    candles = {
        pair: {
            "M15": [candle("2026-06-01T06:45:00Z")],
            "H1": [candle("2026-06-01T06:00:00Z")],
            "H4": [candle("2026-06-01T03:00:00Z")],
            "D1": [candle("2026-05-31T00:00:00Z", available_at="2026-06-01T00:00:00Z")],
        }
        for pair in ("EURUSD", "GBPUSD")
    }
    return build_cycle_replay_report(
        start_utc=datetime(2026, 6, 1, 7, 0, tzinfo=UTC),
        end_utc=datetime(2026, 6, 1, 7, 15, tzinfo=UTC),
        candles_by_pair=candles,
        runtime_epochs=[
            RuntimeEpoch(
                "R1",
                datetime(2026, 6, 1, 0, 0, tzinfo=UTC),
                datetime(2026, 6, 2, 0, 0, tzinfo=UTC),
                True,
                "inferred",
            )
        ],
    )


def test_verify_and_persist_report(tmp_path):
    payload = report()
    verification = verify_replay_report(payload)
    assert verification["status"] == "PASS"
    saved = persist_replay_report(tmp_path, "run-001", payload)
    assert saved["cycle_count"] == 2
    stored = json.loads((tmp_path / saved["path"]).read_text(encoding="utf-8"))
    assert stored == payload
    with pytest.raises(FileExistsError):
        persist_replay_report(tmp_path, "run-001", payload)


def test_detects_report_tampering():
    payload = report()
    payload["rows"][0]["outcome"] = "DELIVERED"
    with pytest.raises(ValueError, match="sha256 mismatch"):
        verify_replay_report(payload)


def test_detects_summary_mismatch():
    payload = report()
    payload["summary"]["PUBLICATION_UNKNOWN"] += 1
    canonical = dict(payload)
    canonical.pop("report_sha256")
    from hashlib import sha256

    payload["report_sha256"] = sha256(
        json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    with pytest.raises(ValueError, match="summary total mismatch"):
        verify_replay_report(payload)
