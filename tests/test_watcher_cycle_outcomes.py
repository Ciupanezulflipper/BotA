"""Regression coverage for the per-cycle terminal-outcome contract.

Every scheduled watcher cycle must produce EXACTLY ONE terminal outcome from
the Monday-readiness enum. These tests exercise both the direct pipeline
ledger surface (single-decision emission) and the aggregated cycle-level
outcome emitted by ``tools/watcher_gated_cycle.sh``.

The suite also encodes structural invariants that must not regress:

* alerts.csv decision persistence happens before Telegram delivery dedup —
  this is the observability contract that lets us distinguish "no signal"
  from "signal suppressed post-decision".
* the ``pipeline_health`` evaluator flags open-market ``CLOCK_GATE_FAILED``
  cycles as unhealthy but leaves closed-market inactivity healthy.
* fixture dry-run mode is refused at the canonical production root so a leaked
  test flag cannot synthesize green liveness on the phone.
"""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
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


pipeline_ledger = load_module("pl_watcher_outcome", TOOLS / "pipeline_ledger.py")
pipeline_health = load_module("ph_watcher_outcome", TOOLS / "pipeline_health.py")


class TemporaryBotARoot:
    """Reusable fixture mixin for concrete unittest.TestCase subclasses."""

    def setUp(self) -> None:
        super().setUp()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "state").mkdir(parents=True)
        (self.root / "logs").mkdir(parents=True)
        (self.root / "tools").mkdir(parents=True)
        for name in (
            "pipeline_ledger.py",
            "pipeline_health.py",
            "watcher_gated_cycle.sh",
            "market_open.sh",
            "run_signal_watcher_with_ledger.sh",
            "watcher_cycle_ledger.py",
        ):
            src = TOOLS / name
            if src.exists():
                shutil.copy2(src, self.root / "tools" / name)
        self.env = mock.patch.dict(
            os.environ, {"BOTA_ROOT": str(self.root)}, clear=False
        )
        self.env.start()
        for key in ("PAIRS", "TIMEFRAMES", "BOTA_REQUIRED_DECISIONS"):
            os.environ.pop(key, None)

    def tearDown(self) -> None:
        self.env.stop()
        self.tmp.cleanup()
        super().tearDown()

    def state(self) -> dict:
        try:
            return json.loads(
                (self.root / "state" / "pipeline_progress.json").read_text()
            )
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def run_gate(self, hint: str, *, dry_run: bool = True) -> subprocess.CompletedProcess:
        env = os.environ.copy()
        env["BOTA_ROOT"] = str(self.root)
        env["WATCHER_GATED_MARKET_HINT"] = hint
        if dry_run:
            env["WATCHER_GATED_DRY_RUN"] = "1"
        return subprocess.run(
            ["bash", str(self.root / "tools" / "watcher_gated_cycle.sh")],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )


