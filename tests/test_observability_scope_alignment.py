"""Regression coverage: observability scope must track production PAIRS/TFs.

Historical incident: the pipeline_health evaluator and the watcher cycle
reconciler both hardcoded the two-pair scope ``("EURUSD", "GBPUSD")``, which
meant a missing USDJPY decision could not fail an open-market health check —
USDJPY silently vanished from observability.

These tests pin the following contract:

* both modules derive the production scope from configuration rather than a
  stale hardcode,
* the safe default matches the current three-pair production scope,
* an explicit ``BOTA_REQUIRED_DECISIONS`` override wins,
* complete ``PAIRS`` and ``TIMEFRAMES`` expand to a Cartesian product,
* partial / malformed configuration falls back to the full safe production
  default (never an accidental narrowed scope),
* pipeline_health flags open-market health as unhealthy when USDJPY is
  missing, and healthy when all three M15 decisions are present,
* watcher_cycle_ledger reconciles USDJPY inside the same cycle as EURUSD
  and GBPUSD when the runit environment is applied.
"""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
TOOLS = REPO / "tools"


def load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


pipeline_health = load_module("ph_scope", TOOLS / "pipeline_health.py")
watcher_cycle_ledger = load_module("wcl_scope", TOOLS / "watcher_cycle_ledger.py")


class ScopeDerivationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.env = mock.patch.dict(os.environ, {}, clear=False)
        self.env.start()
        for key in ("PAIRS", "TIMEFRAMES", "BOTA_REQUIRED_DECISIONS"):
            os.environ.pop(key, None)

    def tearDown(self) -> None:
        self.env.stop()

    def test_default_production_scope_is_three_pairs_m15(self) -> None:
        self.assertEqual(
            pipeline_health.required_decisions(),
            ("EURUSD:M15", "GBPUSD:M15", "USDJPY:M15"),
        )
        self.assertEqual(
            watcher_cycle_ledger.expected_scope(),
            (("EURUSD", "M15"), ("GBPUSD", "M15"), ("USDJPY", "M15")),
        )

    def test_env_pairs_and_timeframes_take_cartesian_product(self) -> None:
        os.environ["PAIRS"] = "EURUSD GBPUSD USDJPY"
        os.environ["TIMEFRAMES"] = "M15"
        self.assertEqual(
            pipeline_health.required_decisions(),
            ("EURUSD:M15", "GBPUSD:M15", "USDJPY:M15"),
        )
        self.assertEqual(
            watcher_cycle_ledger.expected_scope(),
            (("EURUSD", "M15"), ("GBPUSD", "M15"), ("USDJPY", "M15")),
        )

    def test_explicit_required_decisions_env_wins(self) -> None:
        os.environ["BOTA_REQUIRED_DECISIONS"] = "eurusd:m15,usdjpy:m15"
        os.environ["PAIRS"] = "SHOULD_BE_IGNORED"
        os.environ["TIMEFRAMES"] = "H1"
        self.assertEqual(
            pipeline_health.required_decisions(),
            ("EURUSD:M15", "USDJPY:M15"),
        )
        self.assertEqual(
            watcher_cycle_ledger.expected_scope(),
            (("EURUSD", "M15"), ("USDJPY", "M15")),
        )

    def test_empty_pairs_env_falls_back_to_safe_default(self) -> None:
        os.environ["PAIRS"] = "   "
        os.environ["TIMEFRAMES"] = ""
        self.assertEqual(
            pipeline_health.required_decisions(),
            ("EURUSD:M15", "GBPUSD:M15", "USDJPY:M15"),
        )
        self.assertEqual(
            watcher_cycle_ledger.expected_scope(),
            (("EURUSD", "M15"), ("GBPUSD", "M15"), ("USDJPY", "M15")),
        )

    def test_partial_pairs_env_falls_back_to_full_safe_default(self) -> None:
        os.environ["PAIRS"] = "EURUSD"
        self.assertEqual(
            pipeline_health.required_decisions(),
            ("EURUSD:M15", "GBPUSD:M15", "USDJPY:M15"),
        )
        self.assertEqual(
            watcher_cycle_ledger.expected_scope(),
            (("EURUSD", "M15"), ("GBPUSD", "M15"), ("USDJPY", "M15")),
        )

    def test_partial_timeframes_env_falls_back_to_full_safe_default(self) -> None:
        os.environ["TIMEFRAMES"] = "H1"
        self.assertEqual(
            pipeline_health.required_decisions(),
            ("EURUSD:M15", "GBPUSD:M15", "USDJPY:M15"),
        )
        self.assertEqual(
            watcher_cycle_ledger.expected_scope(),
            (("EURUSD", "M15"), ("GBPUSD", "M15"), ("USDJPY", "M15")),
        )

    def test_module_level_backcompat_names_use_defaults(self) -> None:
        self.assertIn("USDJPY:M15", pipeline_health.REQUIRED_DECISIONS)
        self.assertIn(("USDJPY", "M15"), watcher_cycle_ledger.EXPECTED)


