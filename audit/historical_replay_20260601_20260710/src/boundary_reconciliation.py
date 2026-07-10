from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Sequence


@dataclass(frozen=True)
class BoundaryResult:
    merged_count: int
    duplicates_removed: tuple[str, ...]
    overlap_conflicts: tuple[str, ...]
    timestamps: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.overlap_conflicts


def _time_key(row: object) -> datetime:
    value = getattr(row, "time", None)
    if not isinstance(value, datetime):
        raise ValueError("candle row must expose datetime .time")
    if value.tzinfo is None:
        raise ValueError("candle time must be timezone-aware")
    return value


def _signature(row: object) -> tuple:
    return tuple(
        getattr(row, name, None)
        for name in ("complete", "volume", "open", "high", "low", "close")
    )


def reconcile_chunk_boundaries(chunks: Sequence[Iterable[object]]) -> tuple[list[object], BoundaryResult]:
    """Merge ordered chunk responses, tolerating identical boundary duplicates only."""
    merged: list[object] = []
    by_time: dict[datetime, object] = {}
    duplicates: list[str] = []
    conflicts: list[str] = []

    for chunk in chunks:
        previous: datetime | None = None
        for row in chunk:
            current = _time_key(row)
            if previous is not None and current <= previous:
                raise ValueError("timestamps within each chunk must be strictly increasing")
            previous = current

            existing = by_time.get(current)
            stamp = current.isoformat().replace("+00:00", "Z")
            if existing is None:
                by_time[current] = row
                continue
            if _signature(existing) == _signature(row):
                duplicates.append(stamp)
            else:
                conflicts.append(stamp)

    if conflicts:
        result = BoundaryResult(0, tuple(duplicates), tuple(conflicts), tuple())
        return [], result

    for timestamp in sorted(by_time):
        merged.append(by_time[timestamp])
    stamps = tuple(_time_key(row).isoformat().replace("+00:00", "Z") for row in merged)
    return merged, BoundaryResult(len(merged), tuple(duplicates), tuple(), stamps)
