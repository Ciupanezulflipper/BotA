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
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

HERE = Path(__file__).resolve().parents[1]
MODULE_PATH = HERE / "tools" / "watcher_cycle_ledger.py"
spec = importlib.util.spec_from_file_location("watcher_cycle_ledger", MODULE_PATH)
ledger = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(ledger)


def row25(*, pair="GBPUSD", direction="HOLD", score="0.00", rejected="true", entry="0.00000"):
    values = [
        "2026-08-12T12:17:21-0400", pair, "M15", direction, score, "40.00",
        entry, "0.00000", "0.00000", "engine_A3", rejected,
        "direction_not_tradeable | score<65", "no_signal|phase=Open",
        "", "", "", "", "", "", "", "3", "", "LOW", "NY", "ranging",
    ]
    assert len(values) == 25
    return values


class CsvSchemaRegressionTests(unittest.TestCase):
    def _write(self, header, rows):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        path = Path(td.name) / "alerts.csv"
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(header)
        offset = path.stat().st_size
        with path.open("a", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            for row in rows:
                writer.writerow(row)
        return path, offset

    def test_legacy_13_header_plus_current_25_rejected_hold_stays_rejected(self):
        path, offset = self._write(ledger.LEGACY_ALERT_FIELDS_13, [row25()])
        rows = ledger.parse_new_rows(path, offset)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["pair"], "GBPUSD")
        self.assertEqual(rows[0]["direction"], "HOLD")
        self.assertTrue(ledger.normalized_rejected(rows[0]))
        self.assertEqual(rows[0]["tier"], "LOW")

    def test_canonical_25_header_and_nonrejected_buy(self):
        row = row25(direction="BUY", score="84.90", rejected="false", entry="1.35379")
        path, offset = self._write(ledger.CANONICAL_ALERT_FIELDS_25, [row])
        rows = ledger.parse_new_rows(path, offset)
        self.assertEqual(len(rows), 1)
        self.assertFalse(ledger.normalized_rejected(rows[0]))
        self.assertEqual(rows[0]["entry"], "1.35379")

    def test_pure_legacy_13_row_rejected_true(self):
        row = [
            "2026-08-12T12:17:21-0400", "GBPUSD", "M15", "HOLD", "0.00", "40.00",
            "0", "0", "0", "engine_A3", "true", "score<65", "no_signal",
        ]
        path, offset = self._write(ledger.LEGACY_ALERT_FIELDS_13, [row])
        rows = ledger.parse_new_rows(path, offset)
        self.assertEqual(len(rows), 1)
        self.assertTrue(ledger.normalized_rejected(rows[0]))

    def test_malformed_width_is_surfaced_fail_closed(self):
        path, offset = self._write(ledger.LEGACY_ALERT_FIELDS_13, [["bad", "GBPUSD", "M15"]])
        rows = ledger.parse_new_rows(path, offset)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["_malformed"], "true")
        self.assertEqual(rows[0]["pair"], "GBPUSD")
        self.assertEqual(rows[0]["tf"], "M15")


