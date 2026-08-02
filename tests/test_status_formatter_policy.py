#!/usr/bin/env python3
"""Regression tests for BotA's cache-only status formatter."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import format_status


TIMEFRAME_MINUTES = {"H1": 60.0, "H4": 240.0, "D1": 1440.0}


def indicator_bundle(pair: str, timeframe: str, direction: int) -> dict[str, object]:
    """Build one valid deterministic indicator bundle."""
    bullish = direction > 0
    return {
        "pair": pair,
        "timeframe": timeframe,
        "price": 1.23456,
        "age_min": 10.0,
        "tf_ok": True,
        "tf_actual_min": TIMEFRAME_MINUTES[timeframe],
        "weak": False,
        "error": "",
        "ema9": 2.0 if bullish else 1.0,
        "ema21": 1.0 if bullish else 2.0,
        "rsi": 60.0 if bullish else 40.0,
        "macd_hist": 0.1 if bullish else -0.1,
        "adx": 25.0,
        "atr": 0.001,
        "atr_pips": 10.0,
        "bb_upper": 1.3,
        "bb_middle": 1.2,
        "bb_lower": 1.1,
        "bb_squeeze": False,
    }


def write_bundle(
    cache_dir: Path,
    pair: str,
    timeframe: str,
    direction: int,
    overrides: dict[str, object] | None = None,
) -> None:
    """Write one canonical cache fixture."""
    bundle = indicator_bundle(pair, timeframe, direction)
    if overrides is not None:
        bundle.update(overrides)
    path = cache_dir / f"indicators_{pair}_{timeframe}.json"
    path.write_text(json.dumps(bundle), encoding="utf-8")


def seed_valid_pairs(cache_dir: Path) -> None:
    """Write bullish EURUSD and bearish GBPUSD fixtures."""
    for timeframe in format_status.TIMEFRAMES:
        write_bundle(cache_dir, "EURUSD", timeframe, 1)
        write_bundle(cache_dir, "GBPUSD", timeframe, -1)


class StatusFormatterSourceTests(unittest.TestCase):
    """Prevent hidden provider and executable-signal regressions."""

    def test_formatter_source_contains_no_network_or_subprocess_path(self) -> None:
        source = Path(format_status.__file__).read_text(encoding="utf-8")
        forbidden = (
            "emit_snapshot.py",
            "api_credit_tracker.py",
            "subprocess",
            "urllib",
            "requests",
        )
        for token in forbidden:
            with self.subTest(token=token):
                self.assertNotIn(token, source)

    def test_user_facing_labels_and_disclaimer_are_present(self) -> None:
        source = Path(format_status.__file__).read_text(encoding="utf-8")
        for label in (
            "STRONG BUY",
            "BUY",
            "HOLD",
            "SELL",
            "STRONG SELL",
        ):
            with self.subTest(label=label):
                self.assertIn(label, source)
        self.assertIn("not a trade entry", source.lower())
        self.assertNotIn("Vote ", source)
        self.assertNotIn("/9", source)


class StatusFormatterBehaviorTests(unittest.TestCase):
    """Exercise cache validation and user-facing rendering."""

    @staticmethod
    def render(cache_dir: Path) -> str:
        """Render status while temporarily using an isolated cache directory."""
        with patch.object(format_status, "CACHE_DIR", cache_dir):
            return format_status.build_status()

    def test_bull_and_bear_context_is_clear_and_non_actionable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            cache_dir = Path(temporary)
            seed_valid_pairs(cache_dir)
            output = self.render(cache_dir)

        self.assertIn("EUR/USD", output)
        self.assertIn("GBP/USD", output)
        self.assertIn("Overall trend: STRONG BUY", output)
        self.assertIn("Overall trend: STRONG SELL", output)
        self.assertIn("not a trade entry", output.lower())
        self.assertNotIn("Vote ", output)
        self.assertNotIn("/9", output)
        self.assertNotIn("API", output)
        self.assertNotIn(" UTC", output)

    def test_invalid_daily_cache_is_visible_and_excluded(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            cache_dir = Path(temporary)
            seed_valid_pairs(cache_dir)
            write_bundle(
                cache_dir,
                "EURUSD",
                "D1",
                1,
                {
                    "tf_ok": False,
                    "tf_actual_min": 0.0,
                    "weak": True,
                    "error": "tf_mismatch",
                },
            )
            output = self.render(cache_dir)

        self.assertIn("D1: unavailable (tf_mismatch)", output)
        self.assertIn("Coverage: 2 of 3 timeframes", output)

    def test_missing_cache_is_visible(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            cache_dir = Path(temporary)
            output = self.render(cache_dir)

        self.assertIn("H1: unavailable (missing cache)", output)
        self.assertIn("Price: unavailable", output)
        self.assertIn("Coverage: 0 of 3 timeframes", output)

    def test_valid_zero_rsi_is_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            cache_dir = Path(temporary)
            seed_valid_pairs(cache_dir)
            write_bundle(cache_dir, "EURUSD", "H1", -1, {"rsi": 0.0})
            output = self.render(cache_dir)

        self.assertIn("H1: STRONG SELL | RSI 0.0 | MACD falling", output)
        self.assertNotIn("H1: STRONG SELL | RSI 50.0", output)

    def test_invalid_numeric_indicator_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            cache_dir = Path(temporary)
            seed_valid_pairs(cache_dir)
            write_bundle(cache_dir, "EURUSD", "H4", 1, {"rsi": "not-a-number"})
            output = self.render(cache_dir)

        self.assertIn("H4: unavailable (invalid indicators)", output)
        self.assertIn("Coverage: 2 of 3 timeframes", output)

    def test_non_dictionary_json_is_rejected_as_missing_cache(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            cache_dir = Path(temporary)
            path = cache_dir / "indicators_EURUSD_H1.json"
            path.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
            output = self.render(cache_dir)

        self.assertIn("H1: unavailable (missing cache)", output)


if __name__ == "__main__":
    unittest.main()
