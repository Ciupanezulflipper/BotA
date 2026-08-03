#!/usr/bin/env python3
"""Regression tests for the unified BotA heartbeat runtime."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import heartbeat_runtime


ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "tools" / "heartbeat.sh"
SERVICE = ROOT / "services" / "bota-heartbeat" / "run"
SERVER_EPOCH = 1_775_000_000


def write_health(root: Path) -> None:
    path = root / "state" / "runtime_health.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "bot_mode": "HEALTHY",
                "market_state": "open",
                "failure_reasons": [],
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


def write_credentials(root: Path) -> None:
    path = root / ".env.runtime"
    path.write_text(
        "TELEGRAM_BOT_TOKEN=unit-test-token\n"
        "TELEGRAM_CHAT_ID=unit-test-chat\n",
        encoding="utf-8",
    )


def write_progress(root: Path, boot_id: str, value: float) -> None:
    path = root / "state" / "shadow_progress.monotonic"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{boot_id} {value}\n", encoding="utf-8")


def write_bucket(root: Path) -> None:
    path = root / "logs" / "state" / "heartbeat_utc_bucket.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        heartbeat_runtime.utc_bucket(SERVER_EPOCH) + "\n",
        encoding="utf-8",
    )


class HeartbeatRuntimeSourcePolicyTests(unittest.TestCase):
    """Protect the active wrappers from embedded transport or topology mutation."""

    def test_launcher_and_service_delegate_to_one_runtime(self) -> None:
        launcher = LAUNCHER.read_text(encoding="utf-8")
        service = SERVICE.read_text(encoding="utf-8")
        executable_service = "\n".join(
            line for line in service.splitlines()
            if not line.lstrip().startswith("#")
        )

        self.assertIn("heartbeat_runtime.py", launcher)
        self.assertIn("heartbeat_delivery.py", launcher)
        self.assertIn('SCRIPT="${ROOT}/tools/heartbeat.sh"', service)
        self.assertIn('BOTA_ROOT="${ROOT}" bash "${SCRIPT}"', service)
        self.assertNotIn("bota_heartbeat_utc.sh", service)
        self.assertNotIn("curl", launcher + service)
        self.assertNotIn("api.telegram.org", launcher + service)
        for token in (
            "runsvdir ",
            "runsv ",
            "sv up",
            "sv down",
            "sv restart",
            "pkill",
            "killall",
        ):
            with self.subTest(token=token):
                self.assertNotIn(token, executable_service)


class HeartbeatRuntimeValueTests(unittest.TestCase):
    """Verify UTC and monotonic value handling."""

    def test_configured_server_epoch_avoids_network(self) -> None:
        with (
            patch.dict(
                os.environ,
                {"HEARTBEAT_SERVER_EPOCH": str(SERVER_EPOCH)},
                clear=False,
            ),
            patch.object(
                heartbeat_runtime.http.client,
                "HTTPSConnection",
            ) as connection,
        ):
            value, sources = heartbeat_runtime.authoritative_server_epoch()

        self.assertEqual(value, SERVER_EPOCH)
        self.assertEqual(sources, 1)
        connection.assert_not_called()

    def test_progress_age_rejects_boot_change_and_future_value(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "progress"
            path.write_text("boot-a 100\n", encoding="utf-8")
            changed = heartbeat_runtime.progress_age_seconds(path, "boot-b", 200.0)
            future = heartbeat_runtime.progress_age_seconds(path, "boot-a", 50.0)

        self.assertEqual(changed, ("boot_changed", None))
        self.assertEqual(future, ("invalid", None))


class HeartbeatRuntimeCycleTests(unittest.TestCase):
    """Exercise heartbeat, retry, deadman, and recovery state transitions."""

    def test_heartbeat_sends_once_per_authoritative_utc_bucket(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "BotA"
            write_health(root)
            write_credentials(root)
            write_progress(root, "boot-a", 100.0)
            with (
                patch.dict(
                    os.environ,
                    {"HEARTBEAT_SERVER_EPOCH": str(SERVER_EPOCH)},
                    clear=False,
                ),
                patch.object(heartbeat_runtime.time, "monotonic", side_effect=[100.0, 101.0]),
                patch.object(
                    heartbeat_runtime.delivery,
                    "boot_identity",
                    return_value="boot-a",
                ),
                patch.object(
                    heartbeat_runtime.delivery,
                    "send_telegram",
                    return_value=(True, "http_status:200"),
                ) as sender,
            ):
                first = heartbeat_runtime.run_cycle(root)
                second = heartbeat_runtime.run_cycle(root)

            bucket = (
                root / "logs" / "state" / "heartbeat_utc_bucket.txt"
            ).read_text(encoding="utf-8").strip()
            log = (root / "logs" / "cron.heartbeat.log").read_text(encoding="utf-8")

        self.assertEqual(first, 0)
        self.assertEqual(second, 0)
        self.assertEqual(bucket, heartbeat_runtime.utc_bucket(SERVER_EPOCH))
        sender.assert_called_once()
        self.assertIn("HB_UTC_RESULT=PASS", log)
        self.assertIn("HB_UTC_RESULT=BUCKET_UNCHANGED", log)
        self.assertIn("DEADMAN_UTC_RESULT=HEALTHY", log)

    def test_failed_heartbeat_uses_monotonic_backoff(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "BotA"
            write_health(root)
            write_credentials(root)
            write_progress(root, "boot-a", 100.0)
            with (
                patch.dict(
                    os.environ,
                    {"HEARTBEAT_SERVER_EPOCH": str(SERVER_EPOCH)},
                    clear=False,
                ),
                patch.object(heartbeat_runtime.time, "monotonic", side_effect=[100.0, 101.0]),
                patch.object(
                    heartbeat_runtime.delivery,
                    "boot_identity",
                    return_value="boot-a",
                ),
                patch.object(
                    heartbeat_runtime.delivery,
                    "send_telegram",
                    return_value=(False, "timeout"),
                ) as sender,
            ):
                heartbeat_runtime.run_cycle(root)
                heartbeat_runtime.run_cycle(root)

            state = heartbeat_runtime.delivery.load_state(
                root / "state" / "heartbeat_delivery.json"
            )
            log = (root / "logs" / "cron.heartbeat.log").read_text(encoding="utf-8")

        sender.assert_called_once()
        self.assertTrue(state["delivery_failure"])
        self.assertEqual(state["consecutive_failures"], 1)
        self.assertEqual(state["next_retry_monotonic"], 400.0)
        self.assertIn("HB_UTC_RESULT=DELIVERY_FAILED", log)
        self.assertIn("HB_UTC_RESULT=RETRY_SUPPRESSED", log)

    def test_stale_progress_sends_deadman_and_creates_flag(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "BotA"
            write_health(root)
            write_credentials(root)
            write_bucket(root)
            write_progress(root, "boot-a", 0.0)
            with (
                patch.dict(
                    os.environ,
                    {"HEARTBEAT_SERVER_EPOCH": str(SERVER_EPOCH)},
                    clear=False,
                ),
                patch.object(heartbeat_runtime.time, "monotonic", return_value=6000.0),
                patch.object(
                    heartbeat_runtime.delivery,
                    "boot_identity",
                    return_value="boot-a",
                ),
                patch.object(
                    heartbeat_runtime.delivery,
                    "send_telegram",
                    return_value=(True, "http_status:200"),
                ) as sender,
            ):
                result = heartbeat_runtime.run_cycle(root)

            flag = root / "logs" / "state" / "deadman.flag"
            flag_exists = flag.exists()
            log = (root / "logs" / "cron.heartbeat.log").read_text(encoding="utf-8")

        self.assertEqual(result, 0)
        sender.assert_called_once()
        self.assertIn("DEADMAN", sender.call_args.args[2])
        self.assertTrue(flag_exists)
        self.assertIn("DEADMAN_UTC_RESULT=ALERT_SENT", log)

    def test_fresh_progress_sends_recovery_and_removes_flag(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "BotA"
            write_health(root)
            write_credentials(root)
            write_bucket(root)
            write_progress(root, "boot-a", 5999.0)
            flag = root / "logs" / "state" / "deadman.flag"
            flag.parent.mkdir(parents=True, exist_ok=True)
            flag.write_text("active\n", encoding="utf-8")
            with (
                patch.dict(
                    os.environ,
                    {"HEARTBEAT_SERVER_EPOCH": str(SERVER_EPOCH)},
                    clear=False,
                ),
                patch.object(heartbeat_runtime.time, "monotonic", return_value=6000.0),
                patch.object(
                    heartbeat_runtime.delivery,
                    "boot_identity",
                    return_value="boot-a",
                ),
                patch.object(
                    heartbeat_runtime.delivery,
                    "send_telegram",
                    return_value=(True, "http_status:200"),
                ) as sender,
            ):
                result = heartbeat_runtime.run_cycle(root)

            flag_exists = flag.exists()
            log = (root / "logs" / "cron.heartbeat.log").read_text(encoding="utf-8")

        self.assertEqual(result, 0)
        sender.assert_called_once()
        self.assertIn("RECOVERY", sender.call_args.args[2])
        self.assertFalse(flag_exists)
        self.assertIn("DEADMAN_UTC_RESULT=RECOVERY_SENT", log)

    def test_dry_run_never_calls_telegram_or_mutates_delivery_state(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "BotA"
            write_health(root)
            write_progress(root, "boot-a", 0.0)
            with (
                patch.dict(
                    os.environ,
                    {
                        "HEARTBEAT_SERVER_EPOCH": str(SERVER_EPOCH),
                        "HEARTBEAT_DRY_RUN": "1",
                    },
                    clear=False,
                ),
                patch.object(heartbeat_runtime.time, "monotonic", return_value=6000.0),
                patch.object(
                    heartbeat_runtime.delivery,
                    "boot_identity",
                    return_value="boot-a",
                ),
                patch.object(
                    heartbeat_runtime.delivery,
                    "send_telegram",
                ) as sender,
            ):
                result = heartbeat_runtime.run_cycle(root)

            delivery_files = list((root / "state").glob("*_delivery.json"))
            bucket_exists = (
                root / "logs" / "state" / "heartbeat_utc_bucket.txt"
            ).exists()
            flag_exists = (root / "logs" / "state" / "deadman.flag").exists()

        self.assertEqual(result, 0)
        sender.assert_not_called()
        self.assertEqual(delivery_files, [])
        self.assertFalse(bucket_exists)
        self.assertFalse(flag_exists)


if __name__ == "__main__":
    unittest.main()
