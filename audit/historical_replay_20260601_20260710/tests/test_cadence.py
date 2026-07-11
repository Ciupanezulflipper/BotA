from audit.historical_replay_20260601_20260710.src.cadence import (
    validate_fixed_cadence,
)


def test_exact_m15_cadence_passes():
    candles = [
        {"time": "2026-06-01T12:00:00Z"},
        {"time": "2026-06-01T12:15:00Z"},
        {"time": "2026-06-01T12:30:00Z"},
    ]
    result = validate_fixed_cadence(candles, "M15")
    assert result.ok
    assert result.rows == 3


def test_duplicate_timestamp_is_reported():
    candles = [
        {"time": "2026-06-01T12:00:00Z"},
        {"time": "2026-06-01T12:00:00Z"},
    ]
    result = validate_fixed_cadence(candles, "M15")
    assert not result.ok
    assert result.duplicates == ("2026-06-01T12:00:00Z",)


def test_gap_is_reported_without_assuming_market_calendar():
    candles = [
        {"time": "2026-06-01T12:00:00Z"},
        {"time": "2026-06-01T12:30:00Z"},
    ]
    result = validate_fixed_cadence(candles, "M15")
    assert not result.ok
    assert result.gaps == (
        ("2026-06-01T12:00:00Z", "2026-06-01T12:30:00Z", 1800),
    )
