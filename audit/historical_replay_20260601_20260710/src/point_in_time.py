from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, Mapping

from .candle_time import fixed_period_end

UTC = timezone.utc
_FIXED = {"M15", "H1", "H4"}
_SUPPORTED = _FIXED | {"D1"}


@dataclass(frozen=True)
class VisibleCandleSet:
    decision_time_utc: datetime
    granularity: str
    rows: tuple[object, ...]
    latest_available_at_utc: datetime | None


def _aware_utc(value: datetime, name: str) -> datetime:
    if value.tzinfo is None:
        raise ValueError(f"{name} must be timezone-aware")
    return value.astimezone(UTC)


def candle_available_at(row: object, granularity: str) -> datetime | None:
    """Return the earliest decision time at which a completed candle may be used.

    Fixed-duration candles use their period end. D1 deliberately requires an
    explicit provider-aligned ``available_at`` field because a generic 24-hour
    assumption would not prove production-compatible daily alignment.
    """
    key = str(granularity).upper()
    if key not in _SUPPORTED:
        raise ValueError(f"unsupported granularity: {granularity}")
    if not bool(getattr(row, "complete", False)):
        return None

    start = getattr(row, "time", None)
    if not isinstance(start, datetime):
        raise ValueError("candle row must expose datetime .time")
    start = _aware_utc(start, "candle time")

    if key in _FIXED:
        return fixed_period_end(start, key)

    explicit = getattr(row, "available_at", None)
    if not isinstance(explicit, datetime):
        raise ValueError("D1 candle requires explicit datetime .available_at")
    explicit = _aware_utc(explicit, "available_at")
    if explicit <= start:
        raise ValueError("available_at must be after candle start")
    return explicit


def visible_candles(
    rows: Iterable[object], granularity: str, decision_time: datetime
) -> VisibleCandleSet:
    """Build an immutable point-in-time view containing no future candles."""
    decision = _aware_utc(decision_time, "decision_time")
    visible: list[tuple[datetime, object]] = []
    previous_start: datetime | None = None

    for row in rows:
        start = getattr(row, "time", None)
        if not isinstance(start, datetime):
            raise ValueError("candle row must expose datetime .time")
        start = _aware_utc(start, "candle time")
        if previous_start is not None and start <= previous_start:
            raise ValueError("input candles must be strictly increasing")
        previous_start = start

        available_at = candle_available_at(row, granularity)
        if available_at is not None and available_at <= decision:
            visible.append((available_at, row))

    latest = visible[-1][0] if visible else None
    return VisibleCandleSet(
        decision_time_utc=decision,
        granularity=str(granularity).upper(),
        rows=tuple(row for _, row in visible),
        latest_available_at_utc=latest,
    )


def build_multitimeframe_view(
    candles_by_timeframe: Mapping[str, Iterable[object]], decision_time: datetime
) -> dict[str, VisibleCandleSet]:
    required = {"M15", "H1", "H4", "D1"}
    normalized = {str(key).upper(): value for key, value in candles_by_timeframe.items()}
    missing = required - set(normalized)
    extra = set(normalized) - required
    if missing or extra:
        raise ValueError(f"timeframe set mismatch: missing={sorted(missing)} extra={sorted(extra)}")
    return {
        timeframe: visible_candles(normalized[timeframe], timeframe, decision_time)
        for timeframe in ("M15", "H1", "H4", "D1")
    }
