from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools import pre_market_integrity as integrity


class ConfigTests(unittest.TestCase):
    def test_expected_production_scope_passes_without_exposing_other_keys(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / ".env.runtime"
            path.write_text(
                '\n'.join(
                    [
                        'PAIRS="EURUSD GBPUSD USDJPY"',
                        'TIMEFRAMES="M15"',
                        'POLICY_B_ENABLED=1',
                        'POLICY_B_SCORE_MIN=70',
                        'POLICY_B_ADX_MAX=30',
                        'NEWS_ON=0',
                        'TELEGRAM_ENABLED=1',
                        'DRY_RUN_MODE=0',
                        'TELEGRAM_BOT_TOKEN=secret-must-not-be-returned',
                    ]
                )
                + '\n',
                encoding="utf-8",
            )
            result = integrity.config_check(path)
        self.assertTrue(result["healthy"])
        self.assertNotIn("TELEGRAM_BOT_TOKEN", result["values"])

    def test_partial_pair_scope_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / ".env.runtime"
            path.write_text(
                'PAIRS="EURUSD GBPUSD"\nTIMEFRAMES=M15\n', encoding="utf-8"
            )
            result = integrity.config_check(path)
        self.assertFalse(result["healthy"])
        self.assertTrue(
            any(
                reason.startswith("config_mismatch:PAIRS")
                for reason in result["failure_reasons"]
            )
        )


class CronTests(unittest.TestCase):
    def test_migrated_watcher_comment_and_one_profitlab_cron_pass(self) -> None:
        result = integrity.cron_check(
            '#MIGRATED_TO_RUNIT */15 * * * * signal_watcher_pro.sh\n'
            '* * * * * python3 /x/profitlab_delivery.py\n'
        )
        self.assertTrue(result["healthy"])
        self.assertEqual(result["active_direct_watcher_cron_count"], 0)
        self.assertEqual(result["active_profitlab_cron_count"], 1)

    def test_active_watcher_cron_fails(self) -> None:
        result = integrity.cron_check(
            '*/15 * * * * /x/watcher_gated_cycle.sh\n'
            '* * * * * python3 /x/profitlab_delivery.py\n'
        )
        self.assertFalse(result["healthy"])
        self.assertIn("active_direct_watcher_cron:1", result["failure_reasons"])

    def test_duplicate_profitlab_cron_fails(self) -> None:
        line = '* * * * * python3 /x/profitlab_delivery.py\n'
        result = integrity.cron_check(line + line)
        self.assertFalse(result["healthy"])
        self.assertIn("profitlab_cron_count:2", result["failure_reasons"])


class BootTests(unittest.TestCase):
    def test_managed_native_watchdog_boot_block_passes(self) -> None:
        text = (
            '#!/bin/bash\n'
            '# RUNSVDIR_GUARD_START=DISABLED\n'
            f'{integrity.BOOT_BEGIN}\n'
            '"/x/start_native_service_daemon_watchdog.sh" >> "/x/log" 2>&1\n'
            f'{integrity.BOOT_END}\n'
        )
        result = integrity.boot_check(text)
        self.assertTrue(result["healthy"])
        self.assertEqual(result["managed_block_count"], 1)
        self.assertEqual(result["active_legacy_guard_count"], 0)
        self.assertEqual(result["active_native_watchdog_count"], 1)

    def test_active_legacy_guard_fails(self) -> None:
        text = (
            '#!/bin/bash\n'
            '/x/start_runsvdir_guard.sh\n'
            f'{integrity.BOOT_BEGIN}\n'
            '/x/start_native_service_daemon_watchdog.sh\n'
            f'{integrity.BOOT_END}\n'
        )
        result = integrity.boot_check(text)
        self.assertFalse(result["healthy"])
        self.assertIn("boot_active_legacy_guard:1", result["failure_reasons"])

    def test_missing_managed_block_fails(self) -> None:
        result = integrity.boot_check(
            '#!/bin/bash\n/x/start_native_service_daemon_watchdog.sh\n'
        )
        self.assertFalse(result["healthy"])
        self.assertEqual(result["managed_block_count"], 0)
        self.assertTrue(
            any(
                reason.startswith("boot_managed_block:")
                for reason in result["failure_reasons"]
            )
        )

    def test_reversed_markers_report_zero_managed_blocks(self) -> None:
        result = integrity.boot_check(
            f'{integrity.BOOT_END}\n'
            '/x/start_native_service_daemon_watchdog.sh\n'
            f'{integrity.BOOT_BEGIN}\n'
        )
        self.assertFalse(result["healthy"])
        self.assertEqual(result["managed_block_count"], 0)


class ThresholdTests(unittest.TestCase):
    def test_default_integer_threshold_is_returned(self) -> None:
        with mock.patch.dict(integrity.os.environ, {}, clear=True):
            self.assertEqual(integrity.env_int("EXAMPLE_THRESHOLD", "1500"), 1500)

    def test_malformed_threshold_becomes_integrity_error(self) -> None:
        with mock.patch.dict(
            integrity.os.environ,
            {"MAX_UPDATER_PROGRESS_AGE_SECS": "not-an-int"},
            clear=False,
        ):
            with self.assertRaisesRegex(
                integrity.IntegrityError,
                "invalid_threshold:MAX_UPDATER_PROGRESS_AGE_SECS",
            ):
                integrity.env_int("MAX_UPDATER_PROGRESS_AGE_SECS", "1500")


class FailureAggregationTests(unittest.TestCase):
    def test_failure_reasons_are_namespaced(self) -> None:
        checks = {
            "control": {"failure_reasons": ["manager_count:2"]},
            "clock": {"failure_reasons": []},
        }
        self.assertEqual(
            integrity.flatten_failures(checks),
            ["control:manager_count:2"],
        )

    def test_commit_validation_is_exact(self) -> None:
        self.assertTrue(integrity.valid_commit("a" * 40))
        self.assertFalse(integrity.valid_commit("A" * 40))
        self.assertFalse(integrity.valid_commit("a" * 39))


if __name__ == "__main__":
    unittest.main()
