#!/usr/bin/env python3
"""Regression tests for the closed-candle filtering contract in build_indicators.py."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "build_indicators.py"


def load_build_indicators() -> ModuleType:
    """Load the production indicator builder without modifying sys.path."""
    spec = importlib.util.spec_from_file_location(
        "bota_build_indicators_closed_bar", MODULE_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_closed_series(tf_minutes: int, count: int, last_closed_start: float) -> list[dict]:
    """Build `count` sequential completed candles ending at `last_closed_start`."""
    duration = tf_minutes * 60
    start = last_closed_start - duration * (count - 1)
    price = 1.1000
    candles: list[dict] = []
    for i in range(count):
        t = start + i * duration
        opened = price
        closed = price + 0.0003
        candles.append(
            {
                "time": float(t),
                "open": opened,
                "high": closed + 0.0002,
                "low": opened - 0.0002,
                "close": closed,
            }
        )
        price = closed
    return candles


TF_MINUTES = {"M15": 15, "H1": 60, "H4": 240, "D1": 1440}


class FormingCandleExclusionTests(unittest.TestCase):
    """Required regressions 1-4: forming rows excluded on every timeframe."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_build_indicators()

    def _assert_forming_row_excluded(self, tf: str) -> None:
        tf_minutes = TF_MINUTES[tf]
        duration = tf_minutes * 60
        last_closed_start = 2_000_000_000.0
        closed = make_closed_series(tf_minutes, 65, last_closed_start)

        forming_start = last_closed_start + duration
        forming = {
            "time": float(forming_start),
            "open": 999.0,
            "high": 999.0,
            "low": 999.0,
            "close": 999.0,
        }
        now_epoch = forming_start + duration / 2.0  # halfway into the forming candle

        bundle = self.module.build_bundle(
            "EURUSD", tf, closed + [forming], now_epoch=now_epoch
        )

        self.assertTrue(bundle["tf_ok"], bundle)
        self.assertFalse(bundle["weak"], bundle)
        self.assertEqual(bundle["error"], "", bundle)

        last_closed = closed[-1]
        self.assertEqual(bundle["price"], last_closed["close"])
        self.assertEqual(bundle["close"], last_closed["close"])
        expected_age = (now_epoch - last_closed_start) / 60.0
        self.assertAlmostEqual(bundle["age_min"], expected_age, places=6)

    def test_m15_forming_row_excluded(self) -> None:
        self._assert_forming_row_excluded("M15")

    def test_h1_forming_row_excluded(self) -> None:
        self._assert_forming_row_excluded("H1")

    def test_h4_forming_row_excluded(self) -> None:
        self._assert_forming_row_excluded("H4")

    def test_d1_forming_row_excluded(self) -> None:
        self._assert_forming_row_excluded("D1")


class MultipleIncompleteRowsTests(unittest.TestCase):
    """Required regression 5: aligned current-TF row + live snapshot row both excluded."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_build_indicators()

    def test_aligned_forming_row_and_live_snapshot_row_both_excluded(self) -> None:
        tf_minutes = 15
        duration = tf_minutes * 60
        last_closed_start = 2_000_000_000.0
        closed = make_closed_series(tf_minutes, 65, last_closed_start)

        forming_aligned_start = last_closed_start + duration
        forming_aligned = {
            "time": float(forming_aligned_start),
            "open": 999.0,
            "high": 999.0,
            "low": 999.0,
            "close": 999.0,
        }

        now_epoch = forming_aligned_start + duration * 0.9
        # Provider live-snapshot pattern: an extra row not aligned to any
        # candle boundary, stamped close to "now".
        live_snapshot = {
            "time": float(now_epoch - 5.0),
            "open": 777.0,
            "high": 777.0,
            "low": 777.0,
            "close": 777.0,
        }

        bundle = self.module.build_bundle(
            "EURUSD", "M15", closed + [forming_aligned, live_snapshot], now_epoch=now_epoch
        )

        self.assertEqual(bundle["error"], "", bundle)
        self.assertFalse(bundle["weak"], bundle)
        last_closed = closed[-1]
        self.assertEqual(bundle["price"], last_closed["close"])
        self.assertEqual(bundle["close"], last_closed["close"])


class ClosedCandleOhlcTests(unittest.TestCase):
    """Required regressions 6-7: last/previous closed candle supply OHLC/prev_* fields."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_build_indicators()

    def test_last_and_previous_closed_candles_supply_ohlc_fields(self) -> None:
        tf_minutes = 60
        duration = tf_minutes * 60
        last_closed_start = 2_000_000_000.0
        closed = make_closed_series(tf_minutes, 65, last_closed_start)

        forming = {
            "time": float(last_closed_start + duration),
            "open": 999.0,
            "high": 999.0,
            "low": 999.0,
            "close": 999.0,
        }
        now_epoch = last_closed_start + duration + duration / 2.0

        bundle = self.module.build_bundle(
            "EURUSD", "H1", closed + [forming], now_epoch=now_epoch
        )

        last_c = closed[-1]
        prev_c = closed[-2]
        self.assertEqual(bundle["open"], last_c["open"])
        self.assertEqual(bundle["high"], last_c["high"])
        self.assertEqual(bundle["low"], last_c["low"])
        self.assertEqual(bundle["close"], last_c["close"])
        self.assertEqual(bundle["prev_open"], prev_c["open"])
        self.assertEqual(bundle["prev_high"], prev_c["high"])
        self.assertEqual(bundle["prev_low"], prev_c["low"])
        self.assertEqual(bundle["prev_close"], prev_c["close"])


