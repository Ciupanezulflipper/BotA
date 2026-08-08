#!/usr/bin/env python3
"""Regression tests for independent BotA -> ProfitLab delivery."""
from __future__ import annotations

import csv
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
WORKER = ROOT / "tools" / "profitlab_delivery.py"
PUBLISHER = ROOT / "tools" / "supabase_publish.py"
CANONICAL = ROOT / "ops" / "bota_crontab.canonical"
VERIFIER = ROOT / "tools" / "verify_canonical_crontab.sh"

HEADER = [
    "ts",
    "pair",
    "tf",
    "direction",
    "score",
    "confidence",
    "entry",
    "sl",
    "tp",
    "provider",
    "filter_rejected",
    "filter_reasons",
    "reasons",
    "ema_comp",
    "rsi_comp",
    "macd_comp",
    "adx_comp",
    "adx_raw",
    "rsi_raw",
    "macd_hist_raw",
    "macro6",
    "h1_trend",
    "tier",
    "session",
    "adx_regime",
]


def alert_row(
    *,
    pair: str = "EURUSD",
    direction: str = "BUY",
    score: str = "78.4",
    rejected: str = "false",
    tier: str = "GREEN",
) -> list[str]:
    return [
        "2026-08-10T12:00:00+0000",
        pair,
        "M15",
        direction,
        score,
        "80",
        "1.1000",
        "1.0950",
        "1.1100",
        "oanda",
        rejected,
        "none",
        "test",
        "",
        "",
        "",
        "",
        "25",
        "50",
        "0.1",
        "6",
        "up",
        tier,
        "London_NY_overlap",
        "trending",
    ]


def make_root(base: Path) -> tuple[Path, Path, Path]:
    root = base / "BotA"
    (root / "logs").mkdir(parents=True)
    (root / "state").mkdir(parents=True)
    (root / "tools").mkdir(parents=True)
    alerts = root / "logs" / "alerts.csv"
    with alerts.open("w", encoding="utf-8", newline="") as handle:
        csv.writer(handle).writerow(HEADER)

    publish_log = root / "publish.log"
    fake_publisher = root / "tools" / "fake_publisher.py"
    fake_publisher.write_text(
        """#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

log = Path(os.environ[\"PUBLISH_LOG\"])
with log.open(\"a\", encoding=\"utf-8\") as handle:
    handle.write(json.dumps(sys.argv[1:]) + \"\\n\")
sys.exit(1 if os.environ.get(\"PUBLISH_FAIL\") == \"1\" else 0)
""",
        encoding="utf-8",
    )
    return root, alerts, publish_log


def append_rows(alerts: Path, *rows: list[str]) -> None:
    with alerts.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerows(rows)


