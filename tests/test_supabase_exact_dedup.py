#!/usr/bin/env python3
"""Regression coverage for the distinct-signal Supabase dedup contract.

Production evidence (20 Oct 2026): a confirmed USDJPY SELL at entry=158.00999
was followed 35 minutes later by a distinct, qualified GREEN USDJPY SELL at
entry=157.99200. Telegram correctly sent both; Supabase incorrectly suppressed
the second one with the old pair+ACTIVE-only dedup (``skipped_active_exists``).

This violates BOTH_HEALTHY_EXACTLY_ONCE_PER_SINK: a distinct GREEN signal for
the same pair must reach Supabase even while another ACTIVE signal for that
pair is open. An exact retry/replay of the same signal must still dedup.

These tests exercise the real dedup query construction in
``tools/supabase_publish.py`` (via a fake HTTPS connection, no network) and
the watcher-cycle evidence contract in ``tools/watcher_cycle_ledger.py`` /
``tools/watcher_cycle_contract.py``.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from contextlib import nullcontext
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
TOOLS = REPO / "tools"


def load_module(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, REPO / relative)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


publisher = load_module("supabase_publish_exact_dedup_test", "tools/supabase_publish.py")
ledger = load_module("watcher_cycle_ledger_exact_dedup_test", "tools/watcher_cycle_ledger.py")
contract = load_module("watcher_cycle_contract_exact_dedup_test", "tools/watcher_cycle_contract.py")


class FakeHTTPResponse:
    def __init__(self, status: int, payload: bytes = b"") -> None:
        self.status = status
        self.payload = payload

    def read(self) -> bytes:
        return self.payload


class FakeHTTPSConnection:
    """Records the exact dedup query path issued for each call."""

    def __init__(self, responses: list[FakeHTTPResponse]) -> None:
        self.responses = list(responses)
        self.requests: list[dict[str, object]] = []

    def request(self, method, path, body=None, headers=None) -> None:
        self.requests.append({"method": method, "path": path, "body": body})

    def getresponse(self) -> FakeHTTPResponse:
        return self.responses.pop(0)

    def close(self) -> None:
        pass


def query_signal(connection_responses, *, pair, direction, entry, sl, tp, tf="M15", score="80", tier="GREEN"):
    """Run publish_with_status against a scripted HTTPS fake; returns (ok, status, connection)."""
    connection = FakeHTTPSConnection(connection_responses)
    with (
        mock.patch.object(publisher, "publication_lock", return_value=nullcontext()),
        mock.patch.object(publisher.http.client, "HTTPSConnection", return_value=connection),
        mock.patch.dict(os.environ, {"SUPABASE_SERVICE_KEY": "test-key"}, clear=False),
    ):
        ok, status = publisher.publish_with_status(pair, direction, entry, sl, tp, score, tf, tier)
    return ok, status, connection


class DistinctSignalNotBlockedTests(unittest.TestCase):
    """A: a distinct GREEN signal for the same pair must not be suppressed."""

    def test_second_distinct_usdjpy_sell_is_not_blocked_by_first_active(self) -> None:
        # Real Supabase holds only the first ACTIVE row (entry=158.00999). The
        # dedup query for the *second*, distinct entry (157.99200) must filter
        # on the full identity and therefore find no match.
        ok, status, connection = query_signal(
            [FakeHTTPResponse(200, b"[]"), FakeHTTPResponse(201, b"")],
            pair="USDJPY", direction="SELL", entry="157.99200", sl="158.50000", tp="156.80000",
        )
        self.assertTrue(ok)
        self.assertEqual(status, "published")
        dedup_path = connection.requests[0]["path"]
        self.assertIn("entry_price=eq.157.992", dedup_path)
        self.assertIn("pair=eq.USDJPY", dedup_path)
        self.assertIn("direction=eq.SELL", dedup_path)


class ExactRetryDedupTests(unittest.TestCase):
    """B: an exact retry/replay of the same signal must still dedup."""

    def test_exact_retry_of_same_signal_is_deduplicated(self) -> None:
        ok, status, connection = query_signal(
            [FakeHTTPResponse(200, b'[{"id":"existing"}]')],
            pair="USDJPY", direction="SELL", entry="158.00999", sl="158.50000", tp="156.80000",
        )
        self.assertTrue(ok)
        self.assertEqual(status, "skipped_exact_duplicate")
        # Only the dedup GET occurred; no insert was attempted.
        self.assertEqual(len(connection.requests), 1)
        self.assertEqual(connection.requests[0]["method"], "GET")


class DirectionDistinctTests(unittest.TestCase):
    """C: same pair + different direction is a distinct identity."""

    def test_opposite_direction_same_pair_is_not_blocked(self) -> None:
        ok, status, connection = query_signal(
            [FakeHTTPResponse(200, b"[]"), FakeHTTPResponse(201, b"")],
            pair="USDJPY", direction="BUY", entry="158.00999", sl="157.50000", tp="159.20000",
        )
        self.assertTrue(ok)
        self.assertEqual(status, "published")
        self.assertIn("direction=eq.BUY", connection.requests[0]["path"])


class StopTakeProfitDistinctTests(unittest.TestCase):
    """D: same pair + same direction + different SL/TP is a distinct identity."""

    def test_different_sl_tp_same_entry_is_not_blocked(self) -> None:
        ok, status, connection = query_signal(
            [FakeHTTPResponse(200, b"[]"), FakeHTTPResponse(201, b"")],
            pair="USDJPY", direction="SELL", entry="158.00999", sl="158.60000", tp="156.50000",
        )
        self.assertTrue(ok)
        self.assertEqual(status, "published")
        path = connection.requests[0]["path"]
        self.assertIn("stop_loss=eq.158.6", path)
        self.assertIn("take_profit=eq.156.5", path)


class FailedPublishIsolatedFromTelegramTests(unittest.TestCase):
    """E: a failed Supabase retry must stay isolated from Telegram's own result."""

    def test_publish_failure_does_not_touch_telegram(self) -> None:
        connection = FakeHTTPSConnection([FakeHTTPResponse(200, b"[]"), FakeHTTPResponse(500, b"boom")])
        with (
            mock.patch.object(publisher, "publication_lock", return_value=nullcontext()),
            mock.patch.object(publisher.http.client, "HTTPSConnection", return_value=connection),
            mock.patch.dict(os.environ, {"SUPABASE_SERVICE_KEY": "test-key"}, clear=False),
        ):
            ok, status = publisher.publish_with_status(
                "USDJPY", "SELL", "157.99200", "158.50000", "156.80000", "80", "M15", "GREEN"
            )
        self.assertFalse(ok)
        self.assertEqual(status, "failed_publish")
        # The watcher-cycle contract still accepts this row when Telegram sent
        # successfully: Supabase failure is recorded, not papered over, and
        # does not erase or block the independent Telegram outcome.
        rows = {("USDJPY", "M15"): {
            "pair": "USDJPY", "timeframe": "M15", "direction": "SELL", "score": "80",
            "entry": "157.99200", "sl": "158.50000", "tp": "156.80000",
            "rejected": "false", "tier": "GREEN",
        }}
        telegram_record = {
            "pair": "USDJPY", "timeframe": "M15", "direction": "SELL", "score": "80",
            "entry": "157.99200", "sl": "158.50000", "tp": "156.80000", "status": "sent",
        }
        sent_scopes = contract.validate_telegram(rows, [telegram_record])
        self.assertEqual(sent_scopes, {("USDJPY", "M15")})
        supabase_record = {
            "cycle_id": "cycle-1", "pair": "USDJPY", "timeframe": "M15",
            "direction": "SELL", "entry": "157.99200", "tier": "GREEN", "status": status,
        }
        with self.assertRaisesRegex(ValueError, "supabase_delivery_unhealthy:failed_publish"):
            contract.validate_supabase(rows, [supabase_record], "cycle-1", sent_scopes)


