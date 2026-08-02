#!/usr/bin/env python3
"""Regression tests for the BotA Telegram status-message policy."""

from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUTOSTATUS = ROOT / "tools" / "autostatus.sh"
FORMAT_STATUS = ROOT / "tools" / "format_status.py"


class StatusMessagePolicyTests(unittest.TestCase):
    def test_autostatus_is_market_gated(self) -> None:
        source = AUTOSTATUS.read_text(encoding="utf-8")
        self.assertIn(
            "market_open.sh",
            source,
            "Hourly status still sends while the configured market is closed.",
        )

    def test_formatter_does_not_call_network_snapshot_fetcher(self) -> None:
        source = FORMAT_STATUS.read_text(encoding="utf-8")
        self.assertNotIn(
            "emit_snapshot.py",
            source,
            "Status formatting still creates separate unaccounted provider calls.",
        )

    def test_internal_vote_wording_is_not_exposed(self) -> None:
        source = FORMAT_STATUS.read_text(encoding="utf-8")
        self.assertNotIn("Vote ", source)
        self.assertNotIn("/9", source)

    def test_user_facing_trend_labels_exist(self) -> None:
        source = FORMAT_STATUS.read_text(encoding="utf-8")
        for label in ("STRONG BUY", "BUY", "HOLD", "SELL", "STRONG SELL"):
            self.assertIn(label, source)

    def test_status_is_identified_as_non_entry_context(self) -> None:
        source = FORMAT_STATUS.read_text(encoding="utf-8").lower()
        self.assertTrue(
            "not a trade entry" in source or "trend context" in source,
            "Technical trend must not be presented as an executable BotA signal.",
        )

    def test_raw_provider_budget_is_not_appended(self) -> None:
        source = FORMAT_STATUS.read_text(encoding="utf-8")
        self.assertNotIn("api_credit_tracker.py", source)


if __name__ == "__main__":
    unittest.main()
