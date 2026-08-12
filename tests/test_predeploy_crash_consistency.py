from __future__ import annotations

import csv
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parents[1]


def load_module(name: str, relative: str):
    path = HERE / relative
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    if spec.loader is None:
        raise RuntimeError(f"missing loader for {relative}")
    spec.loader.exec_module(module)
    return module


telegram = load_module("telegram_delivery", "tools/telegram_delivery.py")
persist = load_module("watcher_persistence_gate", "tools/watcher_persistence_gate.py")
control = load_module("control_plane_status", "tools/control_plane_status.py")


def canonical_row(*, pair="GBPUSD", direction="BUY", score="84.90", entry="1.35379", rejected="false"):
    return [
        "2026-08-12T08:11:02-0400", pair, "M15", direction, score, score,
        entry, "1.35222", "1.35692", "engine_A3", rejected, "macro6=3",
        "ok|phase=Open", "4.9", "15.0", "15.0", "8.0", "28.1", "77.7",
        "0.000187", "3", "confirmed", "GREEN", "London_NY_overlap", "trending",
    ]


class TelegramCrashConsistencyTests(unittest.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.root = Path(td.name)
        (self.root / "logs").mkdir()
        (self.root / "state").mkdir()
        alerts = self.root / "logs" / "alerts.csv"
        with alerts.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(telegram.CURRENT_FIELDS)
            writer.writerow(canonical_row())
        self.env = {
            "BOTA_ROOT": str(self.root),
            "TELEGRAM_BOT_TOKEN": "test-token",
            "TELEGRAM_CHAT_ID": "123",
        }
        self.message = (
            "🟢 BotA GBPUSD M15 BUY\\n"
            "📊 Score: 84.90 | macro6=3\\n"
            "💰 Entry: 1.35379\\n"
            "🛑 SL: 1.35222  🎯 TP: 1.35692"
        )

    def test_blocks_external_send_when_decision_not_persisted(self):
        (self.root / "logs" / "alerts.csv").write_text(
            ",".join(telegram.CURRENT_FIELDS) + "\n", encoding="utf-8"
        )
        with mock.patch.object(telegram, "send_request") as send:
            with mock.patch.dict(os.environ, self.env, clear=False):
                rc = telegram.deliver(self.message)
        self.assertEqual(rc, 65)
        send.assert_not_called()

    def test_success_persists_authoritative_message_id(self):
        with mock.patch.object(
            telegram, "send_request", return_value=("sent", {"message_id": 7812, "telegram_date": 1786540291})
        ) as send:
            with mock.patch.dict(os.environ, self.env, clear=False):
                rc = telegram.deliver(self.message)
        self.assertEqual(rc, 0)
        send.assert_called_once()
        state_files = list((self.root / "state" / "telegram_delivery").glob("*.json"))
        self.assertEqual(len(state_files), 1)
        state = json.loads(state_files[0].read_text(encoding="utf-8"))
        self.assertEqual(state["status"], "sent")
        self.assertEqual(state["message_id"], 7812)

    def test_unknown_outcome_never_blindly_resends(self):
        with mock.patch.object(telegram, "send_request", return_value=("unknown_outcome", {})) as first:
            with mock.patch.dict(os.environ, self.env, clear=False):
                rc1 = telegram.deliver(self.message)
        self.assertEqual(rc1, 75)
        first.assert_called_once()

        with mock.patch.object(telegram, "send_request") as second:
            with mock.patch.dict(os.environ, self.env, clear=False):
                rc2 = telegram.deliver(self.message)
        self.assertEqual(rc2, 75)
        second.assert_not_called()
        state_file = next((self.root / "state" / "telegram_delivery").glob("*.json"))
        state = json.loads(state_file.read_text(encoding="utf-8"))
        self.assertEqual(state["status"], "unknown_outcome")

    def test_definite_rejection_is_retryable(self):
        with mock.patch.object(
            telegram, "send_request", return_value=("definite_failure", {"http_status": 429})
        ):
            with mock.patch.dict(os.environ, self.env, clear=False):
                self.assertEqual(telegram.deliver(self.message), 1)
        with mock.patch.object(
            telegram, "send_request", return_value=("sent", {"message_id": 99, "telegram_date": 1})
        ) as retry:
            with mock.patch.dict(os.environ, self.env, clear=False):
                self.assertEqual(telegram.deliver(self.message), 0)
        retry.assert_called_once()


class PersistenceGateTests(unittest.TestCase):
    def _fixture(self, *, rows, log_text):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        root = Path(td.name)
        alerts = root / "alerts.csv"
        with alerts.open("w", encoding="utf-8", newline="") as handle:
            csv.writer(handle).writerow(persist.CURRENT_FIELDS)
        offset = alerts.stat().st_size
        with alerts.open("a", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            for row in rows:
                writer.writerow(row)
        log = root / "cycle.log"
        log.write_text(log_text, encoding="utf-8")
        return alerts, offset, log

    def test_rejected_evaluation_requires_persisted_row(self):
        alerts, offset, log = self._fixture(
            rows=[],
            log_text="[FILTER] GBPUSD M15 rejected_by_filter score=0 filters=score<65\n",
        )
        required = persist.expected_evaluated(log.read_text())
        persisted, malformed = persist.parse_pairs(persist.read_segment(alerts, offset))
        self.assertEqual(required, {("GBPUSD", "M15")})
        self.assertFalse(malformed)
        self.assertEqual(required - persisted, {("GBPUSD", "M15")})

    def test_pre_evaluation_stale_gate_does_not_require_row(self):
        alerts, offset, log = self._fixture(
            rows=[],
            log_text="[STALE] GBPUSD M15 candle_stale age=9999s max=2700s -> SKIP\n",
        )
        self.assertEqual(persist.expected_evaluated(log.read_text()), set())
        persisted, malformed = persist.parse_pairs(persist.read_segment(alerts, offset))
        self.assertEqual(persisted, set())
        self.assertFalse(malformed)

    def test_valid_evaluation_row_satisfies_gate(self):
        alerts, offset, log = self._fixture(
            rows=[canonical_row()],
            log_text="[FILTER] GBPUSD M15 accepted score=84.90 conf=84.90 filters=macro6=3\n",
        )
        required = persist.expected_evaluated(log.read_text())
        persisted, malformed = persist.parse_pairs(persist.read_segment(alerts, offset))
        self.assertFalse(malformed)
        self.assertTrue(required <= persisted)


class ControlPlaneZombieTests(unittest.TestCase):
    def test_basename_falls_back_to_comm_for_zombie(self):
        row = {"argv": [], "comm": "runsv", "state": "Z", "ppid": 26950}
        self.assertEqual(control.basename(row), "runsv")
        self.assertTrue(control.is_zombie(row))

    def test_zombie_runsv_is_reported_and_fails_health(self):
        table = {
            25219: {"argv": [], "comm": "runsv", "state": "Z", "ppid": 26950},
            26950: {
                "argv": ["runsvdir", "/data/data/com.termux/files/usr/var/service"],
                "comm": "runsvdir", "state": "S", "ppid": 1,
            },
        }
        zombies = control.zombie_runsv_processes(table)
        self.assertEqual([row["pid"] for row in zombies], [25219])
        rows = {
            name: {"service_running": True, "wrapper_alive": True, "runsv_pid": 1, "wrapper_pid": 2}
            for name in control.SERVICES
        }
        failures = control.topology_failures(
            1, len(control.SERVICES), len(control.SERVICES), 0, 0,
            zombies, rows, [{"pid": 2, "ppid": 1, "argv": ["crond","-n","-s"]}], 2, None,
        )
        self.assertIn("zombie_runsv_count:1", failures)


class WrapperHardeningTests(unittest.TestCase):
    def test_wrapper_enforces_persistence_and_retains_failed_evidence(self):
        text = (HERE / "tools" / "run_signal_watcher_with_ledger.sh").read_text(encoding="utf-8")
        self.assertIn("watcher_persistence_gate.py", text)
        self.assertIn("persistence_exit_code=", text)
        self.assertIn("delete_evidence_on_exit=0", text)
        self.assertIn("delete_evidence_on_exit=1", text)
        self.assertNotIn("assert ", text)

    def test_watcher_boundary_requires_canonical_sender(self):
        watcher = (HERE / "tools" / "signal_watcher_pro.sh").read_text(encoding="utf-8")
        wrapper = (HERE / "tools" / "run_signal_watcher_with_ledger.sh").read_text(encoding="utf-8")
        self.assertIn('${TOOLS}/telegram_send.sh', watcher)
        self.assertIn('chmod 700 "${TOOLS}/telegram_send.sh"', wrapper)
        self.assertIn('[[ ! -x "${TOOLS}/telegram_send.sh" ]]', wrapper)
        self.assertTrue((HERE / "tools" / "telegram_send.sh").is_file())
        self.assertTrue((HERE / "tools" / "telegram_delivery.py").is_file())


if __name__ == "__main__":
    unittest.main()