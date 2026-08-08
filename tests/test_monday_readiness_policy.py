#!/usr/bin/env python3
"""Regression tests for BotA Monday readiness and reconciliation health."""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
PIPELINE = ROOT / "tools" / "pipeline_health.py"
WATCHER_LEDGER = ROOT / "tools" / "watcher_cycle_ledger.py"
WORKER = ROOT / "tools" / "profitlab_delivery.py"
D1_SYNC = ROOT / "tools" / "sync_d1_trend_cache.py"
READINESS = ROOT / "tools" / "monday_readiness.py"

PAIRS = ("EURUSD", "GBPUSD", "USDJPY")
NOW_NS = 10_000_000_000
BOOT = "test-boot"


def load_pipeline_module():
    spec = importlib.util.spec_from_file_location("pipeline_health_test", PIPELINE)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load pipeline_health.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def component_event(status: str = "completed") -> dict[str, object]:
    return {
        "boot_id": BOOT,
        "monotonic_ns": NOW_NS - 1_000_000_000,
        "status": status,
        "cycle_id": "test-cycle",
        "event_id": "test-event",
    }


def decision_event() -> dict[str, object]:
    return {
        "boot_id": BOOT,
        "monotonic_ns": NOW_NS - 1_000_000_000,
        "status": "completed",
        "outcome": "accepted",
        "event_id": "decision-event",
    }


def write_pipeline_state(
    root: Path,
    *,
    include_profitlab: bool = True,
    include_market_components: bool = True,
    decision_pairs: tuple[str, ...] = PAIRS,
) -> None:
    components: dict[str, object] = {}
    if include_profitlab:
        components["profitlab_delivery"] = component_event()
    if include_market_components:
        for name in ("updater", "watcher", "shadow", "d1_sync"):
            components[name] = component_event()
    decisions = {f"{pair}:M15": decision_event() for pair in decision_pairs}
    path = root / "state" / "pipeline_progress.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "boot_id": BOOT,
                "components": components,
                "decisions": decisions,
            }
        ),
        encoding="utf-8",
    )


