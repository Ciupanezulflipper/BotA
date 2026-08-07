from __future__ import annotations

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import replay_semantics as r  # noqa: E402


UTC = timezone.utc


def dt(text: str) -> datetime:
    return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(UTC)


def bundle(**overrides):
    base = {
        "pair": "EURUSD",
        "timeframe": "M15",
        "price": 1.1005,
        "tf_ok": True,
        "error": "",
        "ema9": 1.1010,
        "ema21": 1.1000,
        "rsi": 60.0,
        "macd_hist": 0.0001,
        "adx": 25.0,
        "atr": 0.0010,
        "bb_upper": 1.1020,
        "bb_middle": 1.1000,
        "bb_lower": 1.0980,
        "bb_squeeze": False,
        "open": 1.1000,
        "high": 1.1010,
        "low": 1.0995,
        "close": 1.1005,
        "prev_close": 1.1000,
    }
    base.update(overrides)
    return base


class ReplaySemanticsTests(unittest.TestCase):
    def test_market_open_historical_boundaries(self):
        self.assertFalse(r.market_open_at(dt("2026-06-01T06:59:00Z")))
        self.assertTrue(r.market_open_at(dt("2026-06-01T07:00:00Z")))
        self.assertTrue(r.market_open_at(dt("2026-06-01T19:59:00Z")))
        self.assertFalse(r.market_open_at(dt("2026-06-01T20:00:00Z")))
        self.assertFalse(r.market_open_at(dt("2026-06-06T12:00:00Z")))

    def test_scoring_session_uses_historical_clock(self):
        self.assertEqual(
            r.scoring_session(dt("2026-06-01T08:00:00Z")),
            (2.0, "session_london"),
        )
        self.assertEqual(
            r.scoring_session(dt("2026-06-01T13:00:00Z")),
            (5.0, "session_overlap"),
        )
        self.assertEqual(
            r.scoring_session(dt("2026-06-01T17:00:00Z")),
            (2.0, "session_ny"),
        )
        self.assertEqual(
            r.scoring_session(dt("2026-06-01T21:00:00Z")),
            (0.0, "session_edge"),
        )

    def test_completed_series_prevents_lookahead(self):
        candles = [
            r.Candle(dt("2026-06-01T00:00:00Z"), 1.0, 1.1, 0.9, 1.0),
            r.Candle(dt("2026-06-01T00:15:00Z"), 1.0, 1.1, 0.9, 1.0),
            r.Candle(dt("2026-06-01T00:30:00Z"), 1.0, 1.1, 0.9, 1.0),
        ]
        series = r.HistoricalSeries("EURUSD", "M15", candles)
        self.assertEqual(series.completed_count(dt("2026-06-01T00:14:59Z")), 0)
        self.assertEqual(series.completed_count(dt("2026-06-01T00:15:00Z")), 1)
        self.assertEqual(series.completed_count(dt("2026-06-01T00:30:00Z")), 2)

    def test_pullback_buffer_reproduces_one_atr_live_code(self):
        direction, tag = r._pullback_direction(bundle(), "ANY")
        self.assertEqual(direction, "BUY")
        self.assertEqual(tag, "pullback_entry")

        direction, tag = r._pullback_direction(bundle(low=1.1011), "ANY")
        self.assertEqual(direction, "HOLD")
        self.assertEqual(tag, "no_pullback")

    def test_score_bundle_matches_component_formula(self):
        signal = r.score_bundle(
            "EURUSD",
            "M15",
            bundle(),
            decision_time=dt("2026-06-01T13:00:00Z"),
            sr_comp=0,
            d1_bundle=bundle(timeframe="D1"),
            config=r.ReplayConfig(),
        )
        self.assertEqual(signal["direction"], "BUY")
        self.assertAlmostEqual(signal["score"], 73.1)
        self.assertAlmostEqual(signal["ema_comp"], 9.0909, places=3)
        self.assertEqual(signal["rsi_comp"], 6.0)
        self.assertEqual(signal["macd_comp"], 10.0)
        self.assertEqual(signal["adx_comp"], 8.0)
        self.assertEqual(signal["bb_comp"], -5.0)
        self.assertEqual(signal["session_comp"], 5.0)
        self.assertEqual(signal["sl"], 1.0985)
        self.assertEqual(signal["tp"], 1.1045)

    def test_adx_below_twenty_is_hard_hold(self):
        signal = r.score_bundle(
            "EURUSD",
            "M15",
            bundle(adx=19.9),
            decision_time=dt("2026-06-01T13:00:00Z"),
            sr_comp=0,
            d1_bundle=bundle(timeframe="D1"),
            config=r.ReplayConfig(),
        )
        self.assertEqual(signal["direction"], "HOLD")
        self.assertIn("adx_regime", signal["filter_reasons"])

    def test_quality_filter_uses_frozen_effective_floor(self):
        signal = r.score_bundle(
            "EURUSD",
            "M15",
            bundle(),
            decision_time=dt("2026-06-01T13:00:00Z"),
            sr_comp=0,
            d1_bundle=bundle(timeframe="D1"),
            config=r.ReplayConfig(),
        )
        filtered = r.quality_apply(signal, r.ReplayConfig())
        self.assertFalse(filtered["filter_rejected"])

        low = dict(signal)
        low["score"] = 64.9
        filtered = r.quality_apply(low, r.ReplayConfig())
        self.assertTrue(filtered["filter_rejected"])
        self.assertIn("score<65", filtered["filter_reasons"])

    def test_h1_neutral_high_score_override_matches_effective_setting(self):
        m15 = {
            "pair": "EURUSD",
            "direction": "BUY",
            "score": 75.0,
            "price": 1.1010,
        }
        h1 = {
            "direction": "HOLD",
            "score": 0.0,
            "filter_rejected": True,
        }
        tag, veto = r._h1_fusion_decision(
            m15,
            h1,
            bundle(timeframe="H4", ema9=1.101, ema21=1.100),
            r.ReplayConfig(),
        )
        self.assertEqual(tag, "H1_trend_neutral_overridden")
        self.assertFalse(veto)

    def test_h1_opposite_override_reproduces_missing_top_level_adx_behavior(self):
        m15 = {
            "pair": "EURUSD",
            "direction": "BUY",
            "score": 90.0,
            "price": 1.1010,
            "adx_raw": 45.0,
        }
        h1 = {
            "direction": "SELL",
            "score": 70.0,
            "filter_rejected": False,
        }
        h4 = bundle(timeframe="H4", ema9=1.101, ema21=1.100)
        tag, veto = r._h1_fusion_decision(m15, h1, h4, r.ReplayConfig())
        self.assertEqual(tag, "H1_trend_opposite")
        self.assertTrue(veto)

        m15["adx"] = 45.0
        tag, veto = r._h1_fusion_decision(m15, h1, h4, r.ReplayConfig())
        self.assertEqual(tag, "H1_trend_opposite_overridden")
        self.assertFalse(veto)

    def test_snapshot_vote_formula(self):
        self.assertEqual(
            r.snapshot_vote(bundle(ema9=1.2, ema21=1.1, rsi=60, macd_hist=0.1)),
            3,
        )
        self.assertEqual(
            r.snapshot_vote(bundle(ema9=1.0, ema21=1.1, rsi=40, macd_hist=-0.1)),
            -3,
        )

    def test_policy_flags_freeze_direction_aware_extreme_rsi(self):
        sell_extreme = {
            "direction": "SELL",
            "filter_rejected": False,
            "score": 75,
            "adx_raw": 25,
            "rsi_raw": 30,
        }
        flags = r.policy_flags(sell_extreme)
        self.assertTrue(flags["policy_b_score70_adx_lt30"])
        self.assertFalse(flags["policy_c_score70_adx_lt30_no_extreme"])
        self.assertTrue(flags["extreme_rsi"])

        buy_stretched = {
            "direction": "BUY",
            "filter_rejected": False,
            "score": 75,
            "adx_raw": 25,
            "rsi_raw": 69.9,
        }
        flags = r.policy_flags(buy_stretched)
        self.assertTrue(flags["policy_c_score70_adx_lt30_no_extreme"])
        self.assertFalse(flags["extreme_rsi"])

    def test_source_blobs_are_frozen(self):
        self.assertEqual(
            r.PRODUCTION_SOURCE_BLOBS["tools/scoring_engine.sh"],
            "09c42362a5c3c679696e86d4131ce5dfabd86608",
        )
        self.assertEqual(
            r.PRODUCTION_SOURCE_BLOBS["tools/m15_h1_fusion.sh"],
            "c1de0312ed928f870b9a45df109b730d30888ee7",
        )


if __name__ == "__main__":
    unittest.main()
