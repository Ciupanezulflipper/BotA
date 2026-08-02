#!/usr/bin/env python3
"""Render BotA's user-facing technical trend context from local indicator caches.

This formatter performs no network requests. It intentionally separates cached
technical context from executable BotA trade signals.
"""

from __future__ import annotations

import json
import math
import os
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


def safe_float(value: Any) -> float | None:
    """Return a finite float or ``None`` for invalid input."""
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if math.isfinite(number) else None


def number_or_default(value: Any, default: float) -> float:
    """Return a finite number without replacing valid zero values."""
    number = safe_float(value)
    return default if number is None else number


def load_bundle(pair: str, timeframe: str) -> dict[str, Any] | None:
    """Load one indicator bundle from the canonical cache path."""
    path = CACHE_DIR / f"indicators_{pair}_{timeframe}.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def bundle_error(bundle: dict[str, Any] | None, pair: str, timeframe: str) -> str:
    """Return an explicit fail-closed reason for an unusable bundle."""
    if bundle is None:
        return "missing cache"
    if str(bundle.get("pair", "")).upper() != pair:
        return "pair mismatch"
    if str(bundle.get("timeframe", "")).upper() != timeframe:
        return "timeframe mismatch"
    if bundle.get("tf_ok") is not True:
        return str(bundle.get("error") or "invalid timeframe")
    if bundle.get("weak") is not False:
        return str(bundle.get("error") or "weak data")
    if str(bundle.get("error") or "").strip():
        return str(bundle["error"])
    required = ("price", "ema9", "ema21", "rsi", "macd_hist")
    if any(safe_float(bundle.get(key)) is None for key in required):
        return "invalid indicators"
    return ""


def timeframe_score(bundle: dict[str, Any]) -> int:
    """Compute the existing three-factor technical score for display only."""
    ema9 = number_or_default(bundle.get("ema9"), 0.0)
    ema21 = number_or_default(bundle.get("ema21"), 0.0)
    rsi = number_or_default(bundle.get("rsi"), 50.0)
    macd_hist = number_or_default(bundle.get("macd_hist"), 0.0)

    score = 0
    score += 1 if ema9 > ema21 else -1 if ema9 < ema21 else 0
    score += 1 if rsi > 55.0 else -1 if rsi < 45.0 else 0
    score += 1 if macd_hist > 0.0 else -1 if macd_hist < 0.0 else 0
    return score


def timeframe_label(score: int) -> str:
    """Map one timeframe's score to plain user-facing trend language."""
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
    """Map multi-timeframe context to a label, requiring useful coverage."""
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


def macd_direction(value: Any) -> str:
    """Render MACD histogram direction without exposing raw internal scoring."""
    number = safe_float(value)
    if number is None or number == 0.0:
        return "flat"
    return "rising" if number > 0.0 else "falling"


def format_price(value: Any) -> str:
    """Format a cached price while retaining fail-closed output."""
    number = safe_float(value)
    if number is None:
        return "unavailable"
    return f"{number:.5f}"


def render_pair(pair: str, label: str) -> list[str]:
    """Render one pair from valid cached indicator bundles."""
    lines = [f"━━━ {label} ━━━"]
    bundles: dict[str, dict[str, Any]] = {}
    scores: list[int] = []

    for timeframe in TIMEFRAMES:
        bundle = load_bundle(pair, timeframe)
        reason = bundle_error(bundle, pair, timeframe)
        if reason or bundle is None:
            lines.append(f"{timeframe}: unavailable ({reason or 'missing cache'})")
            continue

        bundles[timeframe] = bundle
        score = timeframe_score(bundle)
        scores.append(score)
        rsi = number_or_default(bundle.get("rsi"), 50.0)
        lines.append(
            f"{timeframe}: {timeframe_label(score)} | "
            f"RSI {rsi:.1f} | MACD {macd_direction(bundle.get('macd_hist'))}"
        )

    price_bundle = next(
        (bundles[timeframe] for timeframe in TIMEFRAMES if timeframe in bundles),
        None,
    )
    if price_bundle is not None:
        lines.insert(1, f"Price: {format_price(price_bundle.get('price'))}")
    else:
        lines.insert(1, "Price: unavailable")

    total = sum(scores)
    lines.append(f"Overall trend: {overall_label(total, len(scores))}")
    lines.append(f"Coverage: {len(scores)} of {len(TIMEFRAMES)} timeframes")
    return lines


def build_status() -> str:
    """Build the complete cache-only status message."""
    lines = [STATUS_TITLE, DISCLAIMER, ""]
    for index, (pair, label) in enumerate(PAIRS):
        if index:
            lines.append("")
        lines.extend(render_pair(pair, label))
    return "\n".join(lines)


def main() -> None:
    """Print the user-facing cached technical context."""
    print(build_status())


if __name__ == "__main__":
    main()
