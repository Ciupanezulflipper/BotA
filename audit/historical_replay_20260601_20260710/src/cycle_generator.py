from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable

UTC = timezone.utc


@dataclass(frozen=True)
class ExpectedCycle:
    decision_time_utc: datetime
    pair: str
    timeframe: str = "M15"


def _require_aware_utc(value: datetime, name: str) -> datetime:
    if value.tzinfo is None:
        raise ValueError(f"{name} must be timezone-aware")
    return value.astimezone(UTC)


def market_gate_open(decision_time_utc: datetime) -> bool:
    """Match committed BotA gate: Monday-Friday, 07:00 <= UTC < 20:00."""
    dt = _require_aware_utc(decision_time_utc, "decision_time_utc")
    if dt.weekday() >= 5:
        return False
    minute_of_day = dt.hour * 60 + dt.minute
    return 7 * 60 <= minute_of_day < 20 * 60


def _ceil_to_quarter_hour(value: datetime) -> datetime:
    dt = _require_aware_utc(value, "value")
    dt = dt.replace(second=0, microsecond=0)
    remainder = dt.minute % 15
    if remainder == 0:
        return dt
    return dt + timedelta(minutes=15 - remainder)


def generate_expected_cycles(
    start_utc: datetime,
    end_utc: datetime,
    pairs: Iterable[str] = ("EURUSD", "GBPUSD"),
) -> list[ExpectedCycle]:
    """Generate half-open [start,end) expected watcher cycles after market gating."""
    start = _require_aware_utc(start_utc, "start_utc")
    end = _require_aware_utc(end_utc, "end_utc")
    if end <= start:
        raise ValueError("end_utc must be after start_utc")

    normalized_pairs = tuple(str(pair).strip().upper() for pair in pairs)
    if not normalized_pairs or any(pair not in {"EURUSD", "GBPUSD"} for pair in normalized_pairs):
        raise ValueError("pairs must be a non-empty subset of EURUSD and GBPUSD")

    result: list[ExpectedCycle] = []
    current = _ceil_to_quarter_hour(start)
    while current < end:
        if market_gate_open(current):
            result.extend(ExpectedCycle(current, pair) for pair in normalized_pairs)
        current += timedelta(minutes=15)
    return result
