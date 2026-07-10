"""Cadence validation for fixed-duration synthetic candle fixtures."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Mapping, Any

from .candle_time import parse_utc

_EXPECTED_SECONDS = {
    "M15": 15 * 60,
    "H1": 60 * 60,
    "H4": 4 * 60 * 60,
}


@dataclass(frozen=True)
class CadenceResult:
    rows: int
    duplicates: tuple[str, ...]
    gaps: tuple[tuple[str, str, int], ...]

    @property
    def ok(self) -> bool:
        return not self.duplicates and not self.gaps


def validate_fixed_cadence(
    candles: Iterable[Mapping[str, Any]], granularity: str
) -> CadenceResult:
    """Validate strictly increasing timestamps and exact fixed-duration spacing.

    This validator intentionally does not infer market-closure exceptions. Those
    belong in a later expected-market-grid layer, not in the raw fixture parser.
    """
    key = str(granularity).upper()
    if key not in _EXPECTED_SECONDS:
        raise ValueError(f"unsupported fixed granularity: {granularity}")

    parsed: list[tuple[str, datetime]] = []
    for row in candles:
        raw = str(row.get("time", "")).strip()
        if not raw:
            raise ValueError("candle missing time")
        parsed.append((raw, parse_utc(raw)))

    duplicates: list[str] = []
    gaps: list[tuple[str, str, int]] = []
    expected = _EXPECTED_SECONDS[key]

    for index in range(1, len(parsed)):
        previous_raw, previous = parsed[index - 1]
        current_raw, current = parsed[index]
        delta = int((current - previous).total_seconds())
        if delta == 0:
            duplicates.append(current_raw)
        elif delta != expected:
            gaps.append((previous_raw, current_raw, delta))

    return CadenceResult(
        rows=len(parsed),
        duplicates=tuple(duplicates),
        gaps=tuple(gaps),
    )
