"""Point-in-time candle timestamp helpers for the isolated audit sidecar."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

_GRANULARITY_SECONDS = {
    "M15": 15 * 60,
    "H1": 60 * 60,
    "H4": 4 * 60 * 60,
}


def parse_utc(value: str) -> datetime:
    """Parse an ISO-8601 timestamp and require timezone awareness."""
    raw = str(value).strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    parsed = datetime.fromisoformat(raw)
    if parsed.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def fixed_period_end(candle_start: datetime, granularity: str) -> datetime:
    """Return period end for fixed-duration granularities only."""
    key = str(granularity).upper()
    if key not in _GRANULARITY_SECONDS:
        raise ValueError(f"unsupported fixed granularity: {granularity}")
    if candle_start.tzinfo is None:
        raise ValueError("candle_start must be timezone-aware")
    return candle_start.astimezone(timezone.utc) + timedelta(
        seconds=_GRANULARITY_SECONDS[key]
    )


def is_available(
    candle_start: datetime,
    granularity: str,
    decision_time: datetime,
    *,
    complete: bool,
) -> bool:
    """A fixed-duration candle is visible only after its period end and if complete."""
    if not complete:
        return False
    if decision_time.tzinfo is None:
        raise ValueError("decision_time must be timezone-aware")
    return fixed_period_end(candle_start, granularity) <= decision_time.astimezone(
        timezone.utc
    )
