#!/usr/bin/env python3
"""Unit tests for ``tools/data_quality.py`` timeframe parsing and OHLC checks."""

from __future__ import annotations

import unittest
from unittest.mock import patch

try:
    import pandas as pd
except ModuleNotFoundError as exc:  # pragma: no cover - pandas is optional locally
    if exc.name != "pandas":
        raise
    pd = None

if pd is not None:
    from tools import data_quality


@unittest.skipIf(pd is None, "pandas is not installed in this runtime")
class TimeframeParsingTests(unittest.TestCase):
    def test_canonical_names(self):
        self.assertEqual(data_quality.tf_to_minutes("M15"), 15)
        self.assertEqual(data_quality.tf_to_minutes("H4"), 240)
        self.assertEqual(data_quality.tf_to_minutes("D1"), 1440)

    def test_case_and_whitespace_are_normalized(self):
        self.assertEqual(data_quality.tf_to_minutes(" m15 "), 15)
        self.assertEqual(data_quality.tf_to_minutes("h1"), 60)

    def test_numeric_suffix_forms(self):
        self.assertEqual(data_quality.tf_to_minutes("15M"), 15)
        self.assertEqual(data_quality.tf_to_minutes("60M"), 60)
        self.assertEqual(data_quality.tf_to_minutes("4H"), 240)

    def test_verbose_alternates(self):
        self.assertEqual(data_quality.tf_to_minutes("1hour"), 60)
        self.assertEqual(data_quality.tf_to_minutes("15min"), 15)
        self.assertEqual(data_quality.tf_to_minutes("1day"), 1440)

    def test_missing_timeframe_is_rejected(self):
        for value in ("", "   ", None):
            with self.assertRaises(ValueError):
                data_quality.tf_to_minutes(value)

    def test_unknown_timeframe_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "unknown timeframe"):
            data_quality.tf_to_minutes("W1")


@unittest.skipIf(pd is None, "pandas is not installed in this runtime")
class ToleranceTests(unittest.TestCase):
    def test_default_tolerance(self):
        with patch.dict(data_quality.os.environ, {}, clear=True):
            self.assertAlmostEqual(data_quality._tol(), 0.35)

    def test_environment_override(self):
        with patch.dict(
            data_quality.os.environ, {"BOTA_TIMESPAN_TOL_PCT": "0.10"}, clear=True
        ):
            self.assertAlmostEqual(data_quality._tol(), 0.10)

    def test_invalid_override_falls_back(self):
        with patch.dict(
            data_quality.os.environ, {"BOTA_TIMESPAN_TOL_PCT": "wide"}, clear=True
        ):
            self.assertAlmostEqual(data_quality._tol(), 0.35)


def frame(rows: int, tf_minutes: int = 15, *, start="2026-01-05 00:00:00"):
    """Build a gap-free OHLC frame indexed by UTC timestamps."""
    index = pd.date_range(start=start, periods=rows, freq=f"{tf_minutes}min", tz="UTC")
    return pd.DataFrame(
        {
            "open": [1.1] * rows,
            "high": [1.2] * rows,
            "low": [1.0] * rows,
            "close": [1.15] * rows,
        },
        index=index,
    )


@unittest.skipIf(pd is None, "pandas is not installed in this runtime")
class ValidateOhlcTests(unittest.TestCase):
    def setUp(self):
        patcher = patch.dict(data_quality.os.environ, {}, clear=True)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_none_or_empty_frame_is_rejected(self):
        self.assertEqual(
            data_quality.validate_ohlc(None, "M15"), (False, "empty dataframe")
        )
        self.assertEqual(
            data_quality.validate_ohlc(pd.DataFrame(), "M15"),
            (False, "empty dataframe"),
        )

    def test_consistent_frame_passes(self):
        ok, msg = data_quality.validate_ohlc(frame(240), "M15")
        self.assertTrue(ok, msg)
        self.assertEqual(msg, "ok")

    def test_too_few_bars_is_reported(self):
        ok, msg = data_quality.validate_ohlc(frame(10), "M15")
        self.assertFalse(ok)
        self.assertIn("not enough bars", msg)
        self.assertIn("rows[10<200]", msg)

    def test_min_bars_argument_is_honoured(self):
        ok, msg = data_quality.validate_ohlc(frame(50), "M15", min_bars=20)
        self.assertTrue(ok, msg)

    def test_min_bars_environment_override_wins(self):
        with patch.dict(data_quality.os.environ, {"BOTA_MIN_BARS": "500"}):
            ok, msg = data_quality.validate_ohlc(frame(240), "M15")
        self.assertFalse(ok)
        self.assertIn("rows[240<500]", msg)

    def test_string_index_is_coerced_to_datetime(self):
        df = frame(240)
        df.index = [str(ts) for ts in df.index]
        ok, msg = data_quality.validate_ohlc(df, "M15")
        self.assertTrue(ok, msg)

    def test_non_datetime_index_is_reported_as_nat(self):
        df = frame(240)
        df.index = ["not-a-timestamp"] * len(df)
        ok, msg = data_quality.validate_ohlc(df, "M15")
        self.assertFalse(ok)
        self.assertEqual(msg, "index contains NaT")

    def test_span_anomaly_is_reported(self):
        # 240 M15 bars spanning hourly steps is ~4x the expected span.
        df = frame(240, tf_minutes=60)
        ok, msg = data_quality.validate_ohlc(df, "M15")
        self.assertFalse(ok)
        self.assertIn("Time span anomaly", msg)

    def test_tolerance_absorbs_a_weekend_gap(self):
        df = frame(240)
        shifted = df.index[120:] + pd.Timedelta(minutes=600)
        df.index = df.index[:120].append(shifted)
        ok, msg = data_quality.validate_ohlc(df, "M15")
        self.assertTrue(ok, msg)

    def test_tf_minutes_environment_override_wins(self):
        df = frame(240, tf_minutes=60)
        with patch.dict(data_quality.os.environ, {"BOTA_TF_MINUTES": "60"}):
            ok, msg = data_quality.validate_ohlc(df, "M15")
        self.assertTrue(ok, msg)


if __name__ == "__main__":
    unittest.main()
