from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from audit.historical_replay_20260601_20260710.src.cycle_replay_orchestrator import (
    ReplayEvidence,
    RuntimeEpoch,
    build_cycle_replay_report,
)

UTC = timezone.utc


def dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def candle(time: str, *, available_at: str | None = None):
    values = {
        "time": dt(time),
        "complete": True,
        "open": 1.1,
        "high": 1.2,
        "low": 1.0,
        "close": 1.15,
        "volume": 10,
    }
    if available_at is not None:
        values["available_at"] = dt(available_at)
    return SimpleNamespace(**values)


def candles():
    return {
        "EURUSD": {
            "M15": [candle("2026-06-01T06:45:00Z")],
            "H1": [candle("2026-06-01T06:00:00Z")],
            "H4": [candle("2026-06-01T03:00:00Z")],
            "D1": [
                candle(
                    "2026-05-31T00:00:00Z",
                    available_at="2026-06-01T00:00:00Z",
                )
            ],
        }
    }


def epoch(*, scheduled: bool = True):
    return RuntimeEpoch(
        "R1",
        dt("2026-06-01T00:00:00Z"),
        dt("2026-06-02T00:00:00Z"),
        scheduled,
        "inferred",
    )


def cycle_id() -> str:
    return "2026-06-01T07:00:00Z|EURUSD|M15"


def test_rejected_cycle_report_is_deterministic():
    kwargs = dict(
        start_utc=dt("2026-06-01T07:00:00Z"),
        end_utc=dt("2026-06-01T07:15:00Z"),
        candles_by_pair=candles(),
        runtime_epochs=[epoch()],
        evidence_by_cycle={
            cycle_id(): ReplayEvidence(True, False, False, False),
        },
        pairs=("EURUSD",),
    )
    first = build_cycle_replay_report(**kwargs)
    second = build_cycle_replay_report(**kwargs)

    assert first == second
    assert first["cycle_count"] == 1
    assert first["rows"][0]["outcome"] == "EVALUATED_REJECTED"
    assert first["rows"][0]["visible_counts"] == {
        "M15": 1,
        "H1": 1,
        "H4": 1,
        "D1": 1,
    }
    assert len(first["report_sha256"]) == 64


def test_missing_decision_evidence_is_not_a_rejection():
    report = build_cycle_replay_report(
        start_utc=dt("2026-06-01T07:00:00Z"),
        end_utc=dt("2026-06-01T07:15:00Z"),
        candles_by_pair=candles(),
        runtime_epochs=[epoch()],
        pairs=("EURUSD",),
    )
    assert report["rows"][0]["outcome"] == "PUBLICATION_UNKNOWN"
    assert report["rows"][0]["claim_status"] == "not proven"


def test_unscheduled_runtime_epoch_wins_over_available_data():
    report = build_cycle_replay_report(
        start_utc=dt("2026-06-01T07:00:00Z"),
        end_utc=dt("2026-06-01T07:15:00Z"),
        candles_by_pair=candles(),
        runtime_epochs=[epoch(scheduled=False)],
        evidence_by_cycle={cycle_id(): ReplayEvidence(True, True, True, True)},
        pairs=("EURUSD",),
    )
    assert report["rows"][0]["outcome"] == "NOT_SCHEDULED"


def test_every_cycle_requires_exactly_one_runtime_epoch():
    with pytest.raises(ValueError, match="exactly one runtime epoch"):
        build_cycle_replay_report(
            start_utc=dt("2026-06-01T07:00:00Z"),
            end_utc=dt("2026-06-01T07:15:00Z"),
            candles_by_pair=candles(),
            runtime_epochs=[],
            pairs=("EURUSD",),
        )


def test_overlapping_runtime_epochs_are_rejected():
    with pytest.raises(ValueError, match="must not overlap"):
        build_cycle_replay_report(
            start_utc=dt("2026-06-01T07:00:00Z"),
            end_utc=dt("2026-06-01T07:15:00Z"),
            candles_by_pair=candles(),
            runtime_epochs=[
                epoch(),
                RuntimeEpoch(
                    "R2",
                    dt("2026-06-01T12:00:00Z"),
                    dt("2026-06-02T12:00:00Z"),
                    True,
                    "suspected",
                ),
            ],
            pairs=("EURUSD",),
        )
