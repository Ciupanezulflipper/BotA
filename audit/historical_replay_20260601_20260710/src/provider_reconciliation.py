from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable


@dataclass(frozen=True)
class ProviderDifference:
    time: str
    field: str
    primary: float
    independent: float
    absolute_difference: float


@dataclass(frozen=True)
class ProviderReconciliation:
    matched_timestamps: int
    primary_only: tuple[str, ...]
    independent_only: tuple[str, ...]
    differences: tuple[ProviderDifference, ...]

    @property
    def exact_match(self) -> bool:
        return not self.primary_only and not self.independent_only and not self.differences


def _index(rows: Iterable[object]) -> dict[datetime, object]:
    out: dict[datetime, object] = {}
    for row in rows:
        stamp = getattr(row, "time", None)
        if not isinstance(stamp, datetime) or stamp.tzinfo is None:
            raise ValueError("provider rows require timezone-aware datetime .time")
        if stamp in out:
            raise ValueError("duplicate provider timestamp")
        out[stamp] = row
    return out


def reconcile_providers(
    primary_rows: Iterable[object],
    independent_rows: Iterable[object],
    *,
    price_tolerance: float = 0.0,
) -> ProviderReconciliation:
    if price_tolerance < 0:
        raise ValueError("price_tolerance must be non-negative")

    primary = _index(primary_rows)
    independent = _index(independent_rows)
    primary_times = set(primary)
    independent_times = set(independent)

    def z(stamp: datetime) -> str:
        return stamp.isoformat().replace("+00:00", "Z")

    differences: list[ProviderDifference] = []
    for stamp in sorted(primary_times & independent_times):
        left = primary[stamp]
        right = independent[stamp]
        for field in ("open", "high", "low", "close"):
            a = float(getattr(left, field))
            b = float(getattr(right, field))
            delta = abs(a - b)
            if delta > price_tolerance:
                differences.append(
                    ProviderDifference(z(stamp), field, a, b, delta)
                )

    return ProviderReconciliation(
        matched_timestamps=len(primary_times & independent_times),
        primary_only=tuple(z(value) for value in sorted(primary_times - independent_times)),
        independent_only=tuple(z(value) for value in sorted(independent_times - primary_times)),
        differences=tuple(differences),
    )
