from __future__ import annotations

import contextlib
import csv
import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

HERE = Path(__file__).resolve().parents[1]


def load_module(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, HERE / relative)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


publisher = load_module("supabase_publish_cycle_test", "tools/supabase_publish.py")
ledger = load_module("watcher_cycle_ledger_cycle_test", "tools/watcher_cycle_ledger.py")


def current_row(*, pair="GBPUSD", direction="BUY", entry="1.35379", rejected="false", tier="GREEN"):
    values = [
        "2026-08-12T08:11:02-0400", pair, "M15", direction, "84.90", "84.90",
        entry, "1.35222", "1.35692", "engine_A3", rejected,
        "macro6=3 | H1_trend_confirmed", "ok|phase=Open", "4.9", "15.0", "15.0",
        "8.0", "28.1", "77.7", "0.000187", "3", "confirmed", tier,
        "London_NY_overlap", "trending",
    ]
    assert len(values) == 25
    return values


class PublisherStatusTests(unittest.TestCase):
    def test_non_green_status_preserves_boolean_api(self):
        ok, status = publisher.publish_with_status(
            "GBPUSD", "BUY", "1.1", "1.0", "1.2", "80", "M15", "YELLOW"
        )
        self.assertTrue(ok)
        self.assertEqual(status, "skipped_non_green")

    def test_missing_key_is_explicit_failure(self):
        with mock.patch.dict(os.environ, {"SUPABASE_SERVICE_KEY": ""}, clear=False):
            ok, status = publisher.publish_with_status(
                "GBPUSD", "BUY", "1.1", "1.0", "1.2", "80", "M15", "GREEN"
            )
        self.assertFalse(ok)
        self.assertEqual(status, "failed_missing_service_key")

    def test_existing_active_signal_is_not_mislabeled_published(self):
        with (
            mock.patch.object(publisher, "publication_lock", return_value=nullcontext()),
            mock.patch.object(publisher, "active_signal_exists", return_value=True),
            mock.patch.dict(os.environ, {"SUPABASE_SERVICE_KEY": "test-key"}, clear=False),
        ):
            ok, status = publisher.publish_with_status(
                "GBPUSD", "BUY", "1.1", "1.0", "1.2", "80", "M15", "GREEN"
            )
        self.assertTrue(ok)
        self.assertEqual(status, "skipped_active_exists")

    def test_successful_insert_is_published(self):
        with (
            mock.patch.object(publisher, "publication_lock", return_value=nullcontext()),
            mock.patch.object(publisher, "active_signal_exists", return_value=False),
            mock.patch.object(publisher, "insert_signal", return_value=True),
            mock.patch.dict(os.environ, {"SUPABASE_SERVICE_KEY": "test-key"}, clear=False),
        ):
            ok, status = publisher.publish_with_status(
                "GBPUSD", "BUY", "1.35379", "1.35222", "1.35692", "84", "M15", "GREEN"
            )
        self.assertTrue(ok)
        self.assertEqual(status, "published")

    def test_cycle_result_is_sanitized_jsonl(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "cycle.jsonl"
            path.touch(mode=0o600)
            with mock.patch.dict(os.environ, {publisher.RESULT_LOG_ENV: str(path)}, clear=False):
                self.assertTrue(publisher.emit_cycle_result(
                    pair="GBPUSD", direction="BUY", entry="1.35379", tf="M15",
                    tier="GREEN", status="published",
                ))
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["pair"], "GBPUSD")
            self.assertEqual(payload["timeframe"], "M15")
            self.assertEqual(payload["status"], "published")
            self.assertNotIn("key", payload)
            self.assertNotIn("token", payload)

    def test_boolean_publish_api_remains_compatible(self):
        with mock.patch.object(publisher, "publish_with_status", return_value=(True, "published")):
            self.assertTrue(publisher.publish("GBPUSD", "BUY", "1", "1", "1", "80", "M15", "GREEN"))


