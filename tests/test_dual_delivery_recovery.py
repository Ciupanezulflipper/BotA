#!/usr/bin/env python3
"""Dual-delivery (Telegram + Supabase/ProfitLab) sink-independence acceptance tests.

These are the local, no-network acceptance tests required by the BotA
execution-recovery contract (docs/BOTA_EXECUTION_RECOVERY_PRD_2026-09-27.md).
Every scenario below is proven with mocks/fakes/failure injection only; no
real Telegram or Supabase network access ever occurs. Natural production
delivery proof is a separate, later step and is explicitly out of scope here.
"""
from __future__ import annotations

import csv
import importlib.util
import io
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
TOOLS = REPO / "tools"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


profitlab_delivery = load_module("profitlab_delivery_ddr_test", TOOLS / "profitlab_delivery.py")
supabase_publish = load_module("supabase_publish_ddr_test", TOOLS / "supabase_publish.py")
telegram_delivery = load_module("telegram_delivery_ddr_test", TOOLS / "telegram_delivery.py")
vps = load_module("vps_orchestrator_ddr_test", TOOLS / "vps_orchestrator.py")

# signal_closer.py resolves its sibling module via a bare `import
# telegram_closure_delivery`. Import it here under its real module name
# first (with tools/ on sys.path) so signal_closer's import reuses the exact
# same module object from sys.modules -- otherwise mock.patch.object on one
# copy would silently miss the other.
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))
import telegram_closure_delivery  # noqa: E402 - see comment above
signal_closer = load_module("signal_closer_ddr_test", TOOLS / "signal_closer.py")

CORE_SOURCE = (TOOLS / "signal_watcher_core.sh").read_text(encoding="utf-8")

ALERT_FIELDS = profitlab_delivery.ALERT_FIELDS


def alert_row(**overrides: str) -> list[str]:
    base = {
        "ts": "2026-09-27T00:00:00+0000", "pair": "EURUSD", "tf": "M15", "direction": "BUY",
        "score": "84.90", "confidence": "80.00", "entry": "1.35379", "sl": "1.35222",
        "tp": "1.35692", "provider": "engine_A2", "filter_rejected": "false",
        "filter_reasons": "", "reasons": "", "ema_comp": "", "rsi_comp": "", "macd_comp": "",
        "adx_comp": "", "adx_raw": "", "rsi_raw": "", "macd_hist_raw": "", "macro6": "",
        "h1_trend": "", "tier": "GREEN", "session": "London", "adx_regime": "trending",
    }
    base.update(overrides)
    return [base[key] for key in ALERT_FIELDS]


