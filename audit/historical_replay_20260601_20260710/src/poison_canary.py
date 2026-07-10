from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Callable, Sequence
from datetime import datetime
from typing import Any


def canonical_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def poison_future_rows(
    rows: Sequence[dict[str, Any]],
    decision_time: datetime,
    timestamp_key: str = "period_end",
) -> list[dict[str, Any]]:
    """Deep-copy rows and corrupt only rows whose period end is after decision_time."""
    poisoned = copy.deepcopy(list(rows))
    for row in poisoned:
        ts = row.get(timestamp_key)
        if not isinstance(ts, datetime):
            raise ValueError(f"{timestamp_key} must contain datetime values")
        if ts > decision_time:
            for key in ("open", "high", "low", "close", "volume"):
                if key in row:
                    row[key] = 9_999_999_999.0
            row["__future_poisoned__"] = True
    return poisoned


def assert_future_independence(
    evaluator: Callable[[Sequence[dict[str, Any]], datetime], Any],
    rows: Sequence[dict[str, Any]],
    decision_time: datetime,
) -> tuple[str, str]:
    """Fail when changing future rows changes the decision-time result."""
    baseline = evaluator(rows, decision_time)
    poisoned = evaluator(poison_future_rows(rows, decision_time), decision_time)
    baseline_hash = canonical_hash(baseline)
    poisoned_hash = canonical_hash(poisoned)
    if baseline_hash != poisoned_hash:
        raise AssertionError("future-row poison changed the decision-time result")
    return baseline_hash, poisoned_hash
