from datetime import datetime, timezone

import json
import pytest

from audit.historical_replay_20260601_20260710.src.canonical_candle import CanonicalCandle
from audit.historical_replay_20260601_20260710.src.reconciliation_evidence import (
    build_reconciliation_evidence,
    write_reconciliation_evidence,
)


def candle(provider: str, price: float, *, instrument="EURUSD", granularity="M15"):
    return CanonicalCandle(
        provider=provider,
        instrument=instrument,
        granularity=granularity,
        time=datetime(2026, 6, 1, tzinfo=timezone.utc),
        open=price,
        high=price + 0.0002,
        low=price - 0.0002,
        close=price + 0.0001,
        volume=10.0,
        complete=True,
    )


def test_builds_deterministic_difference_report():
    report = build_reconciliation_evidence(
        primary_rows=[candle("oanda", 1.1000)],
        independent_rows=[candle("dukascopy", 1.1001)],
        price_tolerance=0.0,
    )
    assert report["matched_timestamps"] == 1
    assert report["exact_match"] is False
    assert {item["field"] for item in report["differences"]} == {"open", "high", "low", "close"}
    assert len(report["evidence_sha256"]) == 64


def test_tolerance_can_accept_small_provider_difference():
    report = build_reconciliation_evidence(
        primary_rows=[candle("oanda", 1.1000)],
        independent_rows=[candle("dukascopy", 1.10001)],
        price_tolerance=0.00002,
    )
    assert report["exact_match"] is True
    assert report["differences"] == []


def test_rejects_mixed_scope_and_writes_once(tmp_path):
    with pytest.raises(ValueError, match="one instrument/granularity"):
        build_reconciliation_evidence(
            primary_rows=[candle("oanda", 1.1)],
            independent_rows=[candle("dukascopy", 1.1, instrument="GBPUSD")],
            price_tolerance=0.0,
        )

    report = build_reconciliation_evidence(
        primary_rows=[candle("oanda", 1.1)],
        independent_rows=[candle("dukascopy", 1.1)],
        price_tolerance=0.0,
    )
    artifact = write_reconciliation_evidence(root=tmp_path, run_id="proof-1", report=report)
    stored = json.loads((tmp_path / artifact["relative_path"]).read_text(encoding="utf-8"))
    assert stored["evidence_sha256"] == report["evidence_sha256"]
    with pytest.raises(FileExistsError):
        write_reconciliation_evidence(root=tmp_path, run_id="proof-1", report=report)