class ClassificationRegressionTests(unittest.TestCase):
    def setUp(self):
        self.run_patch = mock.patch.object(
            ledger.subprocess,
            "run",
            return_value=SimpleNamespace(returncode=0, stderr="", stdout=""),
        )
        self.run_patch.start()
        self.addCleanup(self.run_patch.stop)

    def test_rejected_row_overrides_misleading_accepted_log(self):
        row = dict(zip(ledger.CANONICAL_ALERT_FIELDS_25, row25(), strict=True))
        result = ledger.ledger_decision(
            cycle_id="boot:1", server_epoch=1786555048,
            pair="GBPUSD", timeframe="M15", row=row,
            lines=["[FILTER] GBPUSD M15 accepted score=84.90"],
        )
        self.assertEqual(result["outcome"], "filter_rejected")

    def test_exact_cycle_log_path_beats_stale_global_log(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "logs").mkdir()
            (root / "tools").mkdir()
            alerts = root / "logs" / "alerts.csv"
            stale = root / "logs" / "cron.signals.log"
            current = root / "state-current.log"

            with alerts.open("w", encoding="utf-8", newline="") as handle:
                csv.writer(handle).writerow(ledger.CANONICAL_ALERT_FIELDS_25)
            offset = alerts.stat().st_size
            with alerts.open("a", encoding="utf-8", newline="") as handle:
                csv.writer(handle).writerow(
                    row25(direction="BUY", score="84.90", rejected="false", entry="1.35379")
                )

            stale.write_text(
                "[FILTER] GBPUSD M15 rejected_by_filter score=0 filters=stale\n",
                encoding="utf-8",
            )
            current.write_text(
                "[CLOCK] server_clock_ok BOTA_SERVER_EPOCH=1786555048\n"
                "[FILTER 2026-08-12T08:11:02-0400] GBPUSD M15 accepted score=84.90 conf=84.90 filters=macro6=3\n"
                "[TELEGRAM 2026-08-12T08:11:03-0400] SENT: via tools/telegram_send.sh\n"
                "[CHART 2026-08-12T08:11:04-0400] GBPUSD M15 chart sent\n",
                encoding="utf-8",
            )

            argv = [
                "watcher_cycle_ledger.py", "--cycle-id", "boot:2",
                "--alerts-offset", str(offset), "--log-path", str(current),
                "--log-offset", "0", "--server-epoch", "1786555048",
            ]
            env = {"BOTA_ROOT": str(root), "BOTA_REQUIRED_DECISIONS": "GBPUSD:M15"}
            output = io.StringIO()
            with (
                mock.patch.object(sys, "argv", argv),
                mock.patch.dict(os.environ, env, clear=False),
                contextlib.redirect_stdout(output),
            ):
                rc = ledger.main()
            payload = json.loads(output.getvalue())
            self.assertEqual(rc, 0)
            self.assertTrue(payload["healthy"])
            self.assertEqual(payload["results"][0]["outcome"], "telegram_sent")
            self.assertEqual(payload["results"][0]["telegram"], "sent")

    def test_any_malformed_appended_row_prevents_accepting_earlier_valid_row(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "logs").mkdir()
            (root / "tools").mkdir()
            alerts = root / "logs" / "alerts.csv"
            current = root / "current.log"
            with alerts.open("w", encoding="utf-8", newline="") as handle:
                csv.writer(handle).writerow(ledger.LEGACY_ALERT_FIELDS_13)
            offset = alerts.stat().st_size
            with alerts.open("a", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(row25(direction="BUY", score="84.90", rejected="false", entry="1.35379"))
                writer.writerow(["broken", "GBPUSD", "M15"])
            current.write_text(
                "[FILTER] GBPUSD M15 accepted score=84.90 conf=84.90 filters=macro6=3\n",
                encoding="utf-8",
            )
            argv = [
                "watcher_cycle_ledger.py", "--cycle-id", "boot:3",
                "--alerts-offset", str(offset), "--log-path", str(current),
                "--server-epoch", "1786555048",
            ]
            env = {"BOTA_ROOT": str(root), "BOTA_REQUIRED_DECISIONS": "GBPUSD:M15"}
            output = io.StringIO()
            with (
                mock.patch.object(sys, "argv", argv),
                mock.patch.dict(os.environ, env, clear=False),
                contextlib.redirect_stdout(output),
            ):
                rc = ledger.main()
            payload = json.loads(output.getvalue())
            self.assertEqual(rc, 3)
            self.assertFalse(payload["healthy"])
            self.assertEqual(payload["results"][0]["outcome"], "parse_error")
            self.assertFalse(payload["results"][0]["persisted"])


class WrapperContractTests(unittest.TestCase):
    def test_wrapper_uses_one_exact_cycle_log_for_watcher_and_reconciler(self):
        text = (HERE / "tools" / "run_signal_watcher_with_ledger.sh").read_text(encoding="utf-8")
        self.assertIn('2>"${cycle_log}"', text)
        self.assertIn('--log-path "${cycle_log}"', text)
        self.assertIn('cat "${cycle_log}" >&2', text)
        self.assertNotIn('watcher_log="${LOGS}/cron.signals.log"', text)


if __name__ == "__main__":
    unittest.main()
