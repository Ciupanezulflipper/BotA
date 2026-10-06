from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from ops import vps_release_gate
from tools import signal_closer, vps_orchestrator

REPO = Path(__file__).resolve().parents[1]
TOOLS = REPO / "tools"
FETCHER = TOOLS / "data_fetch_candles.sh"
POLICY_PATH = REPO / "config" / "production-vps.env"


def _write_cache(path: Path, *, provider: str, granularity: str,
                  timestamps: list[int], highs: list[float], lows: list[float]) -> None:
    payload = {
        "chart": {
            "result": [
                {
                    "meta": {"_provider": provider, "dataGranularity": granularity},
                    "timestamp": timestamps,
                    "indicators": {"quote": [{"high": highs, "low": lows}]},
                }
            ],
            "error": None,
        }
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


class VersionedPolicyIsYahooTests(unittest.TestCase):
    def test_versioned_policy_is_yahoo(self) -> None:
        raw = POLICY_PATH.read_text(encoding="utf-8")
        self.assertIn("PRODUCTION_CANDLE_PROVIDER=yahoo", raw)

        policy = vps_orchestrator.load_frozen_policy()
        self.assertEqual(policy["PRODUCTION_CANDLE_PROVIDER"], "yahoo")

        hostile_ambient = {"PRODUCTION_CANDLE_PROVIDER": "oanda"}
        overridden = vps_orchestrator.load_frozen_policy(ambient=hostile_ambient)
        self.assertEqual(overridden["PRODUCTION_CANDLE_PROVIDER"], "yahoo")


class FetcherContractIsYahooOnlyTests(unittest.TestCase):
    def test_source_has_no_oanda_network_path(self) -> None:
        source = FETCHER.read_text(encoding="utf-8")
        self.assertIn("PRODUCTION_CANDLE_PROVIDER", source)
        self.assertNotIn("OANDA_API_TOKEN", source)
        self.assertNotIn("OANDA_API_URL", source)
        self.assertNotIn("api-fxpractice.oanda.com", source)
        self.assertNotIn("oanda_granularity_for_tf", source)
        self.assertIn('result.setdefault("meta", {})["_provider"] = provider', source)

    def test_fetcher_fails_closed_before_any_network_when_provider_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            env = {**os.environ, "BOTA_CODE_ROOT": str(REPO), "BOTA_MUTABLE_ROOT": temp}
            env.pop("PRODUCTION_CANDLE_PROVIDER", None)
            result = subprocess.run(
                ["bash", str(FETCHER), "EURUSD", "M15"],
                env=env, text=True, capture_output=True, timeout=10,
            )
        self.assertEqual(result.returncode, 1)
        self.assertIn("unsupported_provider_contract", result.stderr)

    def test_fetcher_fails_closed_for_unknown_provider_value(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            env = {**os.environ, "BOTA_CODE_ROOT": str(REPO), "BOTA_MUTABLE_ROOT": temp,
                   "PRODUCTION_CANDLE_PROVIDER": "oanda"}
            result = subprocess.run(
                ["bash", str(FETCHER), "EURUSD", "M15"],
                env=env, text=True, capture_output=True, timeout=10,
            )
        self.assertEqual(result.returncode, 1)
        self.assertIn("unsupported_provider_contract", result.stderr)

    def test_provider_gate_precedes_argument_validation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            env = {**os.environ, "BOTA_CODE_ROOT": str(REPO), "BOTA_MUTABLE_ROOT": temp,
                   "PRODUCTION_CANDLE_PROVIDER": "yahoo"}
            result = subprocess.run(
                ["bash", str(FETCHER)],
                env=env, text=True, capture_output=True, timeout=10,
            )
        self.assertEqual(result.returncode, 1)
        self.assertIn("Usage:", result.stderr)
        self.assertNotIn("unsupported_provider_contract", result.stderr)

    def test_yahoo_failure_paths_are_fail_closed_in_source(self) -> None:
        source = FETCHER.read_text(encoding="utf-8")
        self.assertIn('exit 3', source)
        self.assertIn('die "curl failed', source)
        self.assertIn('exit 2', source)


class ClosertCacheContractTests(unittest.TestCase):
    def test_yahoo_provider_marker_is_consumable_by_closer(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            cache_dir = Path(temp)
            server_epoch = 2_000_000_000
            _write_cache(
                cache_dir / "EURUSD_M15.json",
                provider="yahoo", granularity="15m",
                timestamps=[server_epoch - 1800, server_epoch - 900, server_epoch - 60],
                highs=[1.1050, 1.1060, 1.1055],
                lows=[1.1010, 1.1020, 1.1015],
            )
            with mock.patch.object(signal_closer, "CACHE_DIR", cache_dir):
                candles, reason = signal_closer.load_candle_cache(
                    "EURUSD", "M15", server_epoch, "yahoo"
                )
        self.assertEqual(reason, "ok")
        self.assertEqual(len(candles), 3)

    def test_closer_rejects_provider_mismatch(self) -> None:
        server_epoch = 2_000_000_000
        for bad_provider in ("oanda", "unknown", ""):
            with self.subTest(provider=bad_provider):
                with tempfile.TemporaryDirectory() as temp:
                    cache_dir = Path(temp)
                    _write_cache(
                        cache_dir / "EURUSD_M15.json",
                        provider=bad_provider, granularity="15m",
                        timestamps=[server_epoch - 60],
                        highs=[1.1050], lows=[1.1010],
                    )
                    with mock.patch.object(signal_closer, "CACHE_DIR", cache_dir):
                        candles, reason = signal_closer.load_candle_cache(
                            "EURUSD", "M15", server_epoch, "yahoo"
                        )
                self.assertEqual(candles, [])
                self.assertIn("provider mismatch", reason)

    def test_closer_rejects_missing_or_unknown_granularity(self) -> None:
        server_epoch = 2_000_000_000
        for bad_granularity in ("", "BOGUS", "5m"):
            with self.subTest(granularity=bad_granularity):
                with tempfile.TemporaryDirectory() as temp:
                    cache_dir = Path(temp)
                    _write_cache(
                        cache_dir / "EURUSD_M15.json",
                        provider="yahoo", granularity=bad_granularity,
                        timestamps=[server_epoch - 60],
                        highs=[1.1050], lows=[1.1010],
                    )
                    with mock.patch.object(signal_closer, "CACHE_DIR", cache_dir):
                        candles, reason = signal_closer.load_candle_cache(
                            "EURUSD", "M15", server_epoch, "yahoo"
                        )
                self.assertEqual(candles, [])
                self.assertIn("granularity mismatch", reason)


class TimeframeNormalizationTests(unittest.TestCase):
    def test_yahoo_intervals_map_to_canonical_timeframes(self) -> None:
        self.assertEqual(signal_closer.normalize_granularity("15m"), "M15")
        self.assertEqual(signal_closer.normalize_granularity("30m"), "M30")
        self.assertEqual(signal_closer.normalize_granularity("1h"), "H1")
        self.assertEqual(signal_closer.normalize_granularity("4h"), "H4")
        self.assertEqual(signal_closer.normalize_granularity("1d"), "D1")

    def test_canonical_values_remain_valid(self) -> None:
        for value in ("M15", "M30", "H1", "H4", "D1"):
            self.assertEqual(signal_closer.normalize_granularity(value), value)
        self.assertEqual(signal_closer.normalize_granularity("D"), "D1")

    def test_missing_or_unknown_granularity_fails_closed(self) -> None:
        self.assertIsNone(signal_closer.normalize_granularity(""))
        self.assertIsNone(signal_closer.normalize_granularity(None))
        self.assertIsNone(signal_closer.normalize_granularity("5m"))
        self.assertIsNone(signal_closer.normalize_granularity("BOGUS"))

    def test_mismatch_between_canonical_forms_is_rejected(self) -> None:
        self.assertNotEqual(signal_closer.normalize_granularity("1h"), "M15")


class UpdaterHasNoDirectOandaD1PathTests(unittest.TestCase):
    def test_legacy_direct_oanda_d1_function_is_removed(self) -> None:
        source = (TOOLS / "indicators_updater.sh").read_text(encoding="utf-8")
        self.assertNotIn("refresh_d1_trend_cache", source)
        self.assertNotIn("OANDA_API_TOKEN", source)
        self.assertNotIn("api-fxpractice.oanda.com", source)

    def test_orchestrator_second_updater_stage_is_sync_d1_trend_cache(self) -> None:
        jobs = {job.name: job for job in vps_orchestrator.production_jobs()}
        updater_job = jobs["updater"]
        self.assertEqual(updater_job.stage_names, ("indicators_updater", "d1_sync"))
        self.assertEqual(len(updater_job.commands), 2)
        self.assertIn("sync_d1_trend_cache.py", updater_job.commands[1][1])


class ReleaseGateFreezesProviderContractTests(unittest.TestCase):
    def test_repository_contract_requires_yahoo(self) -> None:
        result = vps_release_gate.evaluate(REPO)
        self.assertTrue(result["checks"]["provider_contract_frozen"])
        self.assertEqual(result["PROVIDER_CONTRACT_FROZEN"], "PASS")
        self.assertEqual(result["REPOSITORY_RELEASE_GATE"], "PASS")

    def test_alternate_provider_value_fails_the_contract_check(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            hostile = Path(temp) / "production-vps.env"
            hostile.write_text(
                POLICY_PATH.read_text(encoding="utf-8").replace(
                    "PRODUCTION_CANDLE_PROVIDER=yahoo",
                    "PRODUCTION_CANDLE_PROVIDER=oanda",
                ),
                encoding="utf-8",
            )
            policy = vps_release_gate.env_file(hostile)
        self.assertNotEqual(
            policy.get("PRODUCTION_CANDLE_PROVIDER"),
            vps_release_gate.REQUIRED_CANDLE_PROVIDER,
        )


if __name__ == "__main__":
    unittest.main()
