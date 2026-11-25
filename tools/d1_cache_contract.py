"""Shared fail-closed D1 cache contract for scoring and health."""
from __future__ import annotations

import json
from pathlib import Path

PAIRS = ("EURUSD", "GBPUSD", "USDJPY")


def read_d1_trend(root: Path, pair: str) -> tuple[str, str | None]:
    """Return a usable direction or a sanitized reason (never cache contents)."""
    pair = pair.upper()
    if pair not in PAIRS:
        return "UNAVAILABLE", "unsupported_pair"
    path = Path(root) / "cache" / f"d1_trend_{pair}.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return "UNAVAILABLE", "missing"
    except (OSError, UnicodeError, ValueError):
        return "UNAVAILABLE", "unreadable_or_invalid"
    if not isinstance(data, dict):
        return "UNAVAILABLE", "invalid"
    if data.get("pair", pair) != pair or data.get("error") or data.get("weak") is True:
        return "UNAVAILABLE", "invalid"
    trend = data.get("trend")
    if trend not in ("BUY", "SELL"):
        return "UNAVAILABLE", "invalid_trend"
    return trend, None
