from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import pytest

from audit.historical_replay_20260601_20260710.src.provider_reconciliation import reconcile_providers


@dataclass(frozen=True)
class Row:
    time: datetime
    open: float
    high: float
    low: float
    close: float


def row(minute: int, close: float = 1.1) -> Row:
    return Row(datetime(2026, 6, 1, 0, minute, tzinfo=timezone.utc), 1.0, 1.2, 0.9, close)


def test_exact_match():
    result = reconcile_providers([row(0), row(15)], [row(0), row(15)])
    assert result.exact_match is True
    assert result.matched_timestamps == 2


def test_reports_missing_and_price_differences():
    result = reconcile_providers(
        [row(0), row(15, close=1.101)],
        [row(0), row(30, close=1.2)],
        price_tolerance=0.0005,
    )
    assert result.matched_timestamps == 1
    assert result.primary_only == ("2026-06-01T00:15:00Z",)
    assert result.independent_only == ("2026-06-01T00:30:00Z",)
    assert result.differences == ()


def test_tolerance_controls_price_differences():
    strict = reconcile_providers([row(0, 1.1000)], [row(0, 1.1002)], price_tolerance=0.0001)
    relaxed = reconcile_providers([row(0, 1.1000)], [row(0, 1.1002)], price_tolerance=0.0003)
    assert len(strict.differences) == 1
    assert relaxed.differences == ()


def test_rejects_duplicate_provider_timestamp():
    with pytest.raises(ValueError, match="duplicate provider timestamp"):
        reconcile_providers([row(0), row(0)], [row(0)])
