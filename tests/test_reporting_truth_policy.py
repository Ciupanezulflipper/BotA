#!/usr/bin/env python3
"""Regression tests for BotA daily reporting truth and schedule verification."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DAILY_SUMMARY = ROOT / "tools" / "daily_summary.sh"
VERIFY_CRON = ROOT / "tools" / "verify_canonical_crontab.sh"
CANONICAL_CRON = ROOT / "ops" / "bota_crontab.canonical"


def prepare_runtime(base: Path) -> Path:
    """Create an isolated BotA runtime with authoritative healthy state."""
    root = base / "BotA"
    for directory in (
        root / "logs",
        root / "state",
        root / "config",
        root / "tools",
        root / "ops",
    ):
        directory.mkdir(parents=True, exist_ok=True)

    shutil.copy2(VERIFY_CRON, root / "tools" / "verify_canonical_crontab.sh")
    shutil.copy2(CANONICAL_CRON, root / "ops" / "bota_crontab.canonical")

    (root / "state" / "runtime_health.json").write_text(
        json.dumps(
            {
                "schema_version": "2.1",
                "bot_mode": "HEALTHY",
                "last_supervisor_run_utc": "2026-08-06T20:00:00+00:00",
                "failure_reasons": [],
                "market_state": "closed",
                "market_gate": {
                    "state": "closed",
                    "reason": "market_closed",
                },
                "control_plane": {
                    "healthy": True,
                    "owned": 7,
                    "required": 7,
                },
                "pipeline_progress": {
                    "healthy": True,
                    "market_open": False,
                    "failure_reasons": [],
                    "components": {
                        "market": {
                            "healthy": True,
                            "status": "closed",
                        }
                    },
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    (root / "state" / "provider_usage.json").write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "utc_date": "2026-08-06",
                "providers": {
                    "oanda": {
                        "requests": 10,
                        "successes": 10,
                        "failures": 0,
                        "credits_consumed": 0,
                    },
                    "yahoo": {
                        "requests": 2,
                        "successes": 1,
                        "failures": 1,
                        "credits_consumed": 0,
                    },
                    "twelvedata": {
                        "requests": 0,
                        "successes": 0,
                        "failures": 0,
                        "credits_consumed": 0,
                    },
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    (root / "logs" / "clock_drift_status.json").write_text(
        json.dumps(
            {
                "status": "DRIFT_WARN",
                "drift_seconds": -3600,
                "server_clock_ok": True,
                "local_clock_unsafe": True,
            }
        )
        + "\n",
        encoding="utf-8",
    )

    return root


def run_daily_summary(root: Path, cron_source: Path) -> subprocess.CompletedProcess[str]:
    """Run the production summary without Telegram or provider calls."""
    environment = os.environ.copy()
    environment.update(
        {
            "BOTA_ROOT": str(root),
            "SUMMARY_DATE": "2026-08-06",
            "DAILY_SUMMARY_SEND": "0",
            "CRONTAB_SOURCE_FILE": str(cron_source),
            "RUNTIME_HEALTH_FRESH_MAX_MIN": "9999999",
        }
    )
    return subprocess.run(
        ["bash", str(DAILY_SUMMARY)],
        cwd=ROOT,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )


class ReportingTruthSourceTests(unittest.TestCase):
    """Prevent legacy counters and cron-log freshness from returning."""

    def test_daily_summary_uses_provider_specific_state(self) -> None:
        source = DAILY_SUMMARY.read_text(encoding="utf-8")
        self.assertIn('PROVIDER_USAGE = STATE / "provider_usage.json"', source)
        self.assertNotIn("api_credits.json", source.split("SUMMARY=", 1)[-1])
        self.assertNotIn("API usage:", source)
        self.assertIn("Provider usage:", source)

    def test_daily_summary_does_not_degrade_from_job_log_age(self) -> None:
        source = DAILY_SUMMARY.read_text(encoding="utf-8")
        self.assertNotIn("RUNTIME_JOB_FRESH_MAX_MIN", source)
        self.assertNotIn("closer stale:", source)
        self.assertNotIn("shadow stale:", source)
        self.assertIn("freshness checks correctly suspended", source)

    def test_canonical_schedule_records_core_runit_migrations(self) -> None:
        source = CANONICAL_CRON.read_text(encoding="utf-8")
        for component in (
            "signal_watcher_pro.sh",
            "run_shadow_manager.sh",
            "indicators_updater.sh",
            "heartbeat.sh",
            "bota_supervisor.sh",
            "run_signal_closer_live.sh",
        ):
            with self.subTest(component=component):
                matching = [
                    line
                    for line in source.splitlines()
                    if component in line
                ]
                self.assertEqual(len(matching), 1)
                self.assertTrue(matching[0].startswith("#MIGRATED_TO_RUNIT "))


class ReportingTruthBehaviorTests(unittest.TestCase):
    """Exercise the exact false-degraded and false-quota production cases."""

    def test_market_closed_healthy_runtime_stays_healthy(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = prepare_runtime(Path(temporary))
            cron_source = root / "live.crontab"
            cron_source.write_text(
                "# unrelated block\n" + CANONICAL_CRON.read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            result = run_daily_summary(root, cron_source)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Runtime: ✅ HEALTHY | reported=HEALTHY", result.stdout)
        self.assertIn(
            "Pipeline jobs: market closed — freshness checks correctly suspended",
            result.stdout,
        )
        self.assertIn("Runtime schedule: ✅ PASS | hash=YES", result.stdout)
        self.assertIn("Reasons: none", result.stdout)
        self.assertNotIn("closer stale", result.stdout)
        self.assertNotIn("shadow stale", result.stdout)

    def test_provider_requests_are_not_twelve_data_credits(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = prepare_runtime(Path(temporary))
            cron_source = root / "live.crontab"
            cron_source.write_text(CANONICAL_CRON.read_text(encoding="utf-8"), encoding="utf-8")
            result = run_daily_summary(root, cron_source)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(
            "Provider usage: OANDA 10 req | Yahoo 2 req | Twelve Data 0/800 credits",
            result.stdout,
        )
        self.assertNotIn("10/800", result.stdout)
        self.assertNotIn("12/800", result.stdout)

    def test_verifier_rejects_active_duplicate_of_migrated_job(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = prepare_runtime(Path(temporary))
            cron_source = root / "live.crontab"
            canonical = CANONICAL_CRON.read_text(encoding="utf-8")
            duplicate = next(
                line.removeprefix("#MIGRATED_TO_RUNIT ")
                for line in canonical.splitlines()
                if "signal_watcher_pro.sh" in line
            )
            cron_source.write_text(canonical + duplicate + "\n", encoding="utf-8")

            environment = os.environ.copy()
            environment.update(
                {
                    "BOTA_ROOT": str(root),
                    "CRONTAB_SOURCE_FILE": str(cron_source),
                }
            )
            result = subprocess.run(
                ["bash", str(root / "tools" / "verify_canonical_crontab.sh")],
                env=environment,
                text=True,
                capture_output=True,
                check=False,
                timeout=30,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("signal_watcher_pro.sh MIGRATED_COUNT=1 ACTIVE_COUNT=1", result.stdout)
        self.assertIn("PHASE2_VERIFY_PASS=NO", result.stdout)


if __name__ == "__main__":
    unittest.main()
