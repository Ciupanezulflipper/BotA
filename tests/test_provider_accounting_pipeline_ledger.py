from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
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


provider_usage = load_module("provider_usage_test", TOOLS / "provider_usage.py")
pipeline_ledger = load_module("pipeline_ledger_test", TOOLS / "pipeline_ledger.py")
pipeline_health = load_module("pipeline_health_test", TOOLS / "pipeline_health.py")
watcher_cycle = load_module("watcher_cycle_test", TOOLS / "watcher_cycle_ledger.py")


class TemporaryBotARootMixin:
    def setUp(self) -> None:
        super().setUp()
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "state").mkdir(parents=True)
        (self.root / "logs").mkdir(parents=True)
        self.env = mock.patch.dict(
            os.environ,
            {"BOTA_ROOT": str(self.root)},
            clear=False,
        )
        self.env.start()

    def tearDown(self) -> None:
        self.env.stop()
        self.temp.cleanup()
        super().tearDown()


class ProviderAccountingTests(TemporaryBotARootMixin, unittest.TestCase):
    @staticmethod
    def call(argv: list[str]) -> tuple[int, str]:
        output = StringIO()
        with redirect_stdout(output):
            rc = provider_usage.main(argv)
        return rc, output.getvalue()

    def state(self) -> dict:
        return json.loads(
            (self.root / "state" / "provider_usage.json").read_text()
        )

    def test_oanda_and_yahoo_never_consume_twelve_data_credits(self) -> None:
        for provider in ("oanda", "yahoo"):
            rc, _ = self.call(
                [
                    "record",
                    "--provider",
                    provider,
                    "--caller",
                    "test",
                    "--pair",
                    "EURUSD",
                    "--timeframe",
                    "M15",
                    "--status",
                    "success",
                    "--credits",
                    "0",
                ]
            )
            self.assertEqual(rc, 0)

        state = self.state()
        self.assertEqual(state["providers"]["oanda"]["credits_consumed"], 0)
        self.assertEqual(state["providers"]["yahoo"]["credits_consumed"], 0)
        self.assertNotIn("twelvedata", state["providers"])

    def test_non_twelve_data_credit_charge_is_rejected(self) -> None:
        with redirect_stdout(StringIO()):
            rc = provider_usage.main(
                [
                    "record",
                    "--provider",
                    "oanda",
                    "--caller",
                    "test",
                    "--status",
                    "success",
                    "--credits",
                    "1",
                ]
            )
        self.assertEqual(rc, 2)

    def test_twelve_data_reservation_stops_at_hard_cap(self) -> None:
        with mock.patch.dict(
            os.environ,
            {
                "TWELVE_DATA_DAILY_LIMIT": "800",
                "TWELVE_DATA_RESERVE_CREDITS": "100",
            },
            clear=False,
        ):
            rc, first = self.call(
                [
                    "reserve",
                    "--provider",
                    "twelvedata",
                    "--caller",
                    "test",
                    "--credits",
                    "700",
                ]
            )
            blocked_rc, blocked = self.call(
                [
                    "reserve",
                    "--provider",
                    "twelvedata",
                    "--caller",
                    "test",
                    "--credits",
                    "1",
                ]
            )
        self.assertEqual(rc, 0)
        self.assertTrue(json.loads(first)["allowed"])
        self.assertEqual(blocked_rc, 3)
        self.assertFalse(json.loads(blocked)["allowed"])
        self.assertEqual(
            self.state()["providers"]["twelvedata"]["credits_consumed"],
            700,
        )

    def test_legacy_generic_increment_is_disabled(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(TOOLS / "api_credit_tracker.py"),
                "increment",
                "1",
            ],
            text=True,
            capture_output=True,
            check=False,
            env={**os.environ, "BOTA_ROOT": str(self.root)},
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("provider_required", result.stderr)