class WatcherCycleEvidenceDistinguishesOutcomesTests(unittest.TestCase):
    """F: watcher cycle evidence must distinguish published / deduplicated
    exact retry / failed publish as three separate, legible outcomes."""

    def _decision(self, status: str) -> dict:
        with mock.patch.object(
            ledger.subprocess, "run",
            return_value=ledger.subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
        ):
            return ledger.ledger_decision(
                cycle_id="cycle-1", server_epoch=1_786_000_000, pair="USDJPY", timeframe="M15",
                row={
                    "pair": "USDJPY", "tf": "M15", "direction": "SELL", "score": "80",
                    "entry": "157.99200", "sl": "158.50000", "tp": "156.80000",
                    "rejected": "false", "provider": "engine_A3",
                },
                lines=["[TELEGRAM] SENT: via tools/telegram_send.sh"],
                structured_supabase=status,
            )

    def test_published_deduplicated_and_failed_are_distinct_outcomes(self) -> None:
        published = self._decision("published")
        deduplicated = self._decision("skipped_exact_duplicate")
        failed = self._decision("failed_publish")

        self.assertEqual(published["supabase"], "published")
        self.assertEqual(deduplicated["supabase"], "skipped_exact_duplicate")
        self.assertEqual(failed["supabase"], "failed")

        outcomes = {published["supabase"], deduplicated["supabase"], failed["supabase"]}
        self.assertEqual(len(outcomes), 3, "all three outcomes must be distinguishable")

    def test_status_vocabulary_matches_between_ledger_and_contract(self) -> None:
        self.assertIn("skipped_exact_duplicate", ledger.VALID_SUPABASE_STATUSES)
        self.assertIn("skipped_exact_duplicate", contract.VALID_SUPABASE)
        self.assertNotIn("skipped_active_exists", ledger.VALID_SUPABASE_STATUSES)
        self.assertNotIn("skipped_active_exists", contract.VALID_SUPABASE)


class SignalClosureUnaffectedTests(unittest.TestCase):
    """Requirement 4: existing signal closure must keep working per-row,
    independent of how many ACTIVE rows now exist for one pair."""

    def test_signal_closer_evaluates_rows_by_id_not_pair_uniqueness(self) -> None:
        signal_closer = load_module("signal_closer_exact_dedup_test", "tools/signal_closer.py")
        source = (TOOLS / "signal_closer.py").read_text(encoding="utf-8")
        # get_active_signals fetches every ACTIVE row (no pair-uniqueness
        # assumption); closure logic below operates per `sig["id"]`.
        self.assertIn('"signals?status=eq.ACTIVE"', source)
        self.assertTrue(callable(signal_closer.get_active_signals))


if __name__ == "__main__":
    unittest.main()
