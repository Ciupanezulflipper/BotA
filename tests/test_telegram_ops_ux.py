#!/usr/bin/env python3
"""Regression tests for subscriber-facing BotA operational Telegram UX."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import heartbeat_runtime, telegram_ops_ux


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


class HeartbeatTelegramUxTests(unittest.TestCase):
    def test_heartbeat_keeps_raw_diagnostics_local_only(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "BotA"
            health = root / "state" / "runtime_health.json"
            health.parent.mkdir(parents=True, exist_ok=True)
            health.write_text(
                json.dumps(
                    {
                        "bot_mode": "DEGRADED",
                        "market_state": "open",
                        "failure_reasons": ["control_plane:zombie_runsv_count:2"],
                        "control_plane": {
                            "owned": 7,
                            "required": 7,
                            "running": 7,
                            "orphaned": 0,
                        },
                        "pipeline_progress": {"healthy": True},
                    }
                ),
                encoding="utf-8",
            )
            log_path = root / "logs" / "cron.heartbeat.log"
            bucket_path = root / "logs" / "state" / "heartbeat_utc_bucket.txt"
            state_path = root / "state" / "heartbeat_delivery.json"

            with (
                patch.object(
                    heartbeat_runtime,
                    "telegram_credentials",
                    return_value=("unit-test-token", "unit-test-chat"),
                ),
                patch.object(
                    heartbeat_runtime.delivery,
                    "send_telegram",
                    return_value=(True, "http_status:200"),
                ) as sender,
            ):
                heartbeat_runtime.handle_heartbeat(
                    root=root,
                    log_path=log_path,
                    bucket_path=bucket_path,
                    state_path=state_path,
                    server_epoch=1_775_044_800,
                    source_count=3,
                    now_monotonic=100.0,
                    current_boot_id="boot-a",
                    dry_run=False,
                )

            message = sender.call_args.args[2]
            local_log = log_path.read_text(encoding="utf-8")

        self.assertIn("BOTA · ONLINE", message)
        self.assertNotIn("control_plane:", message)
        self.assertNotIn("zombie_runsv_count", message)
        self.assertNotIn("failures=", message)
        self.assertIn("zombie_runsv_count", local_log)
        self.assertIn("HB_UTC_INTERNAL_SUMMARY", local_log)


if __name__ == "__main__":
    unittest.main()