class HealthEvaluatorFailsWhenUsdjpyMissingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "state").mkdir()
        (self.root / "logs").mkdir()
        self.env = mock.patch.dict(
            os.environ,
            {
                "BOTA_ROOT": str(self.root),
                "PAIRS": "EURUSD GBPUSD USDJPY",
                "TIMEFRAMES": "M15",
            },
            clear=False,
        )
        self.env.start()
        os.environ.pop("BOTA_REQUIRED_DECISIONS", None)

    def tearDown(self) -> None:
        self.env.stop()
        self.tmp.cleanup()

    @staticmethod
    def _seed_pair(pair: str) -> None:
        subprocess.run(
            [
                sys.executable,
                str(TOOLS / "pipeline_ledger.py"),
                "decision",
                "--pair",
                pair,
                "--timeframe",
                "M15",
                "--outcome",
                "filter_rejected",
                "--cycle-id",
                "scope-cycle",
                "--status",
                "completed",
                "--component",
                "watcher",
            ],
            check=True,
            capture_output=True,
            text=True,
        )

    @staticmethod
    def _seed_supporting_components() -> None:
        for component in ("updater", "shadow"):
            subprocess.run(
                [
                    sys.executable,
                    str(TOOLS / "pipeline_ledger.py"),
                    "component",
                    "--component",
                    component,
                    "--status",
                    "completed",
                    "--cycle-id",
                    "scope-cycle",
                ],
                check=True,
                capture_output=True,
                text=True,
            )

    @staticmethod
    def _seed_watcher_terminal() -> None:
        subprocess.run(
            [
                sys.executable,
                str(TOOLS / "pipeline_ledger.py"),
                "component",
                "--component",
                "watcher",
                "--status",
                "completed",
                "--cycle-id",
                "scope-cycle",
                "--terminal-outcome",
                "EVALUATED_REJECTED",
                "--market-reason",
                "MARKET_OPEN",
            ],
            check=True,
            capture_output=True,
            text=True,
        )

    def test_missing_usdjpy_decision_is_unhealthy_open_market(self) -> None:
        self._seed_supporting_components()
        self._seed_pair("EURUSD")
        self._seed_pair("GBPUSD")
        self._seed_watcher_terminal()
        result = pipeline_health.evaluate(market_open=True)
        self.assertFalse(result["healthy"])
        self.assertTrue(
            any(
                "decision_missing_or_stale:USDJPY:M15" in reason
                for reason in result["failure_reasons"]
            ),
            msg=result["failure_reasons"],
        )

    def test_all_three_pairs_present_is_healthy_open_market(self) -> None:
        self._seed_supporting_components()
        self._seed_pair("EURUSD")
        self._seed_pair("GBPUSD")
        self._seed_pair("USDJPY")
        self._seed_watcher_terminal()
        result = pipeline_health.evaluate(market_open=True)
        self.assertTrue(result["healthy"], result["failure_reasons"])
        self.assertIn("USDJPY:M15", result["decisions"])


class WatcherCycleLedgerReconcilesThreePairsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "state").mkdir()
        (self.root / "logs").mkdir()
        self.env = mock.patch.dict(
            os.environ,
            {
                "BOTA_ROOT": str(self.root),
                "PAIRS": "EURUSD GBPUSD USDJPY",
                "TIMEFRAMES": "M15",
            },
            clear=False,
        )
        self.env.start()
        os.environ.pop("BOTA_REQUIRED_DECISIONS", None)

    def tearDown(self) -> None:
        self.env.stop()
        self.tmp.cleanup()

    def test_reconciliation_emits_a_decision_for_every_configured_pair(self) -> None:
        alerts_csv = self.root / "logs" / "alerts.csv"
        cron_log = self.root / "logs" / "cron.signals.log"
        alerts_csv.write_text(
            "pair,tf,provider,filter_rejected,filter_reasons,score\n",
            encoding="utf-8",
        )
        cron_log.write_text("", encoding="utf-8")

        result = subprocess.run(
            [
                sys.executable,
                str(TOOLS / "watcher_cycle_ledger.py"),
                "--cycle-id",
                "three-pair-cycle",
                "--alerts-offset",
                str(alerts_csv.stat().st_size),
                "--log-offset",
                str(cron_log.stat().st_size),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        payload = json.loads(result.stdout)
        pairs = sorted(item["pair"] for item in payload["results"])
        timeframes = sorted({item["timeframe"] for item in payload["results"]})
        self.assertEqual(pairs, ["EURUSD", "GBPUSD", "USDJPY"])
        self.assertEqual(timeframes, ["M15"])


class ConfigurationAndHealthCannotDivergeTests(unittest.TestCase):
    """The runit wrapper's PAIRS and the module defaults must agree."""

    def test_runit_wrapper_pairs_match_default_expected_scope(self) -> None:
        wrapper = (REPO / "ops" / "runit" / "bota-watcher.run").read_text(
            encoding="utf-8"
        )
        for pair in ("EURUSD", "GBPUSD", "USDJPY"):
            with self.subTest(pair=pair):
                self.assertIn(pair, wrapper)
        for pair, timeframe in watcher_cycle_ledger.DEFAULT_EXPECTED:
            with self.subTest(pair=pair, timeframe=timeframe):
                self.assertIn(pair, wrapper)
                self.assertIn(timeframe, wrapper)


if __name__ == "__main__":
    unittest.main()