class IndicatorsUseOnlyCompletedCandlesTests(unittest.TestCase):
    """Required regression 8: indicator values computed only from completed candles."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_build_indicators()

    def test_outlier_forming_row_never_influences_indicators(self) -> None:
        tf_minutes = 15
        duration = tf_minutes * 60
        last_closed_start = 2_000_000_000.0
        closed = make_closed_series(tf_minutes, 65, last_closed_start)

        forming = {
            "time": float(last_closed_start + duration),
            "open": 999.0,
            "high": 999.0,
            "low": 999.0,
            "close": 999.0,
        }
        now_epoch = last_closed_start + duration + duration / 2.0

        with_forming = self.module.build_bundle(
            "EURUSD", "M15", closed + [forming], now_epoch=now_epoch
        )
        without_forming = self.module.build_bundle(
            "EURUSD", "M15", list(closed), now_epoch=now_epoch
        )

        for key in (
            "ema9",
            "ema21",
            "rsi",
            "macd_hist",
            "adx",
            "atr",
            "atr_pips",
            "bb_upper",
            "bb_middle",
            "bb_lower",
            "bb_squeeze",
        ):
            self.assertEqual(with_forming[key], without_forming[key], key)


class H4HorizonRegressionTests(unittest.TestCase):
    """Required regressions 11-12: H4 insufficient_data below 60, healthy at/above 60."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_build_indicators()

    def test_h4_with_fewer_than_60_completed_candles_is_insufficient(self) -> None:
        tf_minutes = 240
        duration = tf_minutes * 60
        last_closed_start = 2_000_000_000.0
        closed = make_closed_series(tf_minutes, 59, last_closed_start)
        now_epoch = last_closed_start + duration

        bundle = self.module.build_bundle("EURUSD", "H4", closed, now_epoch=now_epoch)

        self.assertTrue(bundle["tf_ok"], bundle)
        self.assertEqual(bundle["error"], "insufficient_data", bundle)
        self.assertTrue(bundle["weak"], bundle)
        self.assertEqual(bundle["ema9"], 0.0)
        self.assertEqual(bundle["ema21"], 0.0)
        self.assertEqual(bundle["adx"], 0.0)

    def test_h4_with_60_or_more_completed_candles_is_healthy(self) -> None:
        tf_minutes = 240
        duration = tf_minutes * 60
        last_closed_start = 2_000_000_000.0
        closed = make_closed_series(tf_minutes, 61, last_closed_start)
        now_epoch = last_closed_start + duration

        bundle = self.module.build_bundle("EURUSD", "H4", closed, now_epoch=now_epoch)

        self.assertTrue(bundle["tf_ok"], bundle)
        self.assertEqual(bundle["error"], "", bundle)
        self.assertFalse(bundle["weak"], bundle)
        self.assertGreater(bundle["ema9"], 0.0)
        self.assertGreater(bundle["ema21"], 0.0)


if __name__ == "__main__":
    unittest.main()
