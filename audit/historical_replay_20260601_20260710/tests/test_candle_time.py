from datetime import datetime, timezone

import pytest

from audit.historical_replay_20260601_20260710.src.candle_time import (
    fixed_period_end,
    is_available,
    parse_utc,
)


def test_parse_utc_normalizes_z_suffix():
    parsed = parse_utc("2026-06-01T12:00:00Z")
    assert parsed == datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc)


def test_incomplete_candle_is_never_available():
    start = parse_utc("2026-06-01T12:00:00Z")
    decision = parse_utc("2026-06-01T12:15:00Z")
    assert not is_available(start, "M15", decision, complete=False)


def test_m15_visible_at_period_end_not_before():
    start = parse_utc("2026-06-01T12:00:00Z")
    before = parse_utc("2026-06-01T12:14:59Z")
    at_end = parse_utc("2026-06-01T12:15:00Z")
    assert not is_available(start, "M15", before, complete=True)
    assert is_available(start, "M15", at_end, complete=True)


def test_h4_fixed_period_end():
    start = parse_utc("2026-06-01T08:00:00Z")
    assert fixed_period_end(start, "H4") == parse_utc("2026-06-01T12:00:00Z")


def test_daily_is_not_treated_as_fixed_24h():
    start = parse_utc("2026-06-01T21:00:00Z")
    with pytest.raises(ValueError):
        fixed_period_end(start, "D")
