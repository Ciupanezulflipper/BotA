from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools import production_signal_policy as policy
from tools import sync_d1_trend_cache as d1_sync


ROOT = Path(__file__).resolve().parents[1]
FUSION = ROOT / "tools" / "m15_h1_fusion.sh"


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

    def test_boolean_numeric_inputs_are_rejected(self) -> None:
        self.assertIsNone(policy._finite(True))
        self.assertIsNone(policy._finite(False))
        result = policy.apply_policy(trade(adx_raw=True, reasons="ok|rsi=55.0"))
        self.assertTrue(result["filter_rejected"])
        self.assertIn("policy_b_adx_missing", result["filter_reasons"])

    def test_strict_json_input_rejects_nonstandard_constants(self) -> None:
        for constant in ("NaN", "Infinity", "-Infinity"):
            with self.subTest(constant=constant):
                with self.assertRaisesRegex(ValueError, "non-standard JSON constant"):
                    policy._decode(f'{{"score":{constant}}}')

    def test_strict_json_output_falls_back_on_nonfinite_value(self) -> None:
        encoded = policy._safe_encode(
            {
                "pair": "EURUSD",
                "tf": "M15",
                "direction": "BUY",
                "score": float("inf"),
            }
        )
        decoded = json.loads(encoded)
        self.assertTrue(decoded["filter_rejected"])
        self.assertEqual(decoded["direction"], "HOLD")
        self.assertIn("production_policy_error_serialization", decoded["reasons"])

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

    def test_invalid_usdjpy_risk_inputs_fail_closed(self) -> None:
        result = policy.apply_policy(
            trade(
                pair="USDJPY",
                entry=True,
                atr=True,
                score=75.0,
                reasons="ok|adx=25.0",
            )
        )
        self.assertTrue(result["filter_rejected"])
        self.assertIn("policy_jpy_risk_invalid", result["filter_reasons"])
        self.assertNotIn("risk_pair_aware", result)

    def test_non_jpy_risk_is_not_rewritten(self) -> None:
        result = policy.apply_policy(trade(sl=1.0981, tp=1.1038))
        self.assertEqual(result["sl"], 1.0981)
        self.assertEqual(result["tp"], 1.1038)
        self.assertNotIn("risk_pair_aware", result)


class D1TrendCacheSyncTests(unittest.TestCase):
    def test_sync_pair_derives_trend_from_local_indicator_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            cache = Path(temp)
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
            with mock.patch.object(d1_sync, "CACHE_DIR", cache):
                result = d1_sync.sync_pair("USDJPY")
            self.assertEqual(result["trend"], "BUY")
            target = json.loads(
                (cache / "d1_trend_USDJPY.json").read_text(encoding="utf-8")
            )
            self.assertEqual(target["trend"], "BUY")
            self.assertEqual(target["source"], "local_indicators_D1")

    def test_invalid_d1_bundle_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            cache = Path(temp)
            (cache / "indicators_EURUSD_D1.json").write_text(
                json.dumps(
                    {
                        "pair": "EURUSD",
                        "timeframe": "D1",
                        "tf_ok": False,
                        "error": "tf_mismatch",
                    }
                ),
                encoding="utf-8",
            )
            with (
                mock.patch.object(d1_sync, "CACHE_DIR", cache),
                self.assertRaisesRegex(ValueError, "timeframe validation"),
            ):
                d1_sync.sync_pair("EURUSD")

    def test_wrong_pair_or_timeframe_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            cache = Path(temp)
            (cache / "indicators_GBPUSD_D1.json").write_text(
                json.dumps(
                    {
                        "pair": "EURUSD",
                        "timeframe": "H1",
                        "tf_ok": True,
                        "error": "",
                        "ema9": 1.2,
                        "ema21": 1.1,
                    }
                ),
                encoding="utf-8",
            )
            with (
                mock.patch.object(d1_sync, "CACHE_DIR", cache),
                self.assertRaisesRegex(ValueError, "identity/timeframe validation"),
            ):
                d1_sync.sync_pair("GBPUSD")

    def test_unsupported_pair_is_rejected_before_path_selection(self) -> None:
        with self.assertRaisesRegex(ValueError, "unsupported production pair"):
            d1_sync._cache_paths("EURJPY")


