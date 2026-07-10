from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


_GRANULARITY_SECONDS = {
    "M15": 15 * 60,
    "H1": 60 * 60,
    "H4": 4 * 60 * 60,
    "D": 24 * 60 * 60,
}


@dataclass(frozen=True)
class Chunk:
    start_utc: datetime
    end_utc: datetime
    expected_max_candles: int


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("timestamps must be timezone-aware")
    return value.astimezone(timezone.utc)


def plan_chunks(
    *,
    start_utc: datetime,
    end_utc: datetime,
    granularity: str,
    max_candles: int = 5000,
) -> list[Chunk]:
    """Create contiguous half-open request windows without boundary overlap.

    The planner uses explicit from/to windows and never mixes them with count.
    Market closures may reduce returned rows, so expected_max_candles is a hard
    upper bound rather than an assertion about provider output volume.
    """
    start = _utc(start_utc)
    end = _utc(end_utc)
    key = str(granularity).upper()
    if key not in _GRANULARITY_SECONDS:
        raise ValueError(f"unsupported granularity: {granularity}")
    if max_candles <= 0 or max_candles > 5000:
        raise ValueError("max_candles must be between 1 and 5000")
    if end <= start:
        raise ValueError("end_utc must be after start_utc")

    step = timedelta(seconds=_GRANULARITY_SECONDS[key] * max_candles)
    chunks: list[Chunk] = []
    cursor = start
    while cursor < end:
        chunk_end = min(cursor + step, end)
        duration = int((chunk_end - cursor).total_seconds())
        expected_max = (duration + _GRANULARITY_SECONDS[key] - 1) // _GRANULARITY_SECONDS[key]
        chunks.append(
            Chunk(
                start_utc=cursor,
                end_utc=chunk_end,
                expected_max_candles=expected_max,
            )
        )
        cursor = chunk_end

    return chunks


def iso_z(value: datetime) -> str:
    return _utc(value).isoformat().replace("+00:00", "Z")
