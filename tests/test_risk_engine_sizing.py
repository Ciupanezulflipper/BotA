#!/usr/bin/env python3
"""Unit tests for ``tools/risk_engine.py`` config, ATR and sizing math."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from tools import risk_engine


def ohlc(count: int, *, spread: float = 0.0010) -> list[dict]:
    """Build a deterministic OHLC series with a constant true range."""
    rows = []
    for i in range(count):
        base = 1.1000 + i * spread
        rows.append(
            {
                "open": base,
                "high": base + spread,
                "low": base,
                "close": base + spread,
            }
        )
    return rows


def config(**overrides) -> risk_engine.RiskConfig:
    defaults = dict(
        risk_suggest=True,
        balance=0.0,
        risk_pct=0.0,
        sl_atr_mult=1.5,
        rr=2.0,
        lot_base=100000,
        min_lot=0.01,
        lot_step=0.01,
    )
    defaults.update(overrides)
    return risk_engine.RiskConfig(**defaults)


class RiskConfigFromEnvTests(unittest.TestCase):
    def test_defaults_when_environment_is_empty(self):
        with patch.dict(risk_engine.os.environ, {}, clear=True):
            cfg = risk_engine.RiskConfig.from_env()

        self.assertFalse(cfg.risk_suggest)
        self.assertEqual(cfg.balance, 0.0)
        self.assertEqual(cfg.risk_pct, 0.0)
        self.assertEqual(cfg.sl_atr_mult, 1.5)
        self.assertEqual(cfg.rr, 2.0)
        self.assertEqual(cfg.lot_base, 100000)
        self.assertEqual(cfg.min_lot, 0.01)
        self.assertEqual(cfg.lot_step, 0.01)

    def test_environment_overrides_are_cast(self):
        env = {
            "RISK_SUGGEST": "1",
            "ACCOUNT_BALANCE": "5000",
            "RISK_PCT": "2",
            "SL_ATR_MULT": "2.5",
            "RR": "3",
            "LOT_SIZE_BASE": "10000",
            "MIN_LOT": "0.1",
            "LOT_STEP": "0.05",
        }
        with patch.dict(risk_engine.os.environ, env, clear=True):
            cfg = risk_engine.RiskConfig.from_env()

        self.assertTrue(cfg.risk_suggest)
        self.assertEqual(cfg.balance, 5000.0)
        self.assertEqual(cfg.risk_pct, 2.0)
        self.assertEqual(cfg.sl_atr_mult, 2.5)
        self.assertEqual(cfg.rr, 3.0)
        self.assertEqual(cfg.lot_base, 10000)
        self.assertEqual(cfg.min_lot, 0.1)
        self.assertEqual(cfg.lot_step, 0.05)

    def test_empty_values_fall_back_to_defaults(self):
        with patch.dict(
            risk_engine.os.environ,
            {"RISK_SUGGEST": "0", "RR": "", "SL_ATR_MULT": ""},
            clear=True,
        ):
            cfg = risk_engine.RiskConfig.from_env()

        self.assertEqual(cfg.rr, 2.0)
        self.assertEqual(cfg.sl_atr_mult, 1.5)

    def test_only_exact_flag_enables_suggestions(self):
        for value in ("0", "true", "yes", "2", ""):
            with patch.dict(
                risk_engine.os.environ, {"RISK_SUGGEST": value}, clear=True
            ):
                self.assertFalse(risk_engine.RiskConfig.from_env().risk_suggest)


class AtrTests(unittest.TestCase):
    def test_insufficient_or_missing_history_returns_none(self):
        self.assertIsNone(risk_engine.atr([], period=14))
        self.assertIsNone(risk_engine.atr(ohlc(14), period=14))

    def test_constant_true_range_series(self):
        self.assertAlmostEqual(
            risk_engine.atr(ohlc(30, spread=0.0010), period=14),
            0.0010,
            places=9,
        )

    def test_older_candles_outside_the_window_are_ignored(self):
        rows = ohlc(30)
        rows[0]["high"] = 99.0
        self.assertAlmostEqual(
            risk_engine.atr(rows, period=14), risk_engine.atr(ohlc(30), period=14)
        )


class RoundStepTests(unittest.TestCase):
    def test_floors_to_step(self):
        self.assertAlmostEqual(risk_engine._round_step(0.1234, 0.01), 0.12, places=9)
        self.assertAlmostEqual(risk_engine._round_step(0.99, 0.25), 0.75, places=9)

    def test_non_positive_step_is_passthrough(self):
        self.assertEqual(risk_engine._round_step(0.1234, 0.0), 0.1234)
        self.assertEqual(risk_engine._round_step(0.1234, -1.0), 0.1234)


class PriceConversionTests(unittest.TestCase):
    def test_price_distance_to_pips(self):
        self.assertAlmostEqual(
            risk_engine.price_to_pips("EURUSD", 0.0025), 25.0, places=9
        )

    def test_pip_value_per_lot(self):
        self.assertEqual(risk_engine.pip_value_per_lot("EURUSD"), 10.0)


class SuggestSlTpAndSizeTests(unittest.TestCase):
    def test_disabled_config_returns_none(self):
        self.assertIsNone(
            risk_engine.suggest_sl_tp_and_size(
                "EURUSD", "BUY", 1.1000, ohlc(30), config(risk_suggest=False)
            )
        )

    def test_insufficient_history_returns_none(self):
        self.assertIsNone(
            risk_engine.suggest_sl_tp_and_size(
                "EURUSD", "BUY", 1.1000, ohlc(5), config()
            )
        )

    def test_zero_range_history_returns_none(self):
        flat = [{"open": 1.1, "high": 1.1, "low": 1.1, "close": 1.1}] * 30
        self.assertIsNone(
            risk_engine.suggest_sl_tp_and_size("EURUSD", "BUY", 1.1, flat, config())
        )

    def test_buy_places_stop_below_and_target_above(self):
        out = risk_engine.suggest_sl_tp_and_size(
            "EURUSD", "buy", 1.1000, ohlc(30), config()
        )

        assert out is not None
        atr_value = out["atr"]
        sl_dist = 1.5 * atr_value
        self.assertAlmostEqual(out["sl_price"], round(1.1000 - sl_dist, 5), places=9)
        self.assertAlmostEqual(
            out["tp_price"], round(1.1000 + 2.0 * sl_dist, 5), places=9
        )
        self.assertAlmostEqual(out["tp_pips"], 2.0 * out["sl_pips"], places=1)
        self.assertIsNone(out["size_lots"])

    def test_sell_mirrors_the_buy_geometry(self):
        buy = risk_engine.suggest_sl_tp_and_size(
            "EURUSD", "BUY", 1.1000, ohlc(30), config()
        )
        sell = risk_engine.suggest_sl_tp_and_size(
            "EURUSD", "SELL", 1.1000, ohlc(30), config()
        )

        assert buy is not None and sell is not None
        self.assertGreater(sell["sl_price"], 1.1000)
        self.assertLess(sell["tp_price"], 1.1000)
        self.assertAlmostEqual(sell["sl_pips"], buy["sl_pips"], places=1)
        self.assertAlmostEqual(sell["tp_pips"], buy["tp_pips"], places=1)

    def test_position_size_follows_dollar_risk(self):
        out = risk_engine.suggest_sl_tp_and_size(
            "EURUSD",
            "BUY",
            1.1000,
            ohlc(30),
            config(balance=10000.0, risk_pct=1.0),
        )

        assert out is not None
        dollar_risk = 10000.0 * 0.01
        expected_raw = dollar_risk / (out["sl_pips"] * 10.0)
        self.assertAlmostEqual(
            out["size_lots"],
            round(max(0.01, risk_engine._round_step(expected_raw, 0.01)), 2),
            places=9,
        )

    def test_size_never_drops_below_min_lot(self):
        out = risk_engine.suggest_sl_tp_and_size(
            "EURUSD",
            "BUY",
            1.1000,
            ohlc(30),
            config(balance=1.0, risk_pct=0.01, min_lot=0.05),
        )

        assert out is not None
        self.assertEqual(out["size_lots"], 0.05)

    def test_from_env_config_is_used_when_omitted(self):
        with patch.dict(
            risk_engine.os.environ,
            {"RISK_SUGGEST": "1", "ACCOUNT_BALANCE": "10000", "RISK_PCT": "1"},
            clear=True,
        ):
            out = risk_engine.suggest_sl_tp_and_size(
                "EURUSD", "BUY", 1.1000, ohlc(30)
            )

        assert out is not None
        self.assertIsNotNone(out["size_lots"])


if __name__ == "__main__":
    unittest.main()