class FusionPolicyBehaviorTests(unittest.TestCase):
    @staticmethod
    def _write(path: Path, content: str) -> None:
        path.write_text(content, encoding="utf-8")

    def _make_root(self, root: Path, *, include_policy: bool = True) -> None:
        tools = root / "tools"
        cache = root / "cache"
        tools.mkdir(parents=True)
        cache.mkdir(parents=True)

        self._write(
            tools / "scoring_engine.sh",
            """#!/usr/bin/env bash
scenario="${FUSION_SCENARIO:-accepted}"
tf="${2:-M15}"
if [[ "${scenario}" == "m15_failure" && "${tf}" == "M15" ]]; then exit 7; fi
if [[ "${scenario}" == "h1_failure" && "${tf}" == "H1" ]]; then exit 8; fi
if [[ "${tf}" == "M15" ]]; then
  if [[ "${scenario}" == "m15_early" ]]; then
    printf '%s\n' '{"pair":"EURUSD","tf":"M15","direction":"BUY","entry":1.1,"sl":1.098,"tp":1.104,"atr":0.001,"price":1.1,"score":75,"confidence":75,"filter_rejected":true,"filter_reasons":["base_reject"],"reasons":"ok|adx=25.0"}'
  elif [[ "${scenario}" == "policy_missing_scalar" ]]; then
    printf '%s\n' '{"pair":"EURUSD","tf":"M15","direction":"BUY","entry":1.1,"sl":1.098,"tp":1.104,"atr":0.001,"price":1.1,"score":75,"confidence":75,"filter_rejected":true,"filter_reasons":"prior_reason","reasons":"ok|adx=25.0"}'
  else
    printf '%s\n' '{"pair":"EURUSD","tf":"M15","direction":"BUY","entry":1.1,"sl":1.098,"tp":1.104,"atr":0.001,"price":1.1,"score":75,"confidence":75,"filter_rejected":false,"filter_reasons":[],"reasons":"ok|adx=25.0"}'
  fi
else
  if [[ "${scenario}" == "h1_veto" ]]; then
    printf '%s\n' '{"pair":"EURUSD","tf":"H1","direction":"SELL","score":70,"filter_rejected":false,"filter_reasons":[]}'
  else
    printf '%s\n' '{"pair":"EURUSD","tf":"H1","direction":"BUY","score":70,"filter_rejected":false,"filter_reasons":[]}'
  fi
fi
""",
        )
        self._write(
            tools / "quality_filter.py",
            """import sys
raw = sys.stdin.read().strip()
print(raw if raw else "{}")
""",
        )
        self._write(
            tools / "emit_snapshot.py",
            """import os
scenario = os.environ.get("FUSION_SCENARIO", "accepted")
if scenario == "h4_d1_veto":
    print("H4: vote=-3")
    print("D1: vote=-3")
else:
    print("H4: vote=0")
    print("D1: vote=0")
""",
        )
        if include_policy:
            self._write(
                tools / "production_signal_policy.py",
                """import json, sys
data = json.load(sys.stdin)
data["policy_probe_applied"] = True
data["policy_probe_input_rejected"] = bool(data.get("filter_rejected", False))
print(json.dumps(data, separators=(",", ":")))
""",
            )
        (cache / "indicators_EURUSD_H4.json").write_text(
            json.dumps({"ema9": 1.11, "ema21": 1.10}),
            encoding="utf-8",
        )

    def _run_fusion(self, scenario: str, *, include_policy: bool = True) -> dict:
        if shutil.which("jq") is None:
            self.skipTest("jq is required by production fusion")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self._make_root(root, include_policy=include_policy)
            env = os.environ.copy()
            env.update(
                {
                    "BOTA_ROOT": str(root),
                    "NEWS_ON": "0",
                    "FUSION_SCENARIO": scenario,
                    "H1_TREND_MIN_SCORE": "40",
                    "H1_VETO_OVERRIDE_SCORE": "75",
                    "H1_VETO_OVERRIDE_ADX": "40",
                }
            )
            completed = subprocess.run(
                ["bash", str(FUSION), "EURUSD"],
                check=True,
                capture_output=True,
                text=True,
                env=env,
                timeout=15,
            )
            return json.loads(completed.stdout)

    def test_every_fusion_exit_path_applies_final_policy(self) -> None:
        scenarios = {
            "m15_failure": True,
            "m15_early": True,
            "h1_failure": False,
            "h1_veto": True,
            "h4_d1_veto": True,
            "accepted": False,
        }
        for scenario, expected_rejected in scenarios.items():
            with self.subTest(scenario=scenario):
                result = self._run_fusion(scenario)
                self.assertTrue(result["policy_probe_applied"])
                self.assertEqual(
                    result["policy_probe_input_rejected"], expected_rejected
                )

    def test_missing_policy_fallback_normalizes_scalar_filter_reasons(self) -> None:
        result = self._run_fusion("policy_missing_scalar", include_policy=False)
        self.assertTrue(result["filter_rejected"])
        self.assertFalse(result["policy_b_pass"])
        self.assertEqual(
            sorted(result["filter_reasons"]),
            ["macro6=3", "prior_reason", "production_policy_failure"],
        )


class ProductionConfigurationTests(unittest.TestCase):
    def test_canonical_cron_monitors_three_pairs_with_policy_b(self) -> None:
        cron = (ROOT / "ops" / "bota_crontab.canonical").read_text(encoding="utf-8")
        signal_lines = [
            line for line in cron.splitlines() if "signal_watcher_pro.sh" in line
        ]
        self.assertEqual(len(signal_lines), 1)
        line = signal_lines[0]
        self.assertIn('PAIRS="EURUSD GBPUSD USDJPY"', line)
        self.assertIn("POLICY_B_ENABLED=1", line)
        self.assertIn("POLICY_B_SCORE_MIN=70", line)
        self.assertIn("POLICY_B_ADX_MAX=30", line)
        self.assertIn("NEWS_ON=0", line)

    def test_canonical_updater_syncs_three_d1_trends(self) -> None:
        cron = (ROOT / "ops" / "bota_crontab.canonical").read_text(encoding="utf-8")
        updater_lines = [
            line for line in cron.splitlines() if "indicators_updater.sh" in line
        ]
        self.assertEqual(len(updater_lines), 1)
        line = updater_lines[0]
        self.assertIn('PAIRS="EURUSD GBPUSD USDJPY"', line)
        self.assertIn("sync_d1_trend_cache.py", line)
        self.assertIn("--pairs EURUSD GBPUSD USDJPY", line)


if __name__ == "__main__":
    unittest.main()
