#!/usr/bin/env python3
"""Regression tests for subscriber-facing BotA operational Telegram UX."""

from __future__ import annotations

import unittest

from tools import telegram_ops_ux


class TelegramOpsUxTests(unittest.TestCase):
    def test_zombie_only_control_noise_is_suppressed(self) -> None:
        raw = "control_plane:zombie_runsv_count:2"
        self.assertEqual(telegram_ops_ux.classify_failure(raw), "suppress")

    def test_multiple_zombie_only_tokens_are_suppressed(self) -> None:
        raw = (
            "control_plane:zombie_runsv_count:1|"
            "control_plane:zombie_runsv_count:2"
        )
        self.assertEqual(telegram_ops_ux.classify_failure(raw), "suppress")

    def test_pipeline_failure_is_scan_class(self) -> None:
        raw = (
            "pipeline:decision_missing_or_stale:EURUSD:M15:None:missing:missing|"
            "pipeline:decision_missing_or_stale:GBPUSD:M15:None:missing:missing"
        )
        self.assertEqual(telegram_ops_ux.classify_failure(raw), "scan")

    def test_real_control_failure_is_system_class(self) -> None:
        raw = (
            "control_plane:running:6/7|"
            "control_plane:crond_not_owned_by_current_runsv"
        )
        self.assertEqual(telegram_ops_ux.classify_failure(raw), "system")

    def test_real_control_failure_dominates_pipeline_failure(self) -> None:
        raw = "pipeline:decision_missing:EURUSD|control_plane:running:6/7"
        self.assertEqual(telegram_ops_ux.classify_failure(raw), "system")

    def test_legacy_flag_classification_is_supported(self) -> None:
        self.assertEqual(telegram_ops_ux.classify_flag("scan\n"), "scan")
        self.assertEqual(
            telegram_ops_ux.classify_flag("control_plane:zombie_runsv_count:2"),
            "suppress",
        )
        self.assertEqual(
            telegram_ops_ux.classify_flag("pipeline:decision_missing:EURUSD"),
            "scan",
        )

    def test_user_messages_hide_raw_failure_codes(self) -> None:
        for kind in ("scan", "system"):
            issue = telegram_ops_ux.issue_message(kind)
            recovery = telegram_ops_ux.recovery_message(kind)
            combined = issue + recovery
            self.assertNotIn("control_plane:", combined)
            self.assertNotIn("pipeline:", combined)
            self.assertNotIn("zombie_runsv_count", combined)
            self.assertNotIn("|", combined)

    def test_expected_clean_labels_are_used(self) -> None:
        self.assertIn("SCAN DELAYED", telegram_ops_ux.issue_message("scan"))
        self.assertIn("SCAN RESTORED", telegram_ops_ux.recovery_message("scan"))
        self.assertIn("SYSTEM ISSUE", telegram_ops_ux.issue_message("system"))
        self.assertIn("SYSTEM RESTORED", telegram_ops_ux.recovery_message("system"))
        self.assertEqual(telegram_ops_ux.issue_message("suppress"), "")
        self.assertEqual(telegram_ops_ux.recovery_message("suppress"), "")


if __name__ == "__main__":
    unittest.main()
