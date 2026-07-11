from datetime import datetime, timezone

import pytest

from audit.historical_replay_20260601_20260710.src.cycle_generator import (
    generate_expected_cycles,
    market_gate_open,
)

UTC = timezone.utc


def test_market_gate_boundaries():
    assert market_gate_open(datetime(2026, 6, 1, 7, 0, tzinfo=UTC))
    assert market_gate_open(datetime(2026, 6, 1, 19, 45, tzinfo=UTC))
    assert not market_gate_open(datetime(2026, 6, 1, 6, 45, tzinfo=UTC))
    assert not market_gate_open(datetime(2026, 6, 1, 20, 0, tzinfo=UTC))
    assert not market_gate_open(datetime(2026, 6, 6, 10, 0, tzinfo=UTC))


def test_half_open_cycle_generation_for_two_pairs():
    rows = generate_expected_cycles(
        datetime(2026, 6, 1, 6, 58, tzinfo=UTC),
        datetime(2026, 6, 1, 7, 31, tzinfo=UTC),
    )
    assert [(r.decision_time_utc.minute, r.pair) for r in rows] == [
        (0, "EURUSD"),
        (0, "GBPUSD"),
        (15, "EURUSD"),
        (15, "GBPUSD"),
        (30, "EURUSD"),
        (30, "GBPUSD"),
    ]


def test_rejects_naive_times_and_bad_pairs():
    with pytest.raises(ValueError):
        generate_expected_cycles(datetime(2026, 6, 1), datetime(2026, 6, 2, tzinfo=UTC))
    with pytest.raises(ValueError):
        generate_expected_cycles(
            datetime(2026, 6, 1, tzinfo=UTC),
            datetime(2026, 6, 2, tzinfo=UTC),
            pairs=("USDJPY",),
        )