class PipelineReadinessTests(unittest.TestCase):
    @staticmethod
    def evaluate(root: Path, market_open: bool):
        module = load_pipeline_module()
        with (
            mock.patch.dict(os.environ, {"BOTA_ROOT": str(root)}, clear=False),
            mock.patch.object(module, "boot_id", return_value=BOOT),
            mock.patch.object(module, "monotonic_ns", return_value=NOW_NS),
        ):
            return module.evaluate(market_open=market_open)

    def test_market_open_requires_usdjpy_decision(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "BotA"
            write_pipeline_state(root, decision_pairs=("EURUSD", "GBPUSD"))
            result = self.evaluate(root, market_open=True)

        self.assertFalse(result["healthy"])
        self.assertIn("USDJPY:M15", result["required_decisions"])
        self.assertTrue(
            any(
                reason.startswith("decision_missing_or_stale:USDJPY:M15")
                for reason in result["failure_reasons"]
            )
        )

    def test_market_open_requires_d1_sync(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "BotA"
            write_pipeline_state(root)
            state_path = root / "state" / "pipeline_progress.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            del state["components"]["d1_sync"]
            state_path.write_text(json.dumps(state), encoding="utf-8")
            result = self.evaluate(root, market_open=True)

        self.assertFalse(result["healthy"])
        self.assertTrue(
            any(
                reason.startswith("d1_sync_progress_stale_or_failed")
                for reason in result["failure_reasons"]
            )
        )

    def test_market_closed_suspends_market_pipeline_but_requires_profitlab(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "BotA"
            write_pipeline_state(
                root,
                include_market_components=False,
                decision_pairs=(),
            )
            result = self.evaluate(root, market_open=False)

        self.assertTrue(result["healthy"], result)
        self.assertIn("profitlab_delivery", result["components"])
        self.assertIn("market", result["components"])

    def test_missing_profitlab_fails_even_when_market_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "BotA"
            write_pipeline_state(
                root,
                include_profitlab=False,
                include_market_components=False,
                decision_pairs=(),
            )
            result = self.evaluate(root, market_open=False)

        self.assertFalse(result["healthy"])
        self.assertTrue(
            any(
                reason.startswith("profitlab_delivery_progress_stale_or_failed")
                for reason in result["failure_reasons"]
            )
        )

    def test_three_pair_happy_path_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "BotA"
            write_pipeline_state(root)
            result = self.evaluate(root, market_open=True)

        self.assertTrue(result["healthy"], result)
        self.assertEqual(
            result["required_decisions"],
            ["EURUSD:M15", "GBPUSD:M15", "USDJPY:M15"],
        )


class ProducerLedgerIntegrationTests(unittest.TestCase):
    def test_profitlab_bootstrap_records_completed_progress(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "BotA"
            (root / "logs").mkdir(parents=True)
            (root / "state").mkdir(parents=True)
            (root / "logs" / "alerts.csv").write_text(
                "ts,pair,tf,direction,score,confidence,entry,sl,tp,provider,"
                "filter_rejected,filter_reasons,reasons,ema_comp,rsi_comp,"
                "macd_comp,adx_comp,adx_raw,rsi_raw,macd_hist_raw,macro6,"
                "h1_trend,tier,session,adx_regime\n",
                encoding="utf-8",
            )
            environment = os.environ.copy()
            environment["BOTA_ROOT"] = str(root)
            result = subprocess.run(
                [sys.executable, str(WORKER), "--bootstrap"],
                cwd=ROOT,
                env=environment,
                text=True,
                capture_output=True,
                timeout=30,
                check=False,
            )
            state = json.loads(
                (root / "state" / "pipeline_progress.json").read_text(
                    encoding="utf-8"
                )
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        component = state["components"]["profitlab_delivery"]
        self.assertEqual(component["status"], "completed")

    def test_d1_sync_records_completed_three_pair_progress(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "BotA"
            cache = root / "cache"
            cache.mkdir(parents=True)
            for index, pair in enumerate(PAIRS):
                (cache / f"indicators_{pair}_D1.json").write_text(
                    json.dumps(
                        {
                            "pair": pair,
                            "timeframe": "D1",
                            "tf_ok": True,
                            "ema9": 1.20 + index,
                            "ema21": 1.10 + index,
                        }
                    ),
                    encoding="utf-8",
                )
            environment = os.environ.copy()
            environment["BOTA_ROOT"] = str(root)
            result = subprocess.run(
                [sys.executable, str(D1_SYNC), "--pairs", *PAIRS],
                cwd=ROOT,
                env=environment,
                text=True,
                capture_output=True,
                timeout=30,
                check=False,
            )
            state = json.loads(
                (root / "state" / "pipeline_progress.json").read_text(
                    encoding="utf-8"
                )
            )
            target_exists = all(
                (cache / f"d1_trend_{pair}.json").exists() for pair in PAIRS
            )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(target_exists)
        component = state["components"]["d1_sync"]
        self.assertEqual(component["status"], "completed")


class ReadinessSourcePolicyTests(unittest.TestCase):
    def test_readiness_tool_is_read_only_and_network_free(self) -> None:
        source = READINESS.read_text(encoding="utf-8")
        self.assertNotIn("urlopen(", source)
        self.assertNotIn("HTTPSConnection(", source)
        self.assertNotIn("requests.", source)
        self.assertNotIn("curl ", source)
        self.assertNotIn('["crontab"', source)
        self.assertIn("verify_canonical_crontab.sh", source)
        self.assertIn("control_plane_status.py", source)
        self.assertIn("pipeline_health.py", source)

    def test_readiness_scope_is_three_pair_policy_b(self) -> None:
        source = READINESS.read_text(encoding="utf-8")
        self.assertIn('("EURUSD", "GBPUSD", "USDJPY")', source)
        self.assertIn("POLICY_B_ENABLED=1", source)
        self.assertIn("POLICY_B_SCORE_MIN=70", source)
        self.assertIn("POLICY_B_ADX_MAX=30", source)

    def test_watcher_reconciliation_scope_matches_three_pair_production(self) -> None:
        source = WATCHER_LEDGER.read_text(encoding="utf-8")
        self.assertIn(
            'EXPECTED = (("EURUSD", "M15"), ("GBPUSD", "M15"), ("USDJPY", "M15"))',
            source,
        )


if __name__ == "__main__":
    unittest.main()
