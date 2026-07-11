from datetime import datetime, timedelta, timezone

import pytest

from audit.historical_replay_20260601_20260710.src.cycle_operability import (
    OperabilityState,
    combine_runtime_and_freshness,
)
from audit.historical_replay_20260601_20260710.src.runtime_epochs import (
    RuntimeEpoch,
    RuntimeState,
    resolve_runtime_state,
)
from audit.historical_replay_20260601_20260710.src.watcher_freshness import (
    production_watcher_freshness,
)

UTC = timezone.utc
CYCLE = datetime(2026, 7, 1, 12, 0, tzinfo=UTC)


def runtime(state: RuntimeState):
    return resolve_runtime_state(
        CYCLE,
        [RuntimeEpoch(CYCLE - timedelta(hours=1), CYCLE + timedelta(hours=1), state, "proof")],
    )


def fresh(at: datetime = CYCLE - timedelta(minutes=15)):
    return production_watcher_freshness(
        decision_time=CYCLE,
        candle_starts=[at],
        max_age_seconds=2700,
    )


def test_up_and_fresh_is_operable():
    result = combine_runtime_and_freshness(runtime(RuntimeState.UP), fresh())
    assert result.state is OperabilityState.OPERABLE
    assert result.scheduled is True
    assert result.usable_data is True
    assert result.claim_status == "proven"


def test_down_takes_precedence_over_fresh_data():
    result = combine_runtime_and_freshness(runtime(RuntimeState.DOWN), fresh())
    assert result.state is OperabilityState.RUNTIME_DOWN
    assert result.scheduled is False
    assert result.usable_data is None


def test_unknown_runtime_never_becomes_operable_from_fresh_data():
    result = combine_runtime_and_freshness(runtime(RuntimeState.UNKNOWN), fresh())
    assert result.state is OperabilityState.UNKNOWN
    assert result.claim_status == "not proven"
    assert result.scheduled is None
    assert result.usable_data is True


def test_up_with_stale_data_is_data_unusable():
    stale = production_watcher_freshness(
        decision_time=CYCLE,
        candle_starts=[CYCLE - timedelta(seconds=2701)],
        max_age_seconds=2700,
    )
    result = combine_runtime_and_freshness(runtime(RuntimeState.UP), stale)
    assert result.state is OperabilityState.DATA_UNUSABLE
    assert result.scheduled is True
    assert result.usable_data is False


def test_up_with_missing_data_is_data_unusable():
    missing = production_watcher_freshness(
        decision_time=CYCLE,
        candle_starts=[],
        max_age_seconds=2700,
    )
    result = combine_runtime_and_freshness(runtime(RuntimeState.UP), missing)
    assert result.state is OperabilityState.DATA_UNUSABLE


def test_mismatched_cycle_instants_are_rejected():
    other = production_watcher_freshness(
        decision_time=CYCLE + timedelta(minutes=15),
        candle_starts=[CYCLE],
        max_age_seconds=2700,
    )
    with pytest.raises(ValueError, match="same cycle instant"):
        combine_runtime_and_freshness(runtime(RuntimeState.UP), other)