class PipelineProgressTests(TemporaryBotARootMixin, unittest.TestCase):
    @staticmethod
    def ledger(argv: list[str]) -> int:
        with redirect_stdout(StringIO()):
            return pipeline_ledger.main(argv)

    def seed_healthy_progress(self) -> None:
        for component in ("updater", "shadow"):
            self.assertEqual(
                self.ledger(
                    [
                        "component",
                        "--component",
                        component,
                        "--status",
                        "completed",
                        "--cycle-id",
                        f"cycle-{component}",
                    ]
                ),
                0,
            )
        for pair in ("EURUSD", "GBPUSD"):
            self.assertEqual(
                self.ledger(
                    [
                        "decision",
                        "--component",
                        "watcher",
                        "--status",
                        "completed",
                        "--cycle-id",
                        "cycle-watcher",
                        "--pair",
                        pair,
                        "--timeframe",
                        "M15",
                        "--outcome",
                        "filter_rejected",
                        "--filter-rejected",
                        "true",
                    ]
                ),
                0,
            )

    def test_terminal_progress_and_decisions_are_healthy(self) -> None:
        self.seed_healthy_progress()
        result = pipeline_health.evaluate(market_open=True)
        self.assertTrue(result["healthy"], result["failure_reasons"])

    def test_old_started_event_is_not_reported_healthy(self) -> None:
        self.seed_healthy_progress()
        self.ledger(
            [
                "component",
                "--component",
                "updater",
                "--status",
                "started",
                "--cycle-id",
                "stuck-cycle",
            ]
        )
        path = self.root / "state" / "pipeline_progress.json"
        state = json.loads(path.read_text())
        state["components"]["updater"]["monotonic_ns"] -= 301 * 1_000_000_000
        path.write_text(json.dumps(state))
        with mock.patch.dict(
            os.environ,
            {"MAX_COMPONENT_START_GRACE_SECS": "300"},
        ):
            result = pipeline_health.evaluate(market_open=True)
        self.assertFalse(result["healthy"])
        self.assertEqual(
            result["components"]["updater"]["evaluation"],
            "stuck_started",
        )

    def test_market_closed_suspends_decision_freshness(self) -> None:
        state = pipeline_ledger.empty_state()
        (self.root / "state" / "pipeline_progress.json").write_text(
            json.dumps(state)
        )
        result = pipeline_health.evaluate(market_open=False)
        self.assertTrue(result["healthy"], result["failure_reasons"])


class WatcherCycleTests(unittest.TestCase):
    def test_server_epoch_is_taken_only_from_current_bounded_log(self) -> None:
        text = (
            "old unrelated line\n"
            "[CLOCK 2026-07-22T16:00:00Z] "
            "server_clock_ok BOTA_SERVER_EPOCH=1784736000\n"
        )
        self.assertEqual(
            watcher_cycle.trusted_server_epoch(0, text),
            1784736000,
        )
        self.assertEqual(
            watcher_cycle.trusted_server_epoch(1784737000, text),
            1784737000,
        )

    def test_filter_and_delivery_outcomes_are_terminal(self) -> None:
        outcome, telegram, _, rejection = watcher_cycle.log_outcome(
            [
                "[FILTER now] EURUSD M15 rejected_by_filter "
                "score=61 filters=adx_regime_block",
            ]
        )
        self.assertEqual(outcome, "filter_rejected")
        self.assertEqual(telegram, "not_attempted")
        self.assertEqual(rejection, "adx_regime_block")

        outcome, telegram, _, _ = watcher_cycle.log_outcome(
            [
                "[FILTER now] GBPUSD M15 accepted score=76 filters=ok",
                "[TELEGRAM now] SENT: via tools/telegram_send.sh",
            ]
        )
        self.assertEqual(outcome, "telegram_sent")
        self.assertEqual(telegram, "sent")

    def test_new_csv_parser_does_not_read_historical_rows(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "alerts.csv"
            historical = (
                "ts,pair,tf,score,filter_rejected\n"
                "old,EURUSD,M15,50,true\n"
            )
            path.write_text(historical)
            offset = path.stat().st_size
            with path.open("a") as handle:
                handle.write("new,GBPUSD,M15,70,false\n")
            rows = watcher_cycle.parse_new_rows(path, offset)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["pair"], "GBPUSD")


class SourceSafetyTests(unittest.TestCase):
    def test_old_false_credit_increment_is_removed(self) -> None:
        updater = (TOOLS / "indicators_updater.sh").read_text()
        self.assertNotIn("api_credit_tracker.py\" increment", updater)
        self.assertNotIn("api_credit_tracker.py increment", updater)

    def test_supervisor_does_not_start_detached_crond(self) -> None:
        supervisor = (TOOLS / "bota_supervisor.sh").read_text()
        self.assertNotIn("crond 2>/dev/null", supervisor)
        self.assertIn("SERVICE_MUTATION_PERFORMED=NO", supervisor)

    def test_fetcher_accounts_at_network_boundary(self) -> None:
        fetcher = (TOOLS / "data_fetch_candles.sh").read_text()
        self.assertIn("provider_record oanda success", fetcher)
        self.assertIn("provider_record oanda failure", fetcher)
        self.assertIn("provider_record yahoo blocked", fetcher)
        self.assertIn("provider_record yahoo success", fetcher)


if __name__ == "__main__":
    unittest.main()
