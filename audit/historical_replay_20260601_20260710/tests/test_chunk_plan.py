from datetime import datetime, timezone

import pytest

from audit.historical_replay_20260601_20260710.src.chunk_plan import (
    iso_z,
    plan_chunks,
)


def dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def test_small_window_is_single_half_open_chunk():
    chunks = plan_chunks(
        start_utc=dt("2026-06-01T00:00:00Z"),
        end_utc=dt("2026-06-01T01:00:00Z"),
        granularity="M15",
    )
    assert len(chunks) == 1
    assert iso_z(chunks[0].start_utc) == "2026-06-01T00:00:00Z"
    assert iso_z(chunks[0].end_utc) == "2026-06-01T01:00:00Z"
    assert chunks[0].expected_max_candles == 4


def test_large_window_has_no_overlap_or_gap():
    chunks = plan_chunks(
        start_utc=dt("2026-06-01T00:00:00Z"),
        end_utc=dt("2026-07-11T00:00:00Z"),
        granularity="M15",
        max_candles=5000,
    )
    assert len(chunks) == 2
    assert chunks[0].end_utc == chunks[1].start_utc
    assert chunks[0].expected_max_candles == 5000
    assert chunks[1].end_utc == dt("2026-07-11T00:00:00Z")


def test_rejects_naive_time_and_bad_limits():
    with pytest.raises(ValueError):
        plan_chunks(
            start_utc=datetime(2026, 6, 1),
            end_utc=datetime(2026, 6, 2, tzinfo=timezone.utc),
            granularity="M15",
        )
    with pytest.raises(ValueError):
        plan_chunks(
            start_utc=dt("2026-06-01T00:00:00Z"),
            end_utc=dt("2026-06-02T00:00:00Z"),
            granularity="M15",
            max_candles=5001,
        )


def test_does_not_hardcode_market_open_expectations():
    chunks = plan_chunks(
        start_utc=dt("2026-06-06T00:00:00Z"),
        end_utc=dt("2026-06-07T00:00:00Z"),
        granularity="H1",
    )
    assert chunks[0].expected_max_candles == 24
