#!/usr/bin/env python3
"""Unit tests for ``tools/atr_calculator.py`` true-range averaging."""

from __future__ import annotations

import unittest

from tools import atr_calculator


def candles(count: int, *, step: float = 1.0, spread: float = 1.0) -> list[dict]:
    """Build a deterministic rising OHLC series."""
    return [
        {
            "high": step * i + spread,
            "low": step * i,
            "close": step * i + spread / 2.0,
        }
        for i in range(count)
    ]


def expected_atr(rows: list[dict], period: int) -> float:
    """Reference implementation of the documented ATR contract."""
    trs = []
    for i in range(1, len(rows)):
        high = rows[i]["high"]
        low = rows[i]["low"]
        prev_close = rows[i - 1]["close"]
        trs.append(max(high - low, abs(high - prev_close), abs(low - prev_close)))
    window = trs[-period:]
    return sum(window) / len(window)


class CalculateAtrTests(unittest.TestCase):
    def test_insufficient_history_returns_none(self):
        self.assertIsNone(atr_calculator.calculate_atr(candles(14), period=14))
        self.assertIsNone(atr_calculator.calculate_atr([], period=14))

    def test_exact_minimum_history_is_accepted(self):
        rows = candles(15)
        self.assertAlmostEqual(
            atr_calculator.calculate_atr(rows, period=14),
            expected_atr(rows, 14),
            places=12,
        )

    def test_only_the_last_period_true_ranges_are_averaged(self):
        calm = candles(20, step=1.0, spread=1.0)
        spike = dict(calm[0])
        spike["high"] = 1000.0
        noisy = [spike] + calm

        self.assertAlmostEqual(
            atr_calculator.calculate_atr(noisy, period=5),
            atr_calculator.calculate_atr(calm, period=5),
            places=12,
        )

    def test_flat_market_has_zero_range(self):
        flat = [{"high": 1.0, "low": 1.0, "close": 1.0}] * 20
        self.assertEqual(atr_calculator.calculate_atr(flat, period=14), 0.0)

    def test_true_range_uses_gap_against_previous_close(self):
        rows = [
            {"high": 1.0, "low": 0.9, "close": 0.95},
            {"high": 2.0, "low": 1.9, "close": 1.95},
        ]
        # gap high - prev_close = 1.05 dominates the intrabar range of 0.10.
        self.assertAlmostEqual(
            atr_calculator.calculate_atr(rows, period=1), 1.05, places=12
        )


class AtrInPipsTests(unittest.TestCase):
    def test_converts_using_module_pip_size(self):
        self.assertAlmostEqual(
            atr_calculator.atr_in_pips(0.15),
            0.15 / atr_calculator.PIP_SIZE,
            places=9,
        )

    def test_none_input_returns_none(self):
        self.assertIsNone(atr_calculator.atr_in_pips(None))

    def test_zero_atr_returns_none(self):
        # Documented current behaviour: falsy ATR is reported as unavailable.
        self.assertIsNone(atr_calculator.atr_in_pips(0.0))


if __name__ == "__main__":
    unittest.main()
