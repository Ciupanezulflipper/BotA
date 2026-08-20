from __future__ import annotations

import importlib.util
import socket
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "market_pulse_v2.py"
SPEC = importlib.util.spec_from_file_location("market_pulse_v2", MODULE_PATH)
assert SPEC and SPEC.loader
pulse = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pulse)


def fresh_event(**overrides):
    event = {
        "monotonic_ns": pulse.monotonic_ns(),
        "status": "completed",
        "outcome": "filter_rejected",
        "terminal_outcome": "EVALUATED_REJECTED",
        "filter_rejected": True,
        "rejection_gate": "direction_not_tradeable",
        "score": 42.0,
        "provider": "oanda",
        "alerts_csv_persisted": True,
        "telegram_result": "not_attempted",
    }
    event.update(overrides)
    return event


class MarketPulseV2Tests(unittest.TestCase):
    def test_three_pair_message_is_clean_and_complete(self):
        rows = [
            {
                "pair": "EURUSD",
                "state": "no_setup",
                "headline": "⚪ No setup",
                "detail": "No tradeable direction",
                "age_seconds": 60,
                "score": 42,
                "provider": "oanda",
            },
            {
                "pair": "GBPUSD",
                "state": "qualified",
                "headline": "🟢 Qualified setup",
                "detail": "Trade alert sent",
                "age_seconds": 120,
                "score": 76,
                "provider": "oanda",
            },
            {
                "pair": "USDJPY",
                "state": "data_issue",
                "headline": "⚠️ Data issue",
                "detail": "Market data unavailable",
                "age_seconds": None,
                "score": None,
                "provider": "",
            },
        ]
        text = pulse.format_message(rows, datetime(2026, 8, 19, 12, 15, tzinfo=timezone.utc))

        self.assertIn("📡 BOTA · MARKET CHECK", text)
        self.assertIn("EUR/USD", text)
        self.assertIn("GBP/USD", text)
        self.assertIn("USD/JPY", text)
        self.assertIn("1 qualified · 1 no setup · 1 data issue", text)
        self.assertNotIn("|", text)
        self.assertNotIn("control_plane:", text)
        self.assertNotIn("zombie_runsv", text)

    def test_fresh_rejected_decision_is_no_setup_with_friendly_reason(self):
        now_ns = pulse.monotonic_ns()
        event = fresh_event(monotonic_ns=now_ns, rejection_gate="H1_trend_neutral")
        row = pulse.classify_pair("EURUSD", event, "boot", "boot", now_ns)

        self.assertEqual(row["state"], "no_setup")
        self.assertEqual(row["headline"], "⚪ No setup")
        self.assertEqual(row["detail"], "Awaiting H1 confirmation")

    def test_fresh_persisted_accept_is_qualified(self):
        now_ns = pulse.monotonic_ns()
        event = fresh_event(
            monotonic_ns=now_ns,
            outcome="telegram_sent",
            terminal_outcome="DELIVERY_ATTEMPTED",
            filter_rejected=False,
            score=77.0,
            telegram_result="sent",
        )
        row = pulse.classify_pair("GBPUSD", event, "boot", "boot", now_ns)

        self.assertEqual(row["state"], "qualified")
        self.assertEqual(row["headline"], "🟢 Qualified setup")
        self.assertEqual(row["detail"], "Trade alert sent")

    def test_stale_or_wrong_boot_decision_is_not_presented_as_tradeable(self):
        now_ns = pulse.monotonic_ns()
        event = fresh_event(monotonic_ns=now_ns, filter_rejected=False, score=80.0)
        row = pulse.classify_pair("USDJPY", event, "old-boot", "new-boot", now_ns)

        self.assertEqual(row["state"], "data_issue")
        self.assertEqual(row["headline"], "⚠️ Scan stale")

    def test_scheduled_window_is_three_days_only(self):
        self.assertTrue(pulse.scheduled_window(datetime(2026, 8, 17, 8, 0, tzinfo=timezone.utc)))
        self.assertTrue(pulse.scheduled_window(datetime(2026, 8, 19, 12, 0, tzinfo=timezone.utc)))
        self.assertTrue(pulse.scheduled_window(datetime(2026, 8, 21, 18, 59, tzinfo=timezone.utc)))
        self.assertFalse(pulse.scheduled_window(datetime(2026, 8, 20, 12, 0, tzinfo=timezone.utc)))
        self.assertFalse(pulse.scheduled_window(datetime(2026, 8, 19, 7, 59, tzinfo=timezone.utc)))
        self.assertFalse(pulse.scheduled_window(datetime(2026, 8, 19, 19, 0, tzinfo=timezone.utc)))

    def test_timeout_is_unknown_outcome_and_dns_is_retryable(self):
        timeout_connection = mock.Mock()
        timeout_connection.request.side_effect = TimeoutError("timed out")
        with mock.patch.object(pulse.http.client, "HTTPSConnection", return_value=timeout_connection):
            status, _, reason = pulse.telegram_send("x", "token", "chat")
        self.assertEqual(status, "unknown_outcome")
        self.assertEqual(reason, "timeout")

        dns_connection = mock.Mock()
        dns_connection.request.side_effect = socket.gaierror(-2, "Name or service not known")
        with mock.patch.object(pulse.http.client, "HTTPSConnection", return_value=dns_connection):
            status, _, reason = pulse.telegram_send("x", "token", "chat")
        self.assertEqual(status, "retryable_failure")
        self.assertEqual(reason, "gaierror")


if __name__ == "__main__":
    unittest.main()
