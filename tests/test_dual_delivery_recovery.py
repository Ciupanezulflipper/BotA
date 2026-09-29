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
import threading
import time
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


class ClosureRetryOutboxTests(unittest.TestCase):
    """Blocker 2 regression: a Supabase-confirmed closure whose Telegram send
    could not be confirmed must never be lost. Requirements 1-6 of the
    bounded repair spec."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.env = mock.patch.dict(
            os.environ,
            {"BOTA_MUTABLE_ROOT": str(self.root), "BOTA_ROOT": str(self.root)},
            clear=False,
        )
        self.env.start()

    def tearDown(self) -> None:
        self.env.stop()
        self.tmp.cleanup()

    def state_file(self, signal_id: str) -> Path:
        return self.root / "state" / "telegram_closure" / f"{signal_id}.json"

    def test_definite_failure_is_retried_and_sent_once_on_a_later_run(self) -> None:
        with mock.patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "t", "TELEGRAM_CHAT_ID": "c"}, clear=False):
            # Run 1: Supabase already closed the row (independent of this
            # sink); Telegram is definitively rejected.
            with mock.patch.object(telegram_closure_delivery, "_send_request",
                                    return_value=("definite_failure", {"http_status": 403})):
                first = telegram_closure_delivery.send_closure(
                    "sig-retry-1", "EURUSD", "BUY", "CLOSED", 7.5, 1.1
                )
            self.assertFalse(first)
            self.assertEqual(
                json.loads(self.state_file("sig-retry-1").read_text(encoding="utf-8"))["status"],
                "definite_failure",
            )

            # Run 2 (a later closer invocation, possibly with zero ACTIVE
            # signals): the retry scanner picks the durable payload back up.
            with mock.patch.object(telegram_closure_delivery, "_send_request",
                                    return_value=("sent", {"message_id": 99})) as send:
                summary = telegram_closure_delivery.retry_pending_closures()
            send.assert_called_once()
            self.assertEqual(summary, {"candidates": 1, "sent": 1, "skipped": 0})
            state = json.loads(self.state_file("sig-retry-1").read_text(encoding="utf-8"))
            self.assertEqual(state["status"], "sent")
            self.assertEqual(state["pair"], "EURUSD")
            self.assertEqual(state["result_pips"], 7.5)

            # A third run must not resend.
            with mock.patch.object(telegram_closure_delivery, "_send_request",
                                    side_effect=AssertionError("must not resend")):
                telegram_closure_delivery.retry_pending_closures()

    def test_missing_credentials_persist_durable_retry_state_until_credentials_appear(self) -> None:
        with mock.patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "", "TELEGRAM_CHAT_ID": ""}, clear=False):
            result = telegram_closure_delivery.send_closure(
                "sig-retry-2", "GBPUSD", "SELL", "CANCELLED", 0.0, 1.25
            )
        self.assertFalse(result)
        self.assertEqual(
            json.loads(self.state_file("sig-retry-2").read_text(encoding="utf-8"))["status"],
            "missing_credentials",
        )

        # Credentials remain absent: a retry scan must not attempt a send,
        # but the durable state survives.
        with mock.patch.object(telegram_closure_delivery, "_send_request",
                                side_effect=AssertionError("must not attempt without credentials")):
            summary = telegram_closure_delivery.retry_pending_closures()
        self.assertEqual(summary["sent"], 0)
        self.assertEqual(
            json.loads(self.state_file("sig-retry-2").read_text(encoding="utf-8"))["status"],
            "missing_credentials",
        )

        # Credentials later appear (e.g. the approved child's scoped
        # live-delivery secrets become available): the retry succeeds once.
        with mock.patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "t", "TELEGRAM_CHAT_ID": "c"}, clear=False), \
             mock.patch.object(telegram_closure_delivery, "_send_request",
                                return_value=("sent", {"message_id": 5})) as send:
            summary = telegram_closure_delivery.retry_pending_closures()
        send.assert_called_once()
        self.assertEqual(summary["sent"], 1)
        self.assertEqual(
            json.loads(self.state_file("sig-retry-2").read_text(encoding="utf-8"))["status"],
            "sent",
        )

    def test_unknown_outcome_is_never_automatically_retried(self) -> None:
        with mock.patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "t", "TELEGRAM_CHAT_ID": "c"}, clear=False):
            with mock.patch.object(telegram_closure_delivery, "_send_request",
                                    return_value=("unknown_outcome", {})):
                result = telegram_closure_delivery.send_closure(
                    "sig-retry-3", "EURUSD", "BUY", "CLOSED", 1.0, 1.1
                )
            self.assertFalse(result)

            with mock.patch.object(telegram_closure_delivery, "_send_request",
                                    side_effect=AssertionError("must not resend unknown_outcome")):
                summary = telegram_closure_delivery.retry_pending_closures()
        self.assertEqual(summary, {"candidates": 0, "sent": 0, "skipped": 0})
        self.assertEqual(
            json.loads(self.state_file("sig-retry-3").read_text(encoding="utf-8"))["status"],
            "unknown_outcome",
        )

    def test_sent_is_never_resent_by_the_retry_scanner(self) -> None:
        with mock.patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "t", "TELEGRAM_CHAT_ID": "c"}, clear=False):
            with mock.patch.object(telegram_closure_delivery, "_send_request",
                                    return_value=("sent", {"message_id": 1})):
                telegram_closure_delivery.send_closure("sig-retry-4", "EURUSD", "BUY", "CLOSED", 1.0, 1.1)

            with mock.patch.object(telegram_closure_delivery, "_send_request",
                                    side_effect=AssertionError("must not resend sent")):
                summary = telegram_closure_delivery.retry_pending_closures()
        self.assertEqual(summary, {"candidates": 0, "sent": 0, "skipped": 0})

    def test_concurrent_closure_attempts_are_serialized_and_never_double_send(self) -> None:
        send_calls: list[float] = []

        def slow_send(message, token, chat_id):
            send_calls.append(time.monotonic())
            time.sleep(0.05)
            return "sent", {"message_id": 1}

        results: list[bool] = []

        def worker() -> None:
            with mock.patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "t", "TELEGRAM_CHAT_ID": "c"}, clear=False):
                results.append(
                    telegram_closure_delivery.send_closure(
                        "sig-retry-5", "EURUSD", "BUY", "CLOSED", 3.0, 1.1
                    )
                )

        with mock.patch.object(telegram_closure_delivery, "_send_request", side_effect=slow_send):
            threads = [threading.Thread(target=worker) for _ in range(2)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=5)

        self.assertEqual(len(send_calls), 1)
        self.assertEqual(results, [True, True])
        self.assertEqual(
            json.loads(self.state_file("sig-retry-5").read_text(encoding="utf-8"))["status"],
            "sent",
        )

    def test_retry_scanner_ignores_unrelated_malformed_and_historical_files(self) -> None:
        directory = self.root / "state" / "telegram_closure"
        directory.mkdir(parents=True)
        (directory / "malformed.json").write_text("{not valid json", encoding="utf-8")
        (directory / "unrelated.json").write_text(json.dumps([1, 2, 3]), encoding="utf-8")
        (directory / "legacy_incomplete.json").write_text(
            json.dumps({"status": "definite_failure", "signal_id": "legacy-1"}), encoding="utf-8"
        )
        (directory / "old_sent.json").write_text(
            json.dumps({"status": "sent", "signal_id": "old-1", "pair": "EURUSD",
                        "direction": "BUY", "closure_status": "CLOSED",
                        "result_pips": 1.0, "entry": 1.1}),
            encoding="utf-8",
        )
        with mock.patch.object(telegram_closure_delivery, "_send_request",
                                side_effect=AssertionError("must not attempt any send")):
            summary = telegram_closure_delivery.retry_pending_closures()
        self.assertEqual(summary, {"candidates": 0, "sent": 0, "skipped": 2})


class SignalCloserRetryWiringTests(unittest.TestCase):
    """Requirement: the closer must invoke the durable retry scan on every
    LIVE run, even when zero ACTIVE signals exist -- a lost Telegram closure
    otherwise has no future trigger once its signal leaves ACTIVE."""

    def test_live_run_invokes_retry_scan_even_with_zero_active_signals(self) -> None:
        with mock.patch.object(signal_closer, "SUPABASE_KEY", "k"), \
             mock.patch.object(signal_closer, "compute_server_clock_epoch", return_value=2000000000), \
             mock.patch.object(signal_closer, "get_active_signals", return_value=[]), \
             mock.patch.object(signal_closer.time, "sleep"), \
             mock.patch.object(telegram_closure_delivery, "retry_pending_closures",
                                return_value={"candidates": 0, "sent": 0, "skipped": 0}) as retry, \
             mock.patch.object(sys, "argv",
                                ["signal_closer.py", "--live", "--confirm", "CLOSE_SIGNALS", "--max-batch", "5"]):
            signal_closer.main()
        retry.assert_called_once()

    def test_dry_run_does_not_invoke_retry_scan(self) -> None:
        with mock.patch.object(signal_closer, "SUPABASE_KEY", "k"), \
             mock.patch.object(signal_closer, "compute_server_clock_epoch", return_value=2000000000), \
             mock.patch.object(signal_closer, "get_active_signals", return_value=[]), \
             mock.patch.object(telegram_closure_delivery, "retry_pending_closures") as retry, \
             mock.patch.object(sys, "argv", ["signal_closer.py"]):
            signal_closer.main()
        retry.assert_not_called()


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
            secrets = write_live_delivery_secrets(Path(td) / "live-delivery.env")
            orch = vps.Orchestrator(REPO, mutable, ())
            jobs = {job.name: job for job in vps.production_jobs()}
            with mock.patch.dict(os.environ, {"BOTA_R5_SHADOW": "1", "BOTA_REQUIRE_R5_SHADOW": "1",
                                              vps.LIVE_DELIVERY_SECRET_PATH_ENV: str(secrets)}):
                watcher_env = orch.child_env(jobs["watcher"])
                heartbeat_env = orch.child_env(jobs["heartbeat"])
            self.assertEqual(watcher_env["BOTA_R5_SHADOW"], "0")
            self.assertEqual(watcher_env["BOTA_REQUIRE_R5_SHADOW"], "0")
            self.assertEqual(heartbeat_env["BOTA_R5_SHADOW"], "1")
            self.assertEqual(heartbeat_env["BOTA_REQUIRE_R5_SHADOW"], "1")


def write_live_delivery_secrets(path: Path, **overrides: str) -> Path:
    values = {"TELEGRAM_BOT_TOKEN": "live-token", "TELEGRAM_CHAT_ID": "live-chat",
              "SUPABASE_SERVICE_KEY": "live-key"}
    values.update(overrides)
    path.write_text("".join(f"{key}={value}\n" for key, value in values.items()), encoding="utf-8")
    path.chmod(0o600)
    return path


PROBE_JOB_NAMES = ("watcher", "profitlab_delivery", "closer",
                    "daily_summary_server_gate", "heartbeat", "shadow")

# %-formatted (not .format/f-string) so the dict/set literals in the
# generated probe script don't need brace-escaping.
PROBE_SCRIPT_TEMPLATE = """
import importlib.util, json, os, sys
from pathlib import Path

