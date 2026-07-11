from datetime import datetime, timezone

import pytest

from audit.historical_replay_20260601_20260710.src.runtime_epochs import (
    RuntimeEpoch,
    RuntimeState,
    resolve_runtime_state,
    validate_runtime_epochs,
)

UTC = timezone.utc


def dt(day: int, hour: int = 0, minute: int = 0) -> datetime:
    return datetime(2026, 7, day, hour, minute, tzinfo=UTC)


def test_half_open_runtime_epoch_boundaries():
    epoch = RuntimeEpoch(dt(1), dt(2), RuntimeState.UP, "log-proof-1")
    assert resolve_runtime_state(dt(1), [epoch]).state is RuntimeState.UP
    at_end = resolve_runtime_state(dt(2), [epoch])
    assert at_end.state is RuntimeState.UNKNOWN
    assert at_end.claim_status == "not proven"


def test_down_epoch_proves_not_scheduled():
    result = resolve_runtime_state(
        dt(3, 12),
        [RuntimeEpoch(dt(3), dt(4), RuntimeState.DOWN, "cron-outage-proof")],
    )
    assert result.state is RuntimeState.DOWN
    assert result.watcher_scheduled is False
    assert result.claim_status == "proven"


def test_up_epoch_proves_watcher_available():
    result = resolve_runtime_state(
        dt(4, 12),
        [RuntimeEpoch(dt(4), dt(5), RuntimeState.UP, "watcher-log-proof")],
    )
    assert result.watcher_scheduled is True
    assert result.claim_status == "proven"


def test_explicit_unknown_epoch_remains_not_proven():
    result = resolve_runtime_state(
        dt(5, 12),
        [RuntimeEpoch(dt(5), dt(6), RuntimeState.UNKNOWN, "evidence-gap")],
    )
    assert result.state is RuntimeState.UNKNOWN
    assert result.watcher_scheduled is None
    assert result.claim_status == "not proven"


def test_no_epoch_never_defaults_to_up_or_down():
    result = resolve_runtime_state(dt(7), [])
    assert result.state is RuntimeState.UNKNOWN
    assert result.evidence_id is None
    assert result.claim_status == "not proven"


def test_overlapping_epochs_are_rejected():
    rows = [
        RuntimeEpoch(dt(1), dt(3), RuntimeState.UP, "a"),
        RuntimeEpoch(dt(2), dt(4), RuntimeState.DOWN, "b"),
    ]
    with pytest.raises(ValueError, match="must not overlap"):
        validate_runtime_epochs(rows)


def test_unsorted_epochs_that_overlap_are_rejected():
    rows = [
        RuntimeEpoch(dt(3), dt(4), RuntimeState.UP, "a"),
        RuntimeEpoch(dt(1), dt(2), RuntimeState.DOWN, "b"),
    ]
    with pytest.raises(ValueError, match="must not overlap"):
        validate_runtime_epochs(rows)


def test_invalid_or_naive_epochs_fail_closed():
    with pytest.raises(ValueError, match="timezone-aware"):
        RuntimeEpoch(
            datetime(2026, 7, 1),
            dt(2),
            RuntimeState.UP,
            "bad",
        )
    with pytest.raises(ValueError, match="start_utc < end_utc"):
        RuntimeEpoch(dt(2), dt(2), RuntimeState.UP, "bad")
    with pytest.raises(ValueError, match="evidence_id"):
        RuntimeEpoch(dt(1), dt(2), RuntimeState.UP, " ")
