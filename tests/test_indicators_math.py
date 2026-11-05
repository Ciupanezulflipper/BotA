#!/usr/bin/env python3
"""Unit tests for the base indicator math helpers in ``tools/indicators.py``."""

from __future__ import annotations

import unittest

from tools import indicators


class EmaTests(unittest.TestCase):
    """``ema`` seeds on the first sample and never shortens the series."""

    def test_empty_or_invalid_period_returns_empty_series(self):
        self.assertEqual(indicators.ema([], 14), [])
        self.assertEqual(indicators.ema([1.0, 2.0], 0), [])
        self.assertEqual(indicators.ema([1.0, 2.0], -3), [])

    def test_first_value_seeds_the_average(self):
        out = indicators.ema([1.0, 2.0, 3.0], 2)
        self.assertEqual(len(out), 3)
        self.assertEqual(out[0], 1.0)

    def test_recursion_matches_smoothing_factor(self):
        values = [1.0, 2.0, 3.0]
        period = 2
        k = 2.0 / (period + 1.0)
        expected = [values[0]]
        for value in values[1:]:
            expected.append((value - expected[-1]) * k + expected[-1])

        for actual, want in zip(indicators.ema(values, period), expected):
            self.assertAlmostEqual(actual, want, places=12)

    def test_constant_series_stays_flat(self):
        self.assertEqual(indicators.ema([5.0] * 6, 3), [5.0] * 6)


class RsiTests(unittest.TestCase):
    """``rsi`` is neutral until it has ``period + 1`` samples."""

    def test_short_series_is_neutral(self):
        self.assertEqual(indicators.rsi([1.0, 2.0, 3.0], 5), [50.0] * 3)

    def test_invalid_period_is_neutral(self):
        self.assertEqual(indicators.rsi([1.0, 2.0, 3.0], 0), [50.0] * 3)

    def test_leading_window_stays_neutral(self):
        values = [float(i) for i in range(20)]
        out = indicators.rsi(values, 14)
        self.assertEqual(len(out), len(values))
        self.assertEqual(out[:14], [50.0] * 14)

    def test_monotonic_rise_saturates_at_100(self):
        out = indicators.rsi([float(i) for i in range(20)], 14)
        self.assertEqual(out[-1], 100.0)

    def test_monotonic_fall_bottoms_out(self):
        out = indicators.rsi([float(20 - i) for i in range(20)], 14)
        self.assertAlmostEqual(out[-1], 0.0, places=9)

    def test_mixed_series_stays_inside_bounds(self):
        values = [1.0, 1.2, 1.1, 1.4, 1.3, 1.5, 1.45, 1.6, 1.55, 1.7,
                  1.65, 1.8, 1.75, 1.9, 1.85, 2.0]
        out = indicators.rsi(values, 14)
        self.assertTrue(all(0.0 <= v <= 100.0 for v in out))
        self.assertNotEqual(out[-1], 50.0)


class LastNonNoneTests(unittest.TestCase):
    """``last_non_none`` scans backwards and tolerates fully empty input."""

    def test_returns_latest_populated_value(self):
        self.assertEqual(indicators.last_non_none([1, None, 3, None]), 3)

    def test_all_none_returns_none(self):
        self.assertIsNone(indicators.last_non_none([None, None]))

    def test_empty_returns_none(self):
        self.assertIsNone(indicators.last_non_none([]))

    def test_falsy_values_are_still_values(self):
        self.assertEqual(indicators.last_non_none([1, 0]), 0)


if __name__ == "__main__":
    unittest.main()
