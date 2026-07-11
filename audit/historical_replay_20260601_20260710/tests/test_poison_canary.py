from datetime import datetime, timedelta, timezone

import pytest

from audit.historical_replay_20260601_20260710.src.poison_canary import (
    assert_future_independence,
)

UTC = timezone.utc
T0 = datetime(2026, 6, 1, 7, 15, tzinfo=UTC)
ROWS = [
    {"period_end": T0 - timedelta(minutes=15), "close": 1.10},
    {"period_end": T0, "close": 1.11},
    {"period_end": T0 + timedelta(minutes=15), "close": 1.12},
]


def safe_evaluator(rows, decision_time):
    visible = [row for row in rows if row["period_end"] <= decision_time]
    return {"last_close": visible[-1]["close"], "count": len(visible)}


def unsafe_evaluator(rows, _decision_time):
    return {"last_close": rows[-1]["close"], "count": len(rows)}


def test_future_poison_does_not_change_truncated_result():
    baseline, poisoned = assert_future_independence(safe_evaluator, ROWS, T0)
    assert baseline == poisoned


def test_future_poison_detects_leakage():
    with pytest.raises(AssertionError, match="future-row poison"):
        assert_future_independence(unsafe_evaluator, ROWS, T0)