def run_worker(
    root: Path,
    publish_log: Path,
    *,
    bootstrap: bool = False,
    fail: bool = False,
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment.update(
        {
            "BOTA_ROOT": str(root),
            "PROFITLAB_PUBLISHER": str(root / "tools" / "fake_publisher.py"),
            "PUBLISH_LOG": str(publish_log),
            "PUBLISH_FAIL": "1" if fail else "0",
        }
    )
    command = [sys.executable, str(WORKER)]
    if bootstrap:
        command.append("--bootstrap")
    return subprocess.run(
        command,
        cwd=ROOT,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )


def state_offset(root: Path) -> int:
    state = json.loads(
        (root / "state" / "profitlab_delivery_cursor.json").read_text(
            encoding="utf-8"
        )
    )
    return int(state["offset"])


class ProfitLabWorkerTests(unittest.TestCase):
    def test_first_activation_bootstraps_without_replaying_history(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root, alerts, publish_log = make_root(Path(temporary))
            append_rows(alerts, alert_row())
            result = run_worker(root, publish_log, bootstrap=True)
            expected_offset = alerts.stat().st_size

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("PROFITLAB_DELIVERY_BOOTSTRAP=PASS", result.stdout)
            self.assertEqual(state_offset(root), expected_offset)
            self.assertFalse(publish_log.exists())

    def test_green_delivery_does_not_depend_on_telegram(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root, alerts, publish_log = make_root(Path(temporary))
            bootstrap = run_worker(root, publish_log, bootstrap=True)
            self.assertEqual(bootstrap.returncode, 0, bootstrap.stderr)

            append_rows(alerts, alert_row(pair="GBPUSD", direction="SELL"))
            result = run_worker(root, publish_log)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("PROFITLAB_DELIVERY=PASS pair=GBPUSD", result.stdout)
            calls = publish_log.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(calls), 1)
            args = json.loads(calls[0])
            self.assertIn("GBPUSD", args)
            self.assertIn("SELL", args)
            self.assertEqual(state_offset(root), alerts.stat().st_size)

        source = WORKER.read_text(encoding="utf-8")
        self.assertNotIn("TELEGRAM_", source)

    def test_rejected_and_non_green_rows_do_not_publish(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root, alerts, publish_log = make_root(Path(temporary))
            run_worker(root, publish_log, bootstrap=True)
            append_rows(
                alerts,
                alert_row(rejected="true", tier="GREEN"),
                alert_row(rejected="false", tier="YELLOW"),
            )
            result = run_worker(root, publish_log)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(publish_log.exists())
            self.assertEqual(state_offset(root), alerts.stat().st_size)

    def test_failed_publication_retries_same_row(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root, alerts, publish_log = make_root(Path(temporary))
            run_worker(root, publish_log, bootstrap=True)
            before = state_offset(root)
            append_rows(alerts, alert_row())

            failed = run_worker(root, publish_log, fail=True)
            self.assertEqual(failed.returncode, 1)
            self.assertIn("RETRY_REQUIRED", failed.stderr)
            self.assertEqual(state_offset(root), before)

            recovered = run_worker(root, publish_log, fail=False)
            self.assertEqual(recovered.returncode, 0, recovered.stderr)
            self.assertIn("PROFITLAB_DELIVERY=PASS", recovered.stdout)
            self.assertEqual(state_offset(root), alerts.stat().st_size)
            self.assertEqual(
                len(publish_log.read_text(encoding="utf-8").splitlines()),
                2,
            )

    def test_missing_state_bootstraps_instead_of_replaying(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root, alerts, publish_log = make_root(Path(temporary))
            append_rows(alerts, alert_row())
            result = run_worker(root, publish_log)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("PROFITLAB_DELIVERY_BOOTSTRAP=PASS", result.stdout)
            self.assertFalse(publish_log.exists())
            self.assertEqual(state_offset(root), alerts.stat().st_size)


class FakeResponse:
    def __init__(self, payload: bytes = b"") -> None:
        self.payload = payload

    def read(self) -> bytes:
        return self.payload

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, exc_type, exc, traceback) -> bool:
        return False


class SupabasePublisherTests(unittest.TestCase):
    def load_module(self):
        spec = importlib.util.spec_from_file_location("supabase_publish_test", PUBLISHER)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_existing_active_signal_is_idempotent_success(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            environment = {
                "BOTA_ROOT": str(Path(temporary) / "BotA"),
                "SUPABASE_SERVICE_KEY": "test-key",
            }
            with mock.patch.dict(os.environ, environment, clear=False):
                module = self.load_module()
                with mock.patch.object(
                    module.urllib.request,
                    "urlopen",
                    return_value=FakeResponse(b'[{"id":"existing"}]'),
                ) as urlopen:
                    ok = module.publish(
                        "EURUSD",
                        "BUY",
                        "1.1",
                        "1.09",
                        "1.12",
                        "78",
                        "M15",
                        "GREEN",
                    )

            self.assertTrue(ok)
            self.assertEqual(urlopen.call_count, 1)

    def test_dedup_query_failure_fails_closed_without_insert(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            environment = {
                "BOTA_ROOT": str(Path(temporary) / "BotA"),
                "SUPABASE_SERVICE_KEY": "test-key",
            }
            with mock.patch.dict(os.environ, environment, clear=False):
                module = self.load_module()
                with mock.patch.object(
                    module.urllib.request,
                    "urlopen",
                    side_effect=urllib.error.URLError("offline"),
                ) as urlopen:
                    ok = module.publish(
                        "EURUSD",
                        "BUY",
                        "1.1",
                        "1.09",
                        "1.12",
                        "78",
                        "M15",
                        "GREEN",
                    )

            self.assertFalse(ok)
            self.assertEqual(urlopen.call_count, 1)

    def test_new_signal_queries_then_inserts_expected_payload(self) -> None:
        requests = []

        def fake_urlopen(request, timeout=10):
            requests.append(request)
            if len(requests) == 1:
                return FakeResponse(b"[]")
            return FakeResponse()

        with tempfile.TemporaryDirectory() as temporary:
            environment = {
                "BOTA_ROOT": str(Path(temporary) / "BotA"),
                "SUPABASE_SERVICE_KEY": "test-key",
            }
            with mock.patch.dict(os.environ, environment, clear=False):
                module = self.load_module()
                with mock.patch.object(
                    module.urllib.request,
                    "urlopen",
                    side_effect=fake_urlopen,
                ):
                    ok = module.publish(
                        "GBPUSD",
                        "SELL",
                        "1.27",
                        "1.28",
                        "1.25",
                        "86",
                        "M15",
                        "GREEN",
                    )

        self.assertTrue(ok)
        self.assertEqual(len(requests), 2)
        payload = json.loads(requests[1].data.decode("utf-8"))
        self.assertEqual(payload["pair"], "GBPUSD")
        self.assertEqual(payload["direction"], "SELL")
        self.assertEqual(payload["signal_strength"], 5)
        self.assertEqual(payload["status"], "ACTIVE")
        self.assertEqual(payload["timeframe"], "M15")
        self.assertEqual(payload["min_tier"], "pro")


class ProfitLabScheduleTests(unittest.TestCase):
    def test_independent_worker_is_one_active_cron_job(self) -> None:
        lines = CANONICAL.read_text(encoding="utf-8").splitlines()
        matching = [line for line in lines if "profitlab_delivery.py" in line]
        self.assertEqual(len(matching), 1)
        self.assertFalse(matching[0].startswith("#"))
        self.assertTrue(matching[0].startswith("* * * * * "))
        self.assertNotIn("TELEGRAM_", matching[0])

    def test_verifier_requires_profitlab_worker(self) -> None:
        source = VERIFIER.read_text(encoding="utf-8")
        self.assertIn('"profitlab_delivery.py"', source)


if __name__ == "__main__":
    unittest.main()