class ReconcilerSupabaseTests(unittest.TestCase):
    def setUp(self):
        self.run_patch = mock.patch.object(
            ledger.subprocess, "run",
            return_value=SimpleNamespace(returncode=0, stderr="", stdout=""),
        )
        self.run_patch.start()
        self.addCleanup(self.run_patch.stop)

    def _root(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        root = Path(td.name)
        (root / "logs").mkdir()
        (root / "tools").mkdir()
        return root

    def _write_cycle(self, root: Path, supabase_lines: list[str]):
        alerts = root / "logs" / "alerts.csv"
        with alerts.open("w", encoding="utf-8", newline="") as handle:
            csv.writer(handle).writerow(ledger.LEGACY_ALERT_FIELDS_13)
        offset = alerts.stat().st_size
        with alerts.open("a", encoding="utf-8", newline="") as handle:
            csv.writer(handle).writerow(current_row())
        log_path = root / "cycle.log"
        log_path.write_text(
            "[FILTER] GBPUSD M15 accepted score=84.90 conf=84.90 filters=macro6=3\n"
            "[TELEGRAM] SENT: via tools/telegram_send.sh\n"
            "[CHART] GBPUSD M15 chart sent\n",
            encoding="utf-8",
        )
        supabase = root / "supabase.jsonl"
        supabase.write_text("\n".join(supabase_lines) + ("\n" if supabase_lines else ""), encoding="utf-8")
        return offset, log_path, supabase

    def _run(self, root: Path, offset: int, log_path: Path, supabase: Path):
        argv = [
            "watcher_cycle_ledger.py", "--cycle-id", "boot:sb",
            "--alerts-offset", str(offset), "--log-path", str(log_path),
            "--supabase-result-path", str(supabase), "--server-epoch", "1786555048",
        ]
        env = {"BOTA_ROOT": str(root), "BOTA_REQUIRED_DECISIONS": "GBPUSD:M15"}
        output = io.StringIO()
        with (
            mock.patch.object(sys, "argv", argv),
            mock.patch.dict(os.environ, env, clear=False),
            contextlib.redirect_stdout(output),
        ):
            rc = ledger.main()
        return rc, json.loads(output.getvalue())

    def test_published_result_is_cycle_authoritative(self):
        root = self._root()
        result = json.dumps({
            "schema_version": "1.0", "pair": "GBPUSD", "timeframe": "M15",
            "direction": "BUY", "entry": "1.35379", "tier": "GREEN", "status": "published",
        })
        offset, log_path, supabase = self._write_cycle(root, [result])
        rc, payload = self._run(root, offset, log_path, supabase)
        self.assertEqual(rc, 0)
        self.assertEqual(payload["results"][0]["telegram"], "sent")
        self.assertEqual(payload["results"][0]["supabase"], "published")

    def test_active_existing_result_is_distinct_from_published(self):
        root = self._root()
        result = json.dumps({
            "pair": "GBPUSD", "timeframe": "M15", "direction": "BUY",
            "entry": "1.35379", "tier": "GREEN", "status": "skipped_active_exists",
        })
        offset, log_path, supabase = self._write_cycle(root, [result])
        rc, payload = self._run(root, offset, log_path, supabase)
        self.assertEqual(rc, 0)
        self.assertEqual(payload["results"][0]["supabase"], "skipped_active_exists")

    def test_failed_publish_is_recorded_failed_without_erasing_telegram(self):
        root = self._root()
        result = json.dumps({
            "pair": "GBPUSD", "timeframe": "M15", "direction": "BUY",
            "entry": "1.35379", "tier": "GREEN", "status": "failed_publish",
        })
        offset, log_path, supabase = self._write_cycle(root, [result])
        rc, payload = self._run(root, offset, log_path, supabase)
        self.assertEqual(rc, 0)
        self.assertEqual(payload["results"][0]["telegram"], "sent")
        self.assertEqual(payload["results"][0]["supabase"], "failed")

    def test_malformed_structured_result_fails_cycle_closed(self):
        root = self._root()
        offset, log_path, supabase = self._write_cycle(root, ["{not-json"])
        rc, payload = self._run(root, offset, log_path, supabase)
        self.assertEqual(rc, 3)
        self.assertFalse(payload["healthy"])
        self.assertEqual(payload["results"][0]["outcome"], "parse_error")

    def test_duplicate_structured_results_fail_before_normal_decision_commit(self):
        root = self._root()
        result = json.dumps({
            "pair": "GBPUSD", "timeframe": "M15", "direction": "BUY",
            "entry": "1.35379", "tier": "GREEN", "status": "published",
        })
        offset, log_path, supabase = self._write_cycle(root, [result, result])
        rc, payload = self._run(root, offset, log_path, supabase)
        self.assertEqual(rc, 3)
        self.assertFalse(payload["healthy"])
        self.assertEqual(payload["results"][0]["outcome"], "parse_error")
        self.assertFalse(payload["results"][0]["persisted"])


class SchemaAndWrapperContractTests(unittest.TestCase):
    def test_exact_legacy_schema_matches_phone_forensics(self):
        self.assertEqual(
            ledger.LEGACY_ALERT_FIELDS_13,
            ("timestamp", "pair", "tf", "direction", "score", "confidence", "entry", "sl", "tp",
             "provider", "rejected", "filter_str", "reasons"),
        )

    def test_exact_current_schema_matches_watcher_producer(self):
        self.assertEqual(ledger.CURRENT_ALERT_FIELDS_25[10], "filter_rejected")
        self.assertEqual(ledger.CURRENT_ALERT_FIELDS_25[12], "reasons")
        self.assertEqual(ledger.CURRENT_ALERT_FIELDS_25[-1], "adx_regime")
        self.assertEqual(len(ledger.CURRENT_ALERT_FIELDS_25), 25)

    def test_wrapper_owns_private_supabase_result_file(self):
        text = (HERE / "tools" / "run_signal_watcher_with_ledger.sh").read_text(encoding="utf-8")
        self.assertIn('supabase_result_log="$(mktemp', text)
        self.assertIn('export BOTA_SUPABASE_RESULT_LOG="${supabase_result_log}"', text)
        self.assertIn('--supabase-result-path "${supabase_result_log}"', text)


if __name__ == "__main__":
    unittest.main()