def write_alerts_csv(path: Path, rows: list[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(ALERT_FIELDS)
        for row in rows:
            writer.writerow(row)


def install_stub_publisher(path: Path, *, exit_code: int = 0, marker: Path | None = None) -> None:
    lines = ["#!/usr/bin/env python3", "import sys"]
    if marker is not None:
        lines.append(f"open({str(marker)!r}, 'a').write(' '.join(sys.argv[1:]) + chr(10))")
    lines.append(f"raise SystemExit({exit_code})")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    path.chmod(0o755)


class ProfitLabIndependentOfTelegramTests(unittest.TestCase):
    """Requirement 1/2/4/5/7: ProfitLab delivery never depends on Telegram."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.alerts = self.root / "logs" / "alerts.csv"
        self.state = self.root / "state" / "cursor.json"
        self.lock = self.root / "state" / "cursor.lock"
        self.publisher = self.root / "publisher.py"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def env(self) -> dict[str, str]:
        return {
            "PROFITLAB_ALERTS_CSV": str(self.alerts),
            "PROFITLAB_DELIVERY_STATE": str(self.state),
            "PROFITLAB_DELIVERY_LOCK": str(self.lock),
            "PROFITLAB_PUBLISHER": str(self.publisher),
        }

    def bootstrap_at_header_only(self) -> None:
        """Establish the cursor at end-of-header, matching the real
        first-activation contract (never replay pre-existing rows), so the
        GREEN row appended afterwards is the exact new row under test."""
        write_alerts_csv(self.alerts, [])
        with mock.patch.dict(os.environ, self.env(), clear=False):
            self.assertEqual(profitlab_delivery.run(bootstrap=True), 0)

    def append_row(self, row: list[str]) -> None:
        with self.alerts.open("a", newline="", encoding="utf-8") as handle:
            csv.writer(handle).writerow(row)

    def test_module_has_no_telegram_coupling(self) -> None:
        source = (TOOLS / "profitlab_delivery.py").read_text(encoding="utf-8")
        for forbidden in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "api.telegram.org", "import telegram"):
            self.assertNotIn(forbidden, source)

    def test_green_row_is_published_with_no_telegram_involvement(self) -> None:
        self.bootstrap_at_header_only()
        self.append_row(alert_row())
        marker = self.root / "invoked.txt"
        install_stub_publisher(self.publisher, marker=marker)
        with mock.patch.dict(os.environ, self.env(), clear=False):
            rc = profitlab_delivery.run(bootstrap=False)
        self.assertEqual(rc, 0)
        self.assertTrue(marker.exists())
        self.assertIn("EURUSD", marker.read_text(encoding="utf-8"))

    def test_telegram_failure_does_not_block_profitlab_delivery(self) -> None:
        """A GREEN row reaches ProfitLab even though Telegram delivery for it
        never happened (no telegram_delivery state exists anywhere)."""
        self.bootstrap_at_header_only()
        self.append_row(alert_row())
        marker = self.root / "invoked.txt"
        install_stub_publisher(self.publisher, marker=marker)
        self.assertFalse((self.root / "state" / "telegram_delivery").exists())
        with mock.patch.dict(os.environ, self.env(), clear=False):
            rc = profitlab_delivery.run(bootstrap=False)
        self.assertEqual(rc, 0)
        self.assertTrue(marker.exists())

    def test_retry_after_publisher_failure_does_not_touch_telegram_and_does_not_skip_row(self) -> None:
        self.bootstrap_at_header_only()
        offset_before = json.loads(self.state.read_text(encoding="utf-8"))["offset"]
        self.append_row(alert_row())
        install_stub_publisher(self.publisher, exit_code=1)
        with mock.patch.dict(os.environ, self.env(), clear=False):
            first = profitlab_delivery.run(bootstrap=False)
        self.assertEqual(first, 1)
        cursor_after_failure = json.loads(self.state.read_text(encoding="utf-8"))
        self.assertEqual(cursor_after_failure["offset"], offset_before)

        marker = self.root / "invoked.txt"
        install_stub_publisher(self.publisher, marker=marker)
        with mock.patch.dict(os.environ, self.env(), clear=False):
            second = profitlab_delivery.run(bootstrap=False)
        self.assertEqual(second, 0)
        self.assertTrue(marker.exists())
        self.assertEqual(marker.read_text(encoding="utf-8").count("EURUSD"), 1)

    def test_restart_replay_does_not_duplicate_profitlab_publish(self) -> None:
        self.bootstrap_at_header_only()
        self.append_row(alert_row())
        marker = self.root / "invoked.txt"
        install_stub_publisher(self.publisher, marker=marker)
        with mock.patch.dict(os.environ, self.env(), clear=False):
            self.assertEqual(profitlab_delivery.run(bootstrap=False), 0)
            second = profitlab_delivery.run(bootstrap=False)
        self.assertEqual(second, 0)
        self.assertEqual(marker.read_text(encoding="utf-8").count("EURUSD"), 1)

    def test_rejected_and_non_green_rows_never_reach_profitlab(self) -> None:
        for row in (
            alert_row(filter_rejected="true"),
            alert_row(tier="YELLOW"),
            alert_row(tier="LOW"),
            alert_row(direction="HOLD"),
        ):
            self.assertFalse(profitlab_delivery.eligible(dict(zip(ALERT_FIELDS, row))))


class SupabaseDedupIndependentTests(unittest.TestCase):
    """Requirement 6: Supabase-side dedup is correct on its own, without Telegram."""

    def test_active_signal_exists_short_circuits_insert(self) -> None:
        with mock.patch.object(supabase_publish, "active_signal_exists", return_value=True), \
             mock.patch.object(supabase_publish, "insert_signal") as insert, \
             mock.patch.dict(os.environ, {"SUPABASE_SERVICE_KEY": "k"}, clear=False):
            ok, status = supabase_publish.publish_with_status(
                "EURUSD", "BUY", "1.1", "1.0", "1.2", 84, "M15", "GREEN"
            )
        insert.assert_not_called()
        self.assertTrue(ok)
        self.assertEqual(status, "skipped_active_exists")

    def test_dedup_check_failure_fails_closed_without_inserting(self) -> None:
        with mock.patch.object(supabase_publish, "active_signal_exists", return_value=None), \
             mock.patch.object(supabase_publish, "insert_signal") as insert, \
             mock.patch.dict(os.environ, {"SUPABASE_SERVICE_KEY": "k"}, clear=False):
            ok, status = supabase_publish.publish_with_status(
                "EURUSD", "BUY", "1.1", "1.0", "1.2", 84, "M15", "GREEN"
            )
        insert.assert_not_called()
        self.assertFalse(ok)
        self.assertEqual(status, "failed_dedup_check")

    def test_non_green_tier_never_publishes(self) -> None:
        with mock.patch.object(supabase_publish, "insert_signal") as insert:
            ok, status = supabase_publish.publish_with_status(
                "EURUSD", "BUY", "1.1", "1.0", "1.2", 50, "M15", "YELLOW"
            )
        insert.assert_not_called()
        self.assertTrue(ok)
        self.assertEqual(status, "skipped_non_green")


class TelegramDedupAndRestartTests(unittest.TestCase):
    """Requirement 5/6: Telegram-side dedup/restart safety, independent of ProfitLab."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.alerts = self.root / "logs" / "alerts.csv"
        self.delivery_state = self.root / "logs" / "state"
        self.delivery_state.mkdir(parents=True)
        row = alert_row()
        write_alerts_csv(self.alerts, [row])
        self.message = (
            "\U0001f7e2 BotA EURUSD M15 BUY\n━━━━━━━━━━━━━━\n"
            "\U0001f4ca Score: 84.90 | Confidence: 80.00\n\U0001f4b0 Entry: 1.35379\n"
            "\U0001f6d1 SL: 1.35222\n\U0001f3af TP: 1.35692"
        )
        self.env = mock.patch.dict(
            os.environ,
            {
                "BOTA_ROOT": str(self.root),
                "BOTA_MUTABLE_ROOT": str(self.root),
                "BOTA_ALERTS_OFFSET": "0",
                "BOTA_DELIVERY_STATE_DIR": str(self.delivery_state),
                "TELEGRAM_BOT_TOKEN": "token",
                "TELEGRAM_CHAT_ID": "chat",
            },
            clear=False,
        )
        self.env.start()

    def tearDown(self) -> None:
        self.env.stop()
        self.tmp.cleanup()

    def test_second_call_after_confirmed_send_does_not_resend(self) -> None:
        with mock.patch.object(telegram_delivery, "send_request",
                                return_value=("sent", {"message_id": 1, "telegram_date": 1})) as send:
            rc1 = telegram_delivery.deliver(self.message)
        self.assertEqual(rc1, 0)
        send.assert_called_once()

        with mock.patch.object(telegram_delivery, "send_request",
                                side_effect=AssertionError("must not resend")) as send2:
            rc2 = telegram_delivery.deliver(self.message)
        self.assertEqual(rc2, telegram_delivery.RECONCILED_SENT_RC)
        send2.assert_not_called()

    def test_unknown_outcome_is_never_blindly_resent(self) -> None:
        with mock.patch.object(telegram_delivery, "send_request", return_value=("unknown_outcome", {})):
            rc1 = telegram_delivery.deliver(self.message)
        self.assertEqual(rc1, telegram_delivery.UNKNOWN_OUTCOME_RC)

        with mock.patch.object(telegram_delivery, "send_request",
                                side_effect=AssertionError("must not resend")) as send2:
            rc2 = telegram_delivery.deliver(self.message)
        self.assertEqual(rc2, telegram_delivery.UNKNOWN_OUTCOME_RC)
        send2.assert_not_called()


class WatcherOrderingStructuralTests(unittest.TestCase):
    """Requirement 3/7: Telegram send precedes and is never gated by Supabase,
    and rejected/non-qualified decisions never reach a network sink."""

    def test_telegram_send_precedes_supabase_publish_call(self) -> None:
        process_pair_tf = CORE_SOURCE[CORE_SOURCE.index("process_pair_tf() {"):CORE_SOURCE.index("scan_once() {")]
        telegram_call = process_pair_tf.index('send_telegram_message "${msg}"')
        supabase_call = process_pair_tf.index("complete_delivery_transaction")
        self.assertLess(telegram_call, supabase_call)

    def test_rejected_decision_returns_before_any_telegram_or_supabase_call(self) -> None:
        process_pair_tf = CORE_SOURCE[CORE_SOURCE.index("process_pair_tf() {"):CORE_SOURCE.index("scan_once() {")]
        rejected_guard = process_pair_tf.index('if [[ "${rejected}" == "true" ]]; then')
        telegram_call = process_pair_tf.index('send_telegram_message "${msg}"')
        supabase_call = process_pair_tf.index("complete_delivery_transaction")
        self.assertLess(rejected_guard, telegram_call)
        self.assertLess(rejected_guard, supabase_call)

    def test_complete_delivery_transaction_source_never_references_telegram(self) -> None:
        start = CORE_SOURCE.index("complete_delivery_transaction() {")
        end = CORE_SOURCE.index("raw_cache_path() {")
        body = CORE_SOURCE[start:end]
        self.assertNotIn("telegram", body.lower())


class ClosureLifecycleIndependenceTests(unittest.TestCase):
    """Requirement 8: SL/TP closure fans out to Telegram and ProfitLab independently."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.env = mock.patch.dict(
            os.environ,
            {"BOTA_MUTABLE_ROOT": str(self.root), "BOTA_ROOT": str(self.root),
             "TELEGRAM_BOT_TOKEN": "token", "TELEGRAM_CHAT_ID": "chat"},
            clear=False,
        )
        self.env.start()

    def tearDown(self) -> None:
        self.env.stop()
        self.tmp.cleanup()

    def test_telegram_closure_attempted_even_when_supabase_close_raises(self) -> None:
        with mock.patch.object(signal_closer, "supabase_request", side_effect=OSError("network down")), \
             mock.patch.object(telegram_closure_delivery, "_send_request",
                                return_value=("sent", {"message_id": 5})) as send:
            signal_closer.close_signal("sig-1", "CLOSED", 12.3, dry_run=False, closed_at_iso="2026-09-27T00:00:00Z")
            signal_closer.notify_closure_telegram("sig-1", "EURUSD", "BUY", "CLOSED", 12.3, 1.1, dry_run=False)
        send.assert_called_once()
        state = json.loads((self.root / "state" / "telegram_closure" / "sig-1.json").read_text(encoding="utf-8"))
        self.assertEqual(state["status"], "sent")

    def test_profitlab_closure_unaffected_by_telegram_failure(self) -> None:
        calls: list[tuple[str, str, dict | None]] = []

        def fake_request(method: str, path: str, body: dict | None = None):
            calls.append((method, path, body))
            return {}

        with mock.patch.object(signal_closer, "supabase_request", side_effect=fake_request), \
             mock.patch.object(telegram_closure_delivery, "_send_request",
                                side_effect=AssertionError("network must not be hit")):
            signal_closer.close_signal("sig-2", "CLOSED", -5.0, dry_run=False, closed_at_iso="2026-09-27T00:00:00Z")
            signal_closer.notify_closure_telegram(
                "sig-2", "EURUSD", "SELL", "CLOSED", -5.0, 1.1, dry_run=False
            )
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][0], "PATCH")
        self.assertIn("sig-2", calls[0][1])

    def test_closure_telegram_dedup_prevents_resend_on_retry(self) -> None:
        with mock.patch.object(telegram_closure_delivery, "_send_request",
                                return_value=("sent", {"message_id": 9})) as send:
            first = telegram_closure_delivery.send_closure("sig-3", "EURUSD", "BUY", "CLOSED", 4.0, 1.1)
        self.assertTrue(first)
        send.assert_called_once()

        with mock.patch.object(telegram_closure_delivery, "_send_request",
                                side_effect=AssertionError("must not resend")) as send2:
            second = telegram_closure_delivery.send_closure("sig-3", "EURUSD", "BUY", "CLOSED", 4.0, 1.1)
        self.assertTrue(second)
        send2.assert_not_called()

    def test_missing_credentials_skips_cleanly_without_raising(self) -> None:
        with mock.patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "", "TELEGRAM_CHAT_ID": ""}, clear=False):
            result = telegram_closure_delivery.send_closure("sig-4", "EURUSD", "BUY", "CLOSED", 1.0, 1.1)
        self.assertFalse(result)


class R5JobScopingTests(unittest.TestCase):
    """Requirement 9: only the four approved delivery jobs may bypass R5 shadow;
    every other job's environment is untouched (still bounded/suppressed)."""

    APPROVED = frozenset({"watcher", "profitlab_delivery", "closer", "daily_summary_server_gate"})

    def test_exactly_the_four_approved_jobs_carry_the_r5_bypass_override(self) -> None:
        jobs = {job.name: job for job in vps.production_jobs()}
        for name, job in jobs.items():
            if name in self.APPROVED:
                self.assertEqual(dict(job.env_overrides), vps.R5_LIVE_DELIVERY_ENV, name)
            elif name == "updater":
                self.assertEqual(dict(job.env_overrides), vps.UPDATER_ENV, name)
            else:
                self.assertEqual(job.env_overrides, (), name)

    def test_unrelated_jobs_reject_the_r5_bypass_override(self) -> None:
        for name in ("heartbeat", "market_pulse", "runtime_health_push", "shadow"):
            with self.assertRaises(vps.ContractError):
                vps.Job(name, (("true",),), vps.EVERY_MINUTE, 1,
                        env_overrides=tuple(vps.R5_LIVE_DELIVERY_ENV.items()))

    def test_approved_job_still_rejects_an_unrelated_override(self) -> None:
        with self.assertRaises(vps.ContractError):
            vps.Job("watcher", (("true",),), vps.EVERY_MINUTE, 1,
                    env_overrides=(("TELEGRAM_ENABLED", "0"),))

    def test_child_env_for_approved_job_disables_r5_ambient_flags(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            mutable = Path(td)
            orch = vps.Orchestrator(REPO, mutable, ())
            jobs = {job.name: job for job in vps.production_jobs()}
            with mock.patch.dict(os.environ, {"BOTA_R5_SHADOW": "1", "BOTA_REQUIRE_R5_SHADOW": "1"}):
                watcher_env = orch.child_env(jobs["watcher"])
                heartbeat_env = orch.child_env(jobs["heartbeat"])
            self.assertEqual(watcher_env["BOTA_R5_SHADOW"], "0")
            self.assertEqual(watcher_env["BOTA_REQUIRE_R5_SHADOW"], "0")
            self.assertEqual(heartbeat_env["BOTA_R5_SHADOW"], "1")
            self.assertEqual(heartbeat_env["BOTA_REQUIRE_R5_SHADOW"], "1")


if __name__ == "__main__":
    unittest.main()
