from datetime import datetime, timedelta, timezone

import pytest

from audit.historical_replay_20260601_20260710.src.watcher_freshness import (
    production_watcher_freshness,
)

UTC = timezone.utc
BASE = datetime(2026, 7, 10, 12, 0, tzinfo=UTC)


def test_exact_age_ceiling_is_fresh_like_production_shell_gate():
    result = production_watcher_freshness(
        decision_time=BASE,
        candle_starts=[BASE - timedelta(seconds=2700)],
        max_age_seconds=2700,
    )
    assert result.status == "FRESH"
    assert result.eligible is True
    assert result.age_seconds == 2700


def test_one_second_beyond_ceiling_is_stale():
    result = production_watcher_freshness(
        decision_time=BASE,
        candle_starts=[BASE - timedelta(seconds=2701)],
        max_age_seconds=2700,
    )
    assert result.status == "STALE"
    assert result.eligible is False
    assert result.age_seconds == 2701


def test_missing_raw_timestamp_fails_closed():
    result = production_watcher_freshness(
        decision_time=BASE,
        candle_starts=[],
        max_age_seconds=2700,
    )
    assert result.status == "MISSING"
    assert result.eligible is False
    assert result.age_seconds is None


def test_unavailable_trusted_clock_fails_closed():
    result = production_watcher_freshness(
        decision_time=BASE,
        candle_starts=[BASE - timedelta(minutes=15)],
        max_age_seconds=2700,
        server_clock_available=False,
    )
    assert result.status == "MISSING"
    assert result.source == "server_clock_unavailable"


def test_future_timestamp_fails_closed():
    result = production_watcher_freshness(
        decision_time=BASE,
        candle_starts=[BASE + timedelta(seconds=1)],
        max_age_seconds=2700,
    )
    assert result.status == "MISSING"
    assert result.source == "future_ts"
    assert result.age_seconds is None


def test_latest_start_timestamp_is_authoritative_not_candle_close():
    result = production_watcher_freshness(
        decision_time=BASE,
        candle_starts=[BASE - timedelta(hours=1), BASE - timedelta(minutes=15)],
        max_age_seconds=1200,
    )
    assert result.status == "FRESH"
    assert result.age_seconds == 900
    assert result.latest_candle_start_utc == BASE - timedelta(minutes=15)


def test_rejects_non_monotonic_candle_starts():
    with pytest.raises(ValueError, match="strictly increasing"):
        production_watcher_freshness(
            decision_time=BASE,
            candle_starts=[BASE - timedelta(minutes=15), BASE - timedelta(minutes=30)],
            max_age_seconds=2700,
        )


def test_requires_timezone_aware_inputs():
    with pytest.raises(ValueError, match="timezone-aware"):
        production_watcher_freshness(
            decision_time=datetime(2026, 7, 10, 12, 0),
            candle_starts=[BASE],
            max_age_seconds=2700,
        )
