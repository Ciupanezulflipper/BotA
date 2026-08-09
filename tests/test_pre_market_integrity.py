from __future__ import annotations

import json
import subprocess
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
                "\n".join(
                    [
                        'PAIRS="EURUSD GBPUSD USDJPY"',
                        'TIMEFRAMES="M15"',
                        "POLICY_B_ENABLED=1",
                        "POLICY_B_SCORE_MIN=70",
                        "POLICY_B_ADX_MAX=30",
                        "NEWS_ON=0",
                        "TELEGRAM_ENABLED=1",
                        "DRY_RUN_MODE=0",
                        "TELEGRAM_BOT_TOKEN=secret-must-not-be-returned",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            result = integrity.config_check(path)
        self.assertTrue(result["healthy"])
        self.assertNotIn("TELEGRAM_BOT_TOKEN", result["values"])

    def test_effective_config_honors_watcher_exports_after_runtime_env(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            runtime = root / ".env.runtime"
            wrapper = root / "run"
            runtime.write_text(
                "\n".join(
                    [
                        'PAIRS="EURUSD GBPUSD USDJPY"',
                        'TIMEFRAMES="M15"',
                        'TELEGRAM_ENABLED="1"',
                        'DRY_RUN_MODE="0"',
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            wrapper.write_text(
                "\n".join(
                    [
                        'export PAIRS="EURUSD GBPUSD USDJPY"',
                        'export TIMEFRAMES="M15"',
                        'export POLICY_B_ENABLED="1"',
                        'export POLICY_B_SCORE_MIN="70"',
                        'export POLICY_B_ADX_MAX="30"',
                        'export NEWS_ON="0"',
                        'export TELEGRAM_ENABLED="1"',
                        'export DRY_RUN_MODE="0"',
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            result = integrity.config_check(runtime, wrapper)
        self.assertTrue(result["healthy"])
        self.assertEqual(result["sources"]["POLICY_B_ENABLED"], "watcher_wrapper")
        self.assertEqual(result["values"]["POLICY_B_SCORE_MIN"], "70")
        self.assertEqual(result["values"]["NEWS_ON"], "0")

    def test_watcher_export_precedence_matches_execution_order(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            runtime = root / ".env.runtime"
            wrapper = root / "run"
            runtime.write_text(
                "\n".join(
                    [
                        'PAIRS="EURUSD GBPUSD"',
                        'TIMEFRAMES="H1"',
                        'POLICY_B_ENABLED="0"',
                        'POLICY_B_SCORE_MIN="99"',
                        'POLICY_B_ADX_MAX="1"',
                        'NEWS_ON="1"',
                        'TELEGRAM_ENABLED="0"',
                        'DRY_RUN_MODE="1"',
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            wrapper.write_text(
                "\n".join(
                    [
                        'export PAIRS="EURUSD GBPUSD USDJPY"',
                        'export TIMEFRAMES="M15"',
                        'export POLICY_B_ENABLED="1"',
                        'export POLICY_B_SCORE_MIN="70"',
                        'export POLICY_B_ADX_MAX="30"',
                        'export NEWS_ON="0"',
                        'export TELEGRAM_ENABLED="1"',
                        'export DRY_RUN_MODE="0"',
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            result = integrity.config_check(runtime, wrapper)
        self.assertTrue(result["healthy"])
        self.assertTrue(
            all(source == "watcher_wrapper" for source in result["sources"].values())
        )

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


class ProgressTests(unittest.TestCase):
    @staticmethod
    def write_progress(root: Path, boot: str, now_ns: int) -> None:
        state = {
            "boot_id": boot,
            "components": {
                "updater": {
                    "status": "completed",
                    "monotonic_ns": now_ns - 200000 * 1_000_000_000,
                    "cycle_id": "u-old",
                    "event_id": "u1",
                },
                "shadow": {
                    "status": "failed",
                    "monotonic_ns": now_ns - 300 * 1_000_000_000,
                    "cycle_id": "s-failed",
                    "event_id": "s1",
                },
            },
        }
        (root / "state").mkdir()
        (root / "state/pipeline_progress.json").write_text(
            json.dumps(state), encoding="utf-8"
        )

    def test_closed_market_suspends_useful_progress_freshness_and_status(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            now_ns = 500000 * 1_000_000_000
            self.write_progress(root, "boot-a", now_ns)
            with (
                mock.patch.object(integrity.pipeline_health, "boot_id", return_value="boot-a"),
                mock.patch.object(
                    integrity.pipeline_health, "monotonic_ns", return_value=now_ns
                ),
            ):
                result = integrity.progress_check(root, market_open=False)
        self.assertTrue(result["healthy"])
        self.assertFalse(result["market_open"])
        self.assertEqual(
            result["components"]["shadow"]["evaluation"],
            "market_closed_freshness_suspended",
        )
        self.assertEqual(result["components"]["shadow"]["status"], "failed")

    def test_open_market_keeps_stale_and_failed_progress_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            now_ns = 500000 * 1_000_000_000
            self.write_progress(root, "boot-a", now_ns)
            with (
                mock.patch.object(integrity.pipeline_health, "boot_id", return_value="boot-a"),
                mock.patch.object(
                    integrity.pipeline_health, "monotonic_ns", return_value=now_ns
                ),
            ):
                result = integrity.progress_check(root, market_open=True)
        self.assertFalse(result["healthy"])
        self.assertTrue(result["market_open"])
        self.assertTrue(
            any(
                reason.startswith("updater_progress_stale_or_failed")
                for reason in result["failure_reasons"]
            )
        )
        self.assertTrue(
            any(
                reason.startswith("shadow_progress_stale_or_failed")
                for reason in result["failure_reasons"]
            )
        )

    def test_current_boot_is_still_required_when_market_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            now_ns = 500000 * 1_000_000_000
            self.write_progress(root, "old-boot", now_ns)
            with (
                mock.patch.object(integrity.pipeline_health, "boot_id", return_value="new-boot"),
                mock.patch.object(
                    integrity.pipeline_health, "monotonic_ns", return_value=now_ns
                ),
            ):
                result = integrity.progress_check(root, market_open=False)
        self.assertFalse(result["healthy"])
        self.assertIn("pipeline_progress_missing_for_current_boot", result["failure_reasons"])


class MarketGateTests(unittest.TestCase):
    def test_closed_market_is_valid_classification(self) -> None:
        clock = {"healthy": True, "server_epoch": 1786278888}
        completed = subprocess.CompletedProcess(
            ["bash", "market_open.sh"], 1, stdout="Closed\n", stderr=""
        )
        with mock.patch.object(integrity.subprocess, "run", return_value=completed):
            result = integrity.market_gate_check(Path("/x"), clock)
        self.assertTrue(result["healthy"])
        self.assertFalse(result["market_open"])
        self.assertEqual(result["status"], "Closed")

    def test_open_market_is_valid_classification(self) -> None:
        clock = {"healthy": True, "server_epoch": 1786345200}
        completed = subprocess.CompletedProcess(
            ["bash", "market_open.sh"], 0, stdout="Open\n", stderr=""
        )
        with mock.patch.object(integrity.subprocess, "run", return_value=completed):
            result = integrity.market_gate_check(Path("/x"), clock)
        self.assertTrue(result["healthy"])
        self.assertTrue(result["market_open"])

    def test_untrusted_clock_blocks_market_classification(self) -> None:
        result = integrity.market_gate_check(
            Path("/x"), {"healthy": False, "server_epoch": None}
        )
        self.assertFalse(result["healthy"])
        self.assertIsNone(result["market_open"])


class ThresholdTests(unittest.TestCase):
    def test_default_integer_threshold_is_returned(self) -> None:
        with mock.patch.dict(integrity.os.environ, {}, clear=True):
            self.assertEqual(integrity.env_int("EXAMPLE_THRESHOLD", "1500"), 1500)

    def test_malformed_threshold_becomes_integrity_error(self) -> None:
        with (
            mock.patch.dict(
                integrity.os.environ,
                {"MAX_UPDATER_PROGRESS_AGE_SECS": "not-an-int"},
                clear=False,
            ),
            self.assertRaisesRegex(
                integrity.IntegrityError,
                "invalid_threshold:MAX_UPDATER_PROGRESS_AGE_SECS",
            ),
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
