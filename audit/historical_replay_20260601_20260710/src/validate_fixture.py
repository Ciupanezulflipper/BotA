from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


class FixtureValidationError(ValueError):
    pass


@dataclass(frozen=True)
class Candle:
    time_utc: str
    complete: bool
    open: float
    high: float
    low: float
    close: float


def _parse_utc(value: str) -> datetime:
    if not value.endswith("Z"):
        raise FixtureValidationError(f"non-UTC timestamp: {value}")
    return datetime.fromisoformat(value[:-1] + "+00:00")


def validate_candles(candles: list[Candle]) -> None:
    if not candles:
        raise FixtureValidationError("empty candle fixture")

    seen: set[str] = set()
    previous: datetime | None = None
    for candle in candles:
        timestamp = _parse_utc(candle.time_utc)
        if candle.time_utc in seen:
            raise FixtureValidationError(f"duplicate timestamp: {candle.time_utc}")
        seen.add(candle.time_utc)

        if previous is not None and timestamp <= previous:
            raise FixtureValidationError("timestamps are not strictly increasing")
        previous = timestamp

        if not candle.complete:
            raise FixtureValidationError(f"incomplete candle rejected: {candle.time_utc}")
        if min(candle.open, candle.high, candle.low, candle.close) <= 0:
            raise FixtureValidationError(f"non-positive OHLC: {candle.time_utc}")
        if candle.high < max(candle.open, candle.close, candle.low):
            raise FixtureValidationError(f"invalid high: {candle.time_utc}")
        if candle.low > min(candle.open, candle.close, candle.high):
            raise FixtureValidationError(f"invalid low: {candle.time_utc}")
