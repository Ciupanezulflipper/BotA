#!/usr/bin/env python3
"""Exact retry dedup and independent sink delivery regressions.

The 20 October distinct same-direction ACTIVE publication policy was superseded
by the founder-approved 25 November shared local admission decision. The
publisher remains a transport with exact identity dedup, not admission authority.
Distinct exposure and re-entry are tested in test_retirement_exposure.py.
"""
from __future__ import annotations

import importlib.util
import os
import sys
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
        _ = self.responses
        return None


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
        path = connection.requests[0]["path"]
        self.assertIn("pair=eq.USDJPY", path)
        self.assertIn("direction=eq.SELL", path)
        self.assertIn("timeframe=eq.M15", path)
        self.assertIn("entry_price=eq.158.00999", path)
        self.assertIn("stop_loss=eq.158.5", path)
        self.assertIn("take_profit=eq.156.8", path)


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

    @staticmethod
    def _decision(status: str) -> dict:
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
