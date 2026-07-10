from datetime import datetime, timezone

from audit.historical_replay_20260601_20260710.src.boundary_reconciliation import (
    reconcile_chunk_boundaries,
)
from audit.historical_replay_20260601_20260710.src.oanda_payload import ParsedCandle


def candle(minute: int, close: float = 1.1) -> ParsedCandle:
    return ParsedCandle(
        time=datetime(2026, 6, 1, 0, minute, tzinfo=timezone.utc),
        complete=True,
        volume=10,
        open=1.0,
        high=1.2,
        low=0.9,
        close=close,
    )


def test_identical_boundary_duplicate_is_removed():
    merged, result = reconcile_chunk_boundaries(
        [[candle(0), candle(15)], [candle(15), candle(30)]]
    )
    assert result.ok
    assert result.merged_count == 3
    assert result.duplicates_removed == ("2026-06-01T00:15:00Z",)
    assert len(merged) == 3


def test_conflicting_boundary_duplicate_fails_closed():
    merged, result = reconcile_chunk_boundaries(
        [[candle(0), candle(15)], [candle(15, close=1.3), candle(30)]]
    )
    assert not result.ok
    assert result.overlap_conflicts == ("2026-06-01T00:15:00Z",)
    assert merged == []


def test_unsorted_chunk_is_rejected():
    import pytest

    with pytest.raises(ValueError):
        reconcile_chunk_boundaries([[candle(15), candle(0)]])
