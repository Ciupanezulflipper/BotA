#!/usr/bin/env python3
"""Regression tests for indicator timeframe validation."""

from __future__ import annotations

import importlib.util
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "build_indicators.py"


def load_build_indicators() -> ModuleType:
    """Load the production indicator builder without modifying sys.path."""
    spec = importlib.util.spec_from_file_location("bota_build_indicators", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_daily_candles(count: int = 70) -> list[dict[str, float]]:
    """Build completed weekday candles with normal weekend gaps."""
    candles: list[dict[str, float]] = []
    current = datetime(2025, 1, 1, 21, 0, tzinfo=timezone.utc)
    price = 1.1000

    while len(candles) < count:
        if current.weekday() < 5:
            opened = price
            closed = price + 0.0003
            candles.append(
                {
                    "time": current.timestamp(),
                    "open": opened,
                    "high": closed + 0.0002,
                    "low": opened - 0.0002,
                    "close": closed,
                }
            )
            price = closed
        current += timedelta(days=1)

    return candles


class TimeframeMinutesTests(unittest.TestCase):
    """Verify all configured updater timeframe labels have minute mappings."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_build_indicators()

    def test_configured_timeframes_map_to_minutes(self) -> None:
        expected = {
            "M15": 15,
            "H1": 60,
            "H4": 240,
            "D1": 1440,
        }
        for timeframe, minutes in expected.items():
            with self.subTest(timeframe=timeframe):
                self.assertEqual(self.module.tf_minutes(timeframe), minutes)

    def test_daily_alias_and_case_are_supported(self) -> None:
        self.assertEqual(self.module.tf_minutes("1D"), 1440)
        self.assertEqual(self.module.tf_minutes("d1"), 1440)

    def test_unknown_timeframe_remains_fail_closed(self) -> None:
        self.assertEqual(self.module.tf_minutes("W1"), 0)


class DailyBundleRegressionTests(unittest.TestCase):
    """Reproduce the production D1 mismatch and assert the repaired contract."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_build_indicators()

    def test_daily_candles_with_weekend_gaps_validate(self) -> None:
        bundle = self.module.build_bundle(
            "EURUSD",
            "D1",
            make_daily_candles(),
        )

        self.assertTrue(bundle["tf_ok"], bundle)
        self.assertEqual(bundle["tf_actual_min"], 1440.0)
        self.assertFalse(bundle["weak"], bundle)
        self.assertEqual(bundle["error"], "")
        self.assertGreater(bundle["ema9"], 0.0)
        self.assertGreater(bundle["ema21"], 0.0)
        self.assertGreater(bundle["atr"], 0.0)

    def test_intraday_data_labeled_daily_is_rejected(self) -> None:
        candles = make_daily_candles()
        start = int(candles[0]["time"])
        for index, candle in enumerate(candles):
            candle["time"] = float(start + index * 3600)

        bundle = self.module.build_bundle("EURUSD", "D1", candles)

        self.assertFalse(bundle["tf_ok"], bundle)
        self.assertEqual(bundle["tf_actual_min"], 60.0)
        self.assertTrue(bundle["weak"], bundle)
        self.assertEqual(bundle["error"], "tf_mismatch")


if __name__ == "__main__":
    unittest.main()
