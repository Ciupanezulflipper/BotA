from datetime import datetime, timezone

import pytest

from audit.historical_replay_20260601_20260710.src.acquisition_dry_run import (
    build_acquisition_plan,
)

UTC = timezone.utc


def test_builds_deterministic_full_scope_plan():
    start = datetime(2026, 6, 1, tzinfo=UTC)
    end = datetime(2026, 7, 11, tzinfo=UTC)
    first = build_acquisition_plan(start_utc=start, end_utc=end)
    second = build_acquisition_plan(start_utc=start, end_utc=end)

    assert first == second
    assert first["mode"] == "dry_run_no_network"
    assert first["instruments"] == ["EUR_USD", "GBP_USD"]
    assert first["granularities"] == ["M15", "H1", "H4", "D"]
    assert first["request_count"] == len(first["requests"])
    assert len(first["plan_sha256"]) == 64
    assert all(row["method"] == "GET" for row in first["requests"])
    assert all("count=" not in row["path_and_query"] for row in first["requests"])
    assert all("from=" in row["path_and_query"] and "to=" in row["path_and_query"] for row in first["requests"])


def test_plan_is_half_open_and_chunk_contiguous():
    plan = build_acquisition_plan(
        start_utc=datetime(2026, 6, 1, tzinfo=UTC),
        end_utc=datetime(2026, 7, 11, tzinfo=UTC),
        instruments=("EUR_USD",),
        granularities=("M15",),
        max_candles=3000,
    )
    rows = plan["requests"]
    assert len(rows) == 2
    assert rows[0]["end_utc"] == rows[1]["start_utc"]
    assert rows[0]["start_utc"] == "2026-06-01T00:00:00Z"
    assert rows[-1]["end_utc"] == "2026-07-11T00:00:00Z"


def test_rejects_bad_scope():
    start = datetime(2026, 6, 1, tzinfo=UTC)
    end = datetime(2026, 6, 2, tzinfo=UTC)
    with pytest.raises(ValueError):
        build_acquisition_plan(start_utc=start, end_utc=end, instruments=("USD_JPY",))
    with pytest.raises(ValueError):
        build_acquisition_plan(start_utc=start, end_utc=end, granularities=("M5",))
