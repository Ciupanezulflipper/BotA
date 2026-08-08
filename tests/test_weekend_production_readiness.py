from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools import production_signal_policy as policy
from tools import sync_d1_trend_cache as d1_sync


ROOT = Path(__file__).resolve().parents[1]


def trade(**overrides):
    base = {
        "pair": "EURUSD",
        "tf": "M15",
        "direction": "BUY",
        "entry": 1.1000,
        "sl": 1.0980,
        "tp": 1.1040,
        "atr": 0.0010,
        "score": 75.0,
        "confidence": 75.0,
        "filter_rejected": False,
        "filter_reasons": ["macro6=3", "H1_trend_confirmed"],
        "reasons": "ok|adx=25.0|rsi=58.0|macd_hist=0.000100",
    }
    base.update(overrides)
    return base


class ProductionSignalPolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.env = mock.patch.dict(
            os.environ,
            {
                "POLICY_B_ENABLED": "1",
                "POLICY_B_SCORE_MIN": "70",
                "POLICY_B_ADX_MAX": "30",
                "SCALP_SL_ATR_MULT": "2.0",
                "SCALP_TP_ATR_MULT": "4.0",
                "MAX_SL_PIPS": "30",
                "MAX_TP_PIPS": "60",
            },
            clear=False,
        )
        self.env.start()

    def tearDown(self) -> None:
        self.env.stop()

    def test_policy_b_passes_score70_and_adx_below30(self) -> None:
        result = policy.apply_policy(trade(score=70.0, reasons="ok|adx=29.9"))
        self.assertFalse(result["filter_rejected"])
        self.assertTrue(result["policy_b_pass"])
        self.assertEqual(result["policy_b_adx"], 29.9)

    def test_policy_b_rejects_score_below70(self) -> None:
        result = policy.apply_policy(trade(score=69.9, reasons="ok|adx=25.0"))
        self.assertTrue(result["filter_rejected"])
        self.assertFalse(result["policy_b_pass"])
        self.assertIn("policy_b_score<70", result["filter_reasons"])

    def test_policy_b_rejects_adx_at_or_above30(self) -> None:
        result = policy.apply_policy(trade(score=80.0, reasons="ok|adx=30.0"))
        self.assertTrue(result["filter_rejected"])
        self.assertFalse(result["policy_b_pass"])
        self.assertIn("policy_b_adx>=30", result["filter_reasons"])

    def test_policy_b_missing_adx_fails_closed(self) -> None:
        result = policy.apply_policy(trade(reasons="ok|rsi=55.0"))
        self.assertTrue(result["filter_rejected"])
        self.assertIn("policy_b_adx_missing", result["filter_reasons"])

    def test_policy_b_disabled_preserves_current_acceptance(self) -> None:
        with mock.patch.dict(os.environ, {"POLICY_B_ENABLED": "0"}, clear=False):
            result = policy.apply_policy(trade(score=90.0, reasons="ok|adx=45.0"))
        self.assertFalse(result["filter_rejected"])
        self.assertFalse(result["policy_b_enforced"])

    def test_existing_rejection_is_not_reopened(self) -> None:
        original = trade(
            filter_rejected=True,
            filter_reasons=["H1_trend_opposite"],
            reasons="ok|adx=25.0",
        )
        self.assertEqual(policy.apply_policy(original), original)

    def test_usdjpy_risk_uses_point01_pip(self) -> None:
        result = policy.apply_policy(
            trade(
                pair="USDJPY",
                entry=150.0,
                sl=149.997,
                tp=150.006,
                atr=0.2,
                score=75.0,
                reasons="ok|adx=25.0|rsi=58.0",
            )
        )
        self.assertFalse(result["filter_rejected"])
        self.assertEqual(result["sl"], 149.7)
        self.assertEqual(result["tp"], 150.6)
        self.assertEqual(result["filter_rr"], 2.0)
        self.assertEqual(result["risk_pip_size"], 0.01)
        self.assertTrue(result["risk_pair_aware"])

    def test_non_jpy_risk_is_not_rewritten(self) -> None:
        result = policy.apply_policy(trade(sl=1.0981, tp=1.1038))
        self.assertEqual(result["sl"], 1.0981)
        self.assertEqual(result["tp"], 1.1038)
        self.assertNotIn("risk_pair_aware", result)


class D1TrendCacheSyncTests(unittest.TestCase):
    def test_sync_pair_derives_trend_from_local_indicator_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            cache = root / "cache"
            cache.mkdir()
            source = cache / "indicators_USDJPY_D1.json"
            source.write_text(
                json.dumps(
                    {
                        "pair": "USDJPY",
                        "timeframe": "D1",
                        "tf_ok": True,
                        "error": "",
                        "ema9": 150.2,
                        "ema21": 149.8,
                    }
                ),
                encoding="utf-8",
            )
            result = d1_sync.sync_pair(root, "USDJPY")
            self.assertEqual(result["trend"], "BUY")
            target = json.loads(
                (cache / "d1_trend_USDJPY.json").read_text(encoding="utf-8")
            )
            self.assertEqual(target["trend"], "BUY")
            self.assertEqual(target["source"], "local_indicators_D1")

    def test_invalid_d1_bundle_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            cache = root / "cache"
            cache.mkdir()
            (cache / "indicators_EURUSD_D1.json").write_text(
                json.dumps({"tf_ok": False, "error": "tf_mismatch"}),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "timeframe validation"):
                d1_sync.sync_pair(root, "EURUSD")


class ProductionConfigurationTests(unittest.TestCase):
    def test_canonical_cron_monitors_three_pairs_with_policy_b(self) -> None:
        cron = (ROOT / "ops" / "bota_crontab.canonical").read_text(encoding="utf-8")
        signal_lines = [line for line in cron.splitlines() if "signal_watcher_pro.sh" in line]
        self.assertEqual(len(signal_lines), 1)
        line = signal_lines[0]
        self.assertIn('PAIRS="EURUSD GBPUSD USDJPY"', line)
        self.assertIn("POLICY_B_ENABLED=1", line)
        self.assertIn("POLICY_B_SCORE_MIN=70", line)
        self.assertIn("POLICY_B_ADX_MAX=30", line)
        self.assertIn("NEWS_ON=0", line)

    def test_canonical_updater_syncs_three_d1_trends(self) -> None:
        cron = (ROOT / "ops" / "bota_crontab.canonical").read_text(encoding="utf-8")
        updater_lines = [line for line in cron.splitlines() if "indicators_updater.sh" in line]
        self.assertEqual(len(updater_lines), 1)
        line = updater_lines[0]
        self.assertIn('PAIRS="EURUSD GBPUSD USDJPY"', line)
        self.assertIn("sync_d1_trend_cache.py", line)
        self.assertIn("--pairs EURUSD GBPUSD USDJPY", line)

    def test_fusion_runs_final_production_policy(self) -> None:
        fusion = (ROOT / "tools" / "m15_h1_fusion.sh").read_text(encoding="utf-8")
        self.assertIn("production_signal_policy.py", fusion)
        self.assertIn("emit_with_production_policy", fusion)


if __name__ == "__main__":
    unittest.main()