spec = importlib.util.spec_from_file_location("vps_orchestrator_probe", %(vps_path)r)
vps = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = vps
spec.loader.exec_module(vps)

orch = vps.Orchestrator(Path(%(repo)r), Path(%(mutable)r), ())
jobs = {job.name: job for job in vps.production_jobs()}

result = {
    "parent": {key: os.environ.get(key) for key in
               ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "SUPABASE_SERVICE_KEY", "BOTA_R5_SHADOW")},
    "children": {},
    "errors": {},
}
for name in %(names)r:
    try:
        env = orch.child_env(jobs[name])
    except vps.ContractError as exc:
        result["errors"][name] = str(exc)
        continue
    result["children"][name] = {
        key: env.get(key) for key in
        ("BOTA_R5_SHADOW", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "SUPABASE_SERVICE_KEY")
    }
    result["children"][name]["has_telegram_bot_token"] = "TELEGRAM_BOT_TOKEN" in env
    result["children"][name]["has_supabase_service_key"] = "SUPABASE_SERVICE_KEY" in env

Path(%(output)r).write_text(json.dumps(result))
"""


class R5ParentCredentialPoisonRecoveryTests(unittest.TestCase):
    """Blocker 1 regression.

    r5_bootstrap/sitecustomize.py auto-loads via PYTHONPATH ahead of the
    orchestrator whenever BOTA_R5_SHADOW=1 (proven in
    tests/test_r5_no_side_effect_shadow.py) and, as a side effect of guarding
    against real production secrets, replaces every sensitive credential key
    directly inside the *parent* process's os.environ with the R5 sentinel.
    This is not a hand-rolled stand-in: each probe here boots a real fresh
    interpreter with PYTHONPATH/BOTA_R5_SHADOW set exactly like production,
    so the real sitecustomize module performs the real poisoning, then --
    from inside that already-poisoned process -- builds an Orchestrator and
    calls the real child_env() for both approved and unrelated jobs.
    """

    SENTINEL = "R5_SHADOW_NO_NETWORK"

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.mutable = Path(self.tmp.name) / "mutable"
        self.mutable.mkdir()
        self.secrets_path = Path(self.tmp.name) / "live-delivery.env"
        self.output_path = Path(self.tmp.name) / "probe_output.json"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _poisoned_parent_env(self) -> dict[str, str]:
        env = dict(os.environ)
        env.update({
            "BOTA_R5_SHADOW": "1",
            "BOTA_REQUIRE_R5_SHADOW": "1",
            "BOTA_CODE_ROOT": str(REPO),
            "BOTA_ROOT": str(REPO),
            "BOTA_MUTABLE_ROOT": str(self.mutable),
            "PYTHONPATH": str(REPO / "r5_bootstrap"),
        })
        for key in (
            "TELEGRAM_BOT_TOKEN", "TELEGRAM_TOKEN", "BOT_TOKEN",
            "TELEGRAM_CHAT_ID", "CHAT_ID", "TG_CHAT_ID",
            "SUPABASE_SERVICE_KEY", "BOTA_HEALTH_INGEST_SECRET",
        ):
            env[key] = self.SENTINEL
        return env

    def _run_probe(self, env: dict[str, str]) -> dict:
        script = Path(self.tmp.name) / "probe.py"
        script.write_text(PROBE_SCRIPT_TEMPLATE % {
            "vps_path": str(TOOLS / "vps_orchestrator.py"),
            "repo": str(REPO),
            "mutable": str(self.mutable),
            "names": list(PROBE_JOB_NAMES),
            "output": str(self.output_path),
        }, encoding="utf-8")
        completed = subprocess.run([sys.executable, str(script)], env=env, cwd=REPO,
                                   stdin=subprocess.DEVNULL, text=True, capture_output=True, timeout=20)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        return json.loads(self.output_path.read_text(encoding="utf-8"))

    def test_poisoning_is_reproduced_and_approved_children_recover_scoped_live_secrets(self) -> None:
        write_live_delivery_secrets(self.secrets_path)
        env = self._poisoned_parent_env()
        env["BOTA_LIVE_DELIVERY_SECRET_PATH"] = str(self.secrets_path)
        result = self._run_probe(env)

        # The poisoning this recovery path must survive is real: the parent
        # process itself stayed fully sentinel/R5-shadowed throughout.
        self.assertEqual(result["parent"]["TELEGRAM_BOT_TOKEN"], self.SENTINEL)
        self.assertEqual(result["parent"]["SUPABASE_SERVICE_KEY"], self.SENTINEL)
        self.assertEqual(result["parent"]["BOTA_R5_SHADOW"], "1")
        self.assertEqual(result["errors"], {})

        children = result["children"]
        watcher = children["watcher"]
        self.assertEqual(watcher["BOTA_R5_SHADOW"], "0")
        self.assertEqual(watcher["TELEGRAM_BOT_TOKEN"], "live-token")
        self.assertEqual(watcher["TELEGRAM_CHAT_ID"], "live-chat")
        self.assertEqual(watcher["SUPABASE_SERVICE_KEY"], "live-key")

        profitlab = children["profitlab_delivery"]
        self.assertEqual(profitlab["SUPABASE_SERVICE_KEY"], "live-key")
        self.assertFalse(profitlab["has_telegram_bot_token"])

        closer = children["closer"]
        self.assertEqual(closer["SUPABASE_SERVICE_KEY"], "live-key")
        self.assertEqual(closer["TELEGRAM_BOT_TOKEN"], "live-token")
        self.assertEqual(closer["TELEGRAM_CHAT_ID"], "live-chat")

        gate = children["daily_summary_server_gate"]
        self.assertEqual(gate["TELEGRAM_BOT_TOKEN"], "live-token")
        self.assertEqual(gate["TELEGRAM_CHAT_ID"], "live-chat")
        self.assertFalse(gate["has_supabase_service_key"])

        for unrelated in ("heartbeat", "shadow"):
            env_for = children[unrelated]
            self.assertEqual(env_for["BOTA_R5_SHADOW"], "1")
            self.assertEqual(env_for["TELEGRAM_BOT_TOKEN"], self.SENTINEL)
            self.assertEqual(env_for["SUPABASE_SERVICE_KEY"], self.SENTINEL)

    def test_missing_secret_source_fails_closed_before_launch(self) -> None:
        env = self._poisoned_parent_env()
        env["BOTA_LIVE_DELIVERY_SECRET_PATH"] = str(self.secrets_path)  # never created
        result = self._run_probe(env)
        for approved in ("watcher", "profitlab_delivery", "closer", "daily_summary_server_gate"):
            self.assertNotIn(approved, result["children"])
            self.assertIn("unreadable", result["errors"][approved])
        self.assertEqual(result["children"]["heartbeat"]["BOTA_R5_SHADOW"], "1")
        self.assertEqual(result["children"]["heartbeat"]["TELEGRAM_BOT_TOKEN"], self.SENTINEL)

    def test_insecure_permission_secret_source_fails_closed(self) -> None:
        write_live_delivery_secrets(self.secrets_path)
        self.secrets_path.chmod(0o644)
        env = self._poisoned_parent_env()
        env["BOTA_LIVE_DELIVERY_SECRET_PATH"] = str(self.secrets_path)
        result = self._run_probe(env)
        for approved in ("watcher", "profitlab_delivery", "closer", "daily_summary_server_gate"):
            self.assertIn("insecure_permissions", result["errors"][approved])

    def test_malformed_duplicate_and_incomplete_secret_sources_fail_closed(self) -> None:
        cases = {
            "malformed": "not-a-key-value-line\n",
            "duplicate": "TELEGRAM_BOT_TOKEN=a\nTELEGRAM_BOT_TOKEN=b\nTELEGRAM_CHAT_ID=c\nSUPABASE_SERVICE_KEY=d\n",
            "unknown_key": "TELEGRAM_BOT_TOKEN=a\nTELEGRAM_CHAT_ID=b\nSUPABASE_SERVICE_KEY=c\nEXTRA_KEY=d\n",
            "incomplete": "TELEGRAM_BOT_TOKEN=a\nTELEGRAM_CHAT_ID=b\n",
            "sentinel_value": f"TELEGRAM_BOT_TOKEN={self.SENTINEL}\nTELEGRAM_CHAT_ID=b\nSUPABASE_SERVICE_KEY=c\n",
        }
        for label, content in cases.items():
            with self.subTest(label=label):
                self.secrets_path.write_text(content, encoding="utf-8")
                self.secrets_path.chmod(0o600)
                env = self._poisoned_parent_env()
                env["BOTA_LIVE_DELIVERY_SECRET_PATH"] = str(self.secrets_path)
                result = self._run_probe(env)
                self.assertNotIn("watcher", result["children"])
                self.assertTrue(result["errors"]["watcher"].startswith("live_delivery_secret_source_"))

    def test_preflight_remains_valid_for_the_still_shadowed_parent_process(self) -> None:
        """tools/r5_no_side_effect_preflight.py must keep passing for the
        parent R5 process itself -- this recovery path only affects
        approved children's child_env(), never the parent's own os.environ,
        forced flags, or transport suppression."""
        write_live_delivery_secrets(self.secrets_path)
        env = self._poisoned_parent_env()
        env["BOTA_LIVE_DELIVERY_SECRET_PATH"] = str(self.secrets_path)
        completed = subprocess.run([sys.executable, str(TOOLS / "r5_no_side_effect_preflight.py")],
                                   env=env, cwd=REPO, stdin=subprocess.DEVNULL,
                                   text=True, capture_output=True, timeout=20)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads(completed.stdout.strip().splitlines()[-1])
        self.assertTrue(result["healthy"], result)


if __name__ == "__main__":
    unittest.main()
