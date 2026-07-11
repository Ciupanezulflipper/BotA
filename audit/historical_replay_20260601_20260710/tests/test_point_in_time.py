from dataclasses import dataclass
from datetime import datetime, timezone

import pytest

from audit.historical_replay_20260601_20260710.src.point_in_time import (
    build_multitimeframe_view,
    visible_candles,
)

UTC = timezone.utc


@dataclass(frozen=True)
class Row:
    time: datetime
    complete: bool = True
    available_at: datetime | None = None


def dt(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 6, 1, hour, minute, tzinfo=UTC)


def test_m15_candle_is_hidden_until_period_end():
    rows = [Row(dt(10, 0)), Row(dt(10, 15))]
    before = visible_candles(rows, "M15", dt(10, 14))
    boundary = visible_candles(rows, "M15", dt(10, 15))
    assert before.rows == ()
    assert boundary.rows == (rows[0],)


def test_incomplete_candle_never_visible():
    rows = [Row(dt(10, 0), complete=False)]
    assert visible_candles(rows, "M15", dt(11, 0)).rows == ()


def test_future_poison_row_does_not_enter_view():
    safe = Row(dt(10, 0))
    poison = Row(dt(18, 0))
    view = visible_candles([safe, poison], "M15", dt(10, 30))
    assert view.rows == (safe,)


def test_d1_requires_explicit_provider_aligned_availability():
    with pytest.raises(ValueError, match="explicit datetime"):
        visible_candles([Row(dt(0, 0))], "D1", dt(23, 59))


def test_d1_uses_explicit_availability_not_generic_24_hours():
    row = Row(dt(0, 0), available_at=dt(22, 0))
    assert visible_candles([row], "D1", dt(21, 59)).rows == ()
    assert visible_candles([row], "D1", dt(22, 0)).rows == (row,)


def test_multitimeframe_view_requires_exact_scope():
    rows = [Row(dt(8, 0), available_at=dt(22, 0))]
    with pytest.raises(ValueError, match="timeframe set mismatch"):
        build_multitimeframe_view({"M15": rows}, dt(23, 0))


def test_rejects_non_monotonic_input():
    with pytest.raises(ValueError, match="strictly increasing"):
        visible_candles([Row(dt(10, 15)), Row(dt(10, 0))], "M15", dt(11, 0))
