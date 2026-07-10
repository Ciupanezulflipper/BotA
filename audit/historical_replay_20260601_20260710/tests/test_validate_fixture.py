import pytest

from audit.historical_replay_20260601_20260710.src.validate_fixture import (
    Candle,
    FixtureValidationError,
    validate_candles,
)


def candle(ts: str, *, complete: bool = True) -> Candle:
    return Candle(
        time_utc=ts,
        complete=complete,
        open=1.1000,
        high=1.1010,
        low=1.0990,
        close=1.1005,
    )


def test_accepts_strictly_ordered_complete_candles() -> None:
    validate_candles([
        candle("2026-06-01T07:00:00Z"),
        candle("2026-06-01T07:15:00Z"),
    ])


def test_rejects_duplicate_timestamp() -> None:
    with pytest.raises(FixtureValidationError):
        validate_candles([
            candle("2026-06-01T07:00:00Z"),
            candle("2026-06-01T07:00:00Z"),
        ])


def test_rejects_incomplete_candle() -> None:
    with pytest.raises(FixtureValidationError):
        validate_candles([candle("2026-06-01T07:00:00Z", complete=False)])