class LedgerTerminalOutcomeContractTests(TemporaryBotARoot, unittest.TestCase):
    """Validate ledger enforcement of the 9-item terminal-outcome enum."""

    def test_accepts_all_nine_terminal_outcomes(self) -> None:
        for outcome in (
            "MARKET_CLOSED",
            "CLOCK_GATE_FAILED",
            "DATA_FETCH_FAILED",
            "DATA_STALE",
            "EVALUATED_REJECTED",
            "EVALUATED_ACCEPTED",
            "DEDUP_SUPPRESSED_DELIVERY",
            "DELIVERY_ATTEMPTED",
            "INTERNAL_ERROR",
        ):
            self.assertEqual(
                pipeline_ledger.normalize_terminal_outcome(outcome),
                outcome,
            )

    def test_rejects_unknown_terminal_outcome(self) -> None:
        with self.assertRaises(ValueError):
            pipeline_ledger.normalize_terminal_outcome("BOGUS_OUTCOME")

    def test_empty_outcome_is_normalized_to_empty(self) -> None:
        self.assertEqual(pipeline_ledger.normalize_terminal_outcome(""), "")
        self.assertEqual(pipeline_ledger.normalize_terminal_outcome(None), "")

    def test_ledger_writes_terminal_outcome_field_to_state(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(self.root / "tools" / "pipeline_ledger.py"),
                "component",
                "--component",
                "watcher",
                "--status",
                "completed",
                "--cycle-id",
                "cycle-1",
                "--terminal-outcome",
                "EVALUATED_REJECTED",
                "--market-reason",
                "MARKET_OPEN",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        state = self.state()
        event = state.get("components", {}).get("watcher", {})
        self.assertEqual(event.get("terminal_outcome"), "EVALUATED_REJECTED")
        self.assertEqual(event.get("market_reason"), "MARKET_OPEN")
        summary = state.get("last_terminal_outcome", {})
        self.assertEqual(summary.get("terminal_outcome"), "EVALUATED_REJECTED")


class GatedCycleTerminalOutcomeTests(TemporaryBotARoot, unittest.TestCase):
    """End-to-end: watcher_gated_cycle.sh emits ONE terminal outcome per cycle."""

    SCENARIOS = (
        ("MARKET_CLOSED_SATURDAY", "MARKET_CLOSED", "skipped_market_closed"),
        ("MARKET_CLOSED_SUNDAY", "MARKET_CLOSED", "skipped_market_closed"),
        ("MARKET_CLOSED_FRIDAY_POST_2000", "MARKET_CLOSED", "skipped_market_closed"),
        ("MARKET_CLOSED_ASIAN_PRE_0700", "MARKET_CLOSED", "skipped_market_closed"),
        ("MARKET_CLOSED_POST_NY", "MARKET_CLOSED", "skipped_market_closed"),
        ("CLOCK_UNAVAILABLE", "CLOCK_GATE_FAILED", "failed"),
        ("MARKET_GATE_ERROR", "CLOCK_GATE_FAILED", "failed"),
        ("MARKET_OPEN", "EVALUATED_REJECTED", "completed"),
    )

    def _reset(self) -> None:
        for path in (
            self.root / "state" / "pipeline_progress.json",
            self.root / "logs" / "pipeline_events.jsonl",
        ):
            try:
                path.unlink()
            except FileNotFoundError:
                pass

    def test_every_scenario_emits_exactly_one_terminal_outcome(self) -> None:
        for hint, expected_terminal, expected_status in self.SCENARIOS:
            with self.subTest(hint=hint):
                self._reset()
                completed = self.run_gate(hint, dry_run=True)
                self.assertEqual(completed.returncode, 0, completed.stderr)
                event = self.state().get("components", {}).get("watcher", {})
                self.assertEqual(event.get("terminal_outcome"), expected_terminal)
                self.assertEqual(event.get("status"), expected_status)
                self.assertEqual(event.get("market_reason"), hint)

    def test_events_jsonl_contains_one_component_event_per_gate_hint(self) -> None:
        # A single gated cycle should append exactly two watcher-component
        # events: one "started" and one terminal event. This is the audit
        # contract we rely on to reconstruct history.
        self._reset()
        self.run_gate("MARKET_CLOSED_SUNDAY", dry_run=True)
        events_path = self.root / "logs" / "pipeline_events.jsonl"
        lines = [line for line in events_path.read_text().splitlines() if line.strip()]
        watcher_events = [
            json.loads(line)
            for line in lines
            if json.loads(line).get("component") == "watcher"
        ]
        self.assertEqual(len(watcher_events), 2)
        self.assertEqual(watcher_events[0]["status"], "started")
        self.assertEqual(watcher_events[-1]["status"], "skipped_market_closed")
        self.assertEqual(watcher_events[-1]["terminal_outcome"], "MARKET_CLOSED")

    def test_repeated_clock_gate_failed_updates_terminal_outcome(self) -> None:
        # Two failed cycles must both record the same terminal outcome; the
        # most recent one must overwrite the compact state without silently
        # dropping the failure classification.
        self._reset()
        self.run_gate("CLOCK_UNAVAILABLE", dry_run=True)
        first = self.state().get("components", {}).get("watcher", {}).get("event_id")
        self.run_gate("CLOCK_UNAVAILABLE", dry_run=True)
        second = self.state().get("components", {}).get("watcher", {})
        self.assertNotEqual(first, second.get("event_id"))
        self.assertEqual(second.get("terminal_outcome"), "CLOCK_GATE_FAILED")

    def test_canonical_production_root_refuses_fixture_dry_run(self) -> None:
        production_home = self.root / "production-home"
        production_root = production_home / "BotA"
        shutil.copytree(self.root / "tools", production_root / "tools")
        (production_root / "state").mkdir(parents=True)
        (production_root / "logs").mkdir(parents=True)

        env = os.environ.copy()
        env["HOME"] = str(production_home)
        env["BOTA_ROOT"] = str(production_root)
        env["WATCHER_GATED_MARKET_HINT"] = "MARKET_OPEN"
        env["WATCHER_GATED_DRY_RUN"] = "1"
        env.pop("BOTA_SERVER_EPOCH", None)

        completed = subprocess.run(
            ["bash", str(production_root / "tools" / "watcher_gated_cycle.sh")],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)

        state = json.loads(
            (production_root / "state" / "pipeline_progress.json").read_text()
        )
        watcher = state.get("components", {}).get("watcher", {})
        self.assertEqual(watcher.get("status"), "failed")
        self.assertEqual(watcher.get("terminal_outcome"), "INTERNAL_ERROR")
        self.assertIn("dry_run_refused_in_production=1", watcher.get("details", ""))


class HealthEvaluatorClockGateStuckTests(TemporaryBotARoot, unittest.TestCase):
    """Open-market CLOCK_GATE_FAILED must be flagged unhealthy."""

    def _seed_watcher(
        self,
        *,
        status: str,
        terminal: str,
        market_reason: str,
    ) -> None:
        # Seed updater and shadow first so the component freshness arm is
        # satisfied.
        for component in ("updater", "shadow"):
            subprocess.run(
                [
                    sys.executable,
                    str(self.root / "tools" / "pipeline_ledger.py"),
                    "component",
                    "--component",
                    component,
                    "--status",
                    "completed",
                    "--cycle-id",
                    "cycle-seed",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
        # Seed the three required decisions BEFORE the aggregated watcher
        # component event, mirroring watcher_gated_cycle.sh's real-world
        # ordering (per-pair reconciler events, then the aggregated cycle
        # outcome). Note: emitting a decision also overwrites
        # state.components.watcher, which is why the component event must
        # come last.
        for pair in ("EURUSD", "GBPUSD", "USDJPY"):
            subprocess.run(
                [
                    sys.executable,
                    str(self.root / "tools" / "pipeline_ledger.py"),
                    "decision",
                    "--pair",
                    pair,
                    "--timeframe",
                    "M15",
                    "--outcome",
                    "filter_rejected",
                    "--cycle-id",
                    "cycle-seed",
                    "--status",
                    "completed",
                    "--component",
                    "watcher",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
        subprocess.run(
            [
                sys.executable,
                str(self.root / "tools" / "pipeline_ledger.py"),
                "component",
                "--component",
                "watcher",
                "--status",
                status,
                "--cycle-id",
                "cycle-seed",
                "--terminal-outcome",
                terminal,
                "--market-reason",
                market_reason,
            ],
            capture_output=True,
            text=True,
            check=True,
        )

    def test_open_market_clock_gate_failed_is_unhealthy(self) -> None:
        self._seed_watcher(
            status="failed",
            terminal="CLOCK_GATE_FAILED",
            market_reason="CLOCK_UNAVAILABLE",
        )
        result = pipeline_health.evaluate(market_open=True)
        self.assertFalse(result["healthy"])
        self.assertTrue(
            any(
                "watcher_open_market_terminal_failure" in reason
                for reason in result["failure_reasons"]
            )
        )

    def test_closed_market_ignores_watcher_terminal_state(self) -> None:
        self._seed_watcher(
            status="failed",
            terminal="CLOCK_GATE_FAILED",
            market_reason="CLOCK_UNAVAILABLE",
        )
        result = pipeline_health.evaluate(market_open=False)
        self.assertTrue(result["healthy"], result["failure_reasons"])
        self.assertEqual(result["components"]["market"]["status"], "closed")

    def test_open_market_healthy_completed_cycle_is_healthy(self) -> None:
        self._seed_watcher(
            status="completed",
            terminal="EVALUATED_REJECTED",
            market_reason="MARKET_OPEN",
        )
        result = pipeline_health.evaluate(market_open=True)
        self.assertTrue(result["healthy"], result["failure_reasons"])
        self.assertEqual(
            result["components"]["watcher"]["terminal_outcome"],
            "EVALUATED_REJECTED",
        )


class DecisionBeforeDedupInvariantTests(unittest.TestCase):
    """Decision persistence must precede Telegram dedup — read the source.

    We assert against the source directly (not just runtime behavior) because
    a regression that swaps the two blocks will still emit a healthy-looking
    ledger in dry-run tests but destroys the ability to explain why a signal
    was suppressed.
    """

    def test_signal_watcher_persists_decision_before_dedup_check(self) -> None:
        boundary = (TOOLS / "signal_watcher_pro.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            'CORE="${TOOLS}/signal_watcher_core.sh"',
            boundary,
            "signal_watcher_pro.sh must select the reviewed watcher core",
        )
        self.assertIn(
            'exec bash "${CORE}" "$@"',
            boundary,
            "signal_watcher_pro.sh must delegate execution to its core",
        )

        source = (TOOLS / "signal_watcher_core.sh").read_text(
            encoding="utf-8"
        )
        # Locate the alerts.csv append and the dedup gate.
        append_marker = "append_alert_csv"
        dedup_markers = (
            "already delivered",
            "delivery dedup",
            "delivery_dedup",
            "hash is marked only after a successful real send",
        )
        self.assertIn(
            append_marker,
            source,
            "signal_watcher_core.sh must call append_alert_csv to persist decisions",
        )
        dedup_index = -1
        for marker in dedup_markers:
            index = source.find(marker)
            if index > dedup_index:
                dedup_index = index
        self.assertGreater(
            dedup_index,
            -1,
            "signal_watcher_core.sh must contain a Telegram delivery dedup gate",
        )
        # The last occurrence of append_alert_csv must appear before the
        # dedup marker; otherwise a decision could be dedup-suppressed
        # without ever being journaled.
        last_append = source.rfind(append_marker)
        self.assertLess(
            last_append,
            dedup_index,
            "decision persistence must happen before delivery dedup",
        )


if __name__ == "__main__":
    unittest.main()
