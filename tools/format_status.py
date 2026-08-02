#!/usr/bin/env python3
"""Render cache-only technical trend context for BotA status messages.

This module performs no network calls and does not create executable trade
signals. Invalid or missing cache data is shown explicitly and excluded from the
technical context score.
"""

from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_ROOT = Path(__file__).resolve().parents[1]
ROOT = Path(os.environ.get("BOTA_ROOT", str(DEFAULT_ROOT))).expanduser()
CACHE_DIR = ROOT / "cache"

PAIRS = (("EURUSD", "EUR/USD"), ("GBPUSD", "GBP/USD"))
TIMEFRAMES = ("H1", "H4", "D1")

STRONG_BUY = "STRONG BUY"
BUY = "BUY"
HOLD = "HOLD"
SELL = "SELL"
STRONG_SELL = "STRONG SELL"

STATUS_TITLE = "BotA Technical Trend Context"
DISCLAIMER = "Cached indicators only — not a trade entry."


@dataclass(frozen=True)
class IndicatorMetrics:
    """Validated numeric values required for one timeframe summary."""

    price: float
    ema9: float
    ema21: float
    rsi: float
    macd_hist: float


def finite_float(value: Any) -> float | None:
    """Convert a value to a finite float, or return ``None``."""
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if not math.isfinite(number):
        return None
    return number


def load_bundle(pair: str, timeframe: str) -> dict[str, Any] | None:
    """Read one canonical indicator cache file."""
    path = CACHE_DIR / f"indicators_{pair}_{timeframe}.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    return data


def validate_bundle(
    bundle: dict[str, Any] | None,
    pair: str,
    timeframe: str,
) -> tuple[str, IndicatorMetrics | None]:
    """Validate cache identity, state, and numeric indicator values."""
    if bundle is None:
        return "missing cache", None
    if str(bundle.get("pair", "")).upper() != pair:
        return "pair mismatch", None
    if str(bundle.get("timeframe", "")).upper() != timeframe:
        return "timeframe mismatch", None
    if bundle.get("tf_ok") is not True:
        return str(bundle.get("error") or "invalid timeframe"), None
    if bundle.get("weak") is not False:
        return str(bundle.get("error") or "weak data"), None

    recorded_error = str(bundle.get("error") or "").strip()
    if recorded_error:
        return recorded_error, None

    price = finite_float(bundle.get("price"))
    ema9 = finite_float(bundle.get("ema9"))
    ema21 = finite_float(bundle.get("ema21"))
    rsi = finite_float(bundle.get("rsi"))
    macd_hist = finite_float(bundle.get("macd_hist"))
    if (
        price is None
        or ema9 is None
        or ema21 is None
        or rsi is None
        or macd_hist is None
    ):
        return "invalid indicators", None

    return "", IndicatorMetrics(
        price=price,
        ema9=ema9,
        ema21=ema21,
        rsi=rsi,
        macd_hist=macd_hist,
    )


def timeframe_score(metrics: IndicatorMetrics) -> int:
    """Calculate the existing three-factor technical display score."""
    score = 0
    if metrics.ema9 > metrics.ema21:
        score += 1
    elif metrics.ema9 < metrics.ema21:
        score -= 1

    if metrics.rsi > 55.0:
        score += 1
    elif metrics.rsi < 45.0:
        score -= 1

    if metrics.macd_hist > 0.0:
        score += 1
    elif metrics.macd_hist < 0.0:
        score -= 1
    return score


def timeframe_label(score: int) -> str:
    """Map one timeframe score to user-facing trend language."""
    if score >= 3:
        return STRONG_BUY
    if score >= 2:
        return BUY
    if score <= -3:
        return STRONG_SELL
    if score <= -2:
        return SELL
    return HOLD


def overall_label(total_score: int, valid_timeframes: int) -> str:
    """Map multi-timeframe context to a label with minimum coverage."""
    if valid_timeframes < 2:
        return HOLD
    if total_score >= 5:
        return STRONG_BUY
    if total_score >= 2:
        return BUY
    if total_score <= -5:
        return STRONG_SELL
    if total_score <= -2:
        return SELL
    return HOLD


def macd_direction(value: float) -> str:
    """Render MACD histogram direction."""
    if value > 0.0:
        return "rising"
    if value < 0.0:
        return "falling"
    return "flat"


def render_pair(pair: str, display_name: str) -> list[str]:
    """Render one pair from validated H1, H4, and D1 caches."""
    lines = [f"━━━ {display_name} ━━━"]
    scores: list[int] = []
    first_price: float | None = None

    for timeframe in TIMEFRAMES:
        bundle = load_bundle(pair, timeframe)
        reason, metrics = validate_bundle(bundle, pair, timeframe)
        if metrics is None:
            lines.append(f"{timeframe}: unavailable ({reason})")
            continue

        if first_price is None:
            first_price = metrics.price
        score = timeframe_score(metrics)
        scores.append(score)
        lines.append(
            f"{timeframe}: {timeframe_label(score)} | "
            f"RSI {metrics.rsi:.1f} | MACD {macd_direction(metrics.macd_hist)}"
        )

    price_text = "unavailable" if first_price is None else f"{first_price:.5f}"
    lines.insert(1, f"Price: {price_text}")
    lines.append(f"Overall trend: {overall_label(sum(scores), len(scores))}")
    lines.append(f"Coverage: {len(scores)} of {len(TIMEFRAMES)} timeframes")
    return lines


def build_status() -> str:
    """Build the complete cache-only status message."""
    lines = [STATUS_TITLE, DISCLAIMER, ""]
    for index, (pair, display_name) in enumerate(PAIRS):
        if index > 0:
            lines.append("")
        lines.extend(render_pair(pair, display_name))
    return "\n".join(lines)


def main() -> None:
    """Print the cache-only technical context."""
    print(build_status())


if __name__ == "__main__":
    main()
