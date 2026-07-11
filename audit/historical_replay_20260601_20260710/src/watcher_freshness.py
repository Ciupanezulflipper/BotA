from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

UTC = timezone.utc


@dataclass(frozen=True)
class FreshnessDecision:
    decision_time_utc: datetime
    latest_candle_start_utc: datetime | None
    age_seconds: int | None
    max_age_seconds: int
    source: str
    status: str
    reason: str

    @property
    def eligible(self) -> bool:
        return self.status == "FRESH"


def _aware_utc(value: datetime, name: str) -> datetime:
    if value.tzinfo is None:
        raise ValueError(f"{name} must be timezone-aware")
    return value.astimezone(UTC)


def production_watcher_freshness(
    *,
    decision_time: datetime,
    candle_starts: Iterable[datetime] | None,
    max_age_seconds: int,
    server_clock_available: bool = True,
    source: str = "chart_timestamp",
) -> FreshnessDecision:
    """Reproduce the production watcher's authoritative raw-cache age gate.

    Production computes age from the trusted server-clock instant minus the last
    candle *start* timestamp in ``cache/<PAIR>_<TF>.json``. It fails closed when
    trusted time or the raw timestamp is unavailable, rejects future timestamps,
    and treats ``age == max_age_seconds`` as fresh because the shell gate is
    strictly ``age > CANDLE_MAX_AGE_SECS``.
    """
    decision = _aware_utc(decision_time, "decision_time")
    if not isinstance(max_age_seconds, int) or max_age_seconds < 0:
        raise ValueError("max_age_seconds must be a non-negative integer")

    if not server_clock_available:
        return FreshnessDecision(
            decision_time_utc=decision,
            latest_candle_start_utc=None,
            age_seconds=None,
            max_age_seconds=max_age_seconds,
            source="server_clock_unavailable",
            status="MISSING",
            reason="trusted server clock unavailable",
        )

    rows = list(candle_starts or [])
    if not rows:
        return FreshnessDecision(
            decision_time_utc=decision,
            latest_candle_start_utc=None,
            age_seconds=None,
            max_age_seconds=max_age_seconds,
            source=source,
            status="MISSING",
            reason="raw cache timestamp missing",
        )

    normalized = [_aware_utc(value, "candle start") for value in rows]
    for previous, current in zip(normalized, normalized[1:]):
        if current <= previous:
            raise ValueError("candle starts must be strictly increasing")

    latest = normalized[-1]
    age = int((decision - latest).total_seconds())
    if age < 0:
        return FreshnessDecision(
            decision_time_utc=decision,
            latest_candle_start_utc=latest,
            age_seconds=None,
            max_age_seconds=max_age_seconds,
            source="future_ts",
            status="MISSING",
            reason="latest candle timestamp is in the future",
        )

    if age > max_age_seconds:
        return FreshnessDecision(
            decision_time_utc=decision,
            latest_candle_start_utc=latest,
            age_seconds=age,
            max_age_seconds=max_age_seconds,
            source=source,
            status="STALE",
            reason="candle age exceeds production ceiling",
        )

    return FreshnessDecision(
        decision_time_utc=decision,
        latest_candle_start_utc=latest,
        age_seconds=age,
        max_age_seconds=max_age_seconds,
        source=source,
        status="FRESH",
        reason="candle age is within production ceiling",
    )
