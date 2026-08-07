#!/usr/bin/env python3
"""Regression tests for Android boot-time and signal-first heartbeat policy."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import heartbeat_boottime
from tools import heartbeat_runtime


ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "tools" / "heartbeat.sh"
SHADOW_SERVICE = ROOT / "services" / "bota-shadow" / "run"
SERVER_EPOCH = 1_775_000_000


def write_progress(root: Path, boot_id: str, value: float) -> None:
    """Write one isolated shadow progress record."""
    path = root / "state" / "shadow_progress.monotonic"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{boot_id} {value}\n", encoding="utf-8")


def write_credentials(root: Path) -> None:
    """Write non-secret Telegram test credentials."""
    (root / ".env.runtime").write_text(
        "TELEGRAM_BOT_TOKEN=unit-test-token\n"
        "TELEGRAM_CHAT_ID=unit-test-chat\n",
        encoding="utf-8",
    )


class HeartbeatBootTimeSourcePolicyTests(unittest.TestCase):
    """Keep the launcher, producer, and notification policy explicit."""

    def test_launcher_uses_boot_time_adapter(self) -> None:
        source = LAUNCHER.read_text(encoding="utf-8")
        self.assertIn("heartbeat_boottime.py", source)
        self.assertIn("heartbeat_runtime.py", source)
        self.assertIn("heartbeat_delivery.py", source)

    def test_shadow_service_writes_progress_only_after_success(self) -> None:
        source = SHADOW_SERVICE.read_text(encoding="utf-8")
        executable = "\n".join(
            line for line in source.splitlines()
            if not line.lstrip().startswith("#")
        )

        self.assertIn("CLOCK_BOOTTIME", source)
        self.assertIn("shadow_progress.monotonic", source)
        self.assertIn("mark_shadow_progress", source)
        self.assertIn("if timeout", executable)
        self.assertIn("then\n      mark_shadow_progress", executable)

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
                self.assertNotIn(token, executable)

    def test_adapter_declares_routine_heartbeat_local_only(self) -> None:
        source = (ROOT / "tools" / "heartbeat_boottime.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("HB_UTC_RESULT=LOG_ONLY", source)
        self.assertIn("record_local_heartbeat", source)
        self.assertNotIn("send_telegram", source)
        self.assertNotIn("api.telegram.org", source)


class HeartbeatBootTimeValueTests(unittest.TestCase):
    """Verify boot-time selection and the proven Android suspend case."""

    def test_boot_time_clock_prefers_clock_boottime(self) -> None:
        with (
            patch.object(
                heartbeat_boottime.time,
                "CLOCK_BOOTTIME",
                123,
                create=True,
            ),
            patch.object(
                heartbeat_boottime.time,
                "clock_gettime",
                return_value=689_098.25,
            ) as getter,
            patch.object(heartbeat_boottime.time, "monotonic") as fallback,
        ):
            value = heartbeat_boottime._BootTimeClock.monotonic()

        self.assertEqual(value, 689_098.25)
        getter.assert_called_once_with(123)
        fallback.assert_not_called()

    def test_proven_suspend_gap_is_valid_in_boot_time_domain(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "shadow_progress.monotonic"
            path.write_text("boot-a 622925\n", encoding="utf-8")
            result = heartbeat_runtime.progress_age_seconds(
                path,
                "boot-a",
                689_098.202150225,
            )

        self.assertEqual(result[0], "valid")
        self.assertAlmostEqual(result[1] or 0.0, 66_173.20215022506)

    def test_adapter_is_process_local_and_restored(self) -> None:
        original_clock = heartbeat_boottime.heartbeat_runtime.time
        original_heartbeat = heartbeat_boottime.heartbeat_runtime.handle_heartbeat

        def fake_cycle(root: Path) -> int:
            self.assertEqual(root, Path("/tmp/BotA"))
            self.assertEqual(
                heartbeat_boottime.heartbeat_runtime.time.monotonic(),
                700_000.0,
            )
            self.assertIs(
                heartbeat_boottime.heartbeat_runtime.handle_heartbeat,
                heartbeat_boottime.record_local_heartbeat,
            )
            return 0

        with (
            patch.object(
                heartbeat_boottime._BootTimeClock,
                "monotonic",
                return_value=700_000.0,
            ),
            patch.object(
                heartbeat_boottime.heartbeat_runtime,
                "run_cycle",
                side_effect=fake_cycle,
            ) as runner,
        ):
            result = heartbeat_boottime.run(Path("/tmp/BotA"))

        self.assertEqual(result, 0)
        runner.assert_called_once_with(Path("/tmp/BotA"))
        self.assertIs(heartbeat_boottime.heartbeat_runtime.time, original_clock)
        self.assertIs(
            heartbeat_boottime.heartbeat_runtime.handle_heartbeat,
            original_heartbeat,
        )


class SignalFirstHeartbeatBehaviorTests(unittest.TestCase):
    """Prove routine evidence stays local while critical alerts still deliver."""

    def test_routine_heartbeat_records_bucket_without_telegram(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "BotA"
            write_progress(root, "boot-a", 100.0)

            with (
                patch.object(
                    heartbeat_runtime,
                    "authoritative_server_epoch",
                    return_value=(SERVER_EPOCH, 3),
                ),
                patch.object(
                    heartbeat_runtime.delivery,
                    "boot_identity",
                    return_value="boot-a",
                ),
                patch.object(
                    heartbeat_boottime._BootTimeClock,
                    "monotonic",
                    return_value=100.0,
                ),
                patch.object(
                    heartbeat_runtime.delivery,
                    "send_telegram",
                ) as sender,
            ):
                first = heartbeat_boottime.run(root)
                second = heartbeat_boottime.run(root)

            bucket = (
                root / "logs" / "state" / "heartbeat_utc_bucket.txt"
            ).read_text(encoding="utf-8").strip()
            log = (root / "logs" / "cron.heartbeat.log").read_text(
                encoding="utf-8"
            )
            heartbeat_state_exists = (
                root / "state" / "heartbeat_delivery.json"
            ).exists()

        self.assertEqual(first, 0)
        self.assertEqual(second, 0)
        self.assertEqual(bucket, heartbeat_runtime.utc_bucket(SERVER_EPOCH))
        sender.assert_not_called()
        self.assertFalse(heartbeat_state_exists)
        self.assertIn("HB_UTC_RESULT=LOG_ONLY sources=3", log)
        self.assertIn("HB_UTC_RESULT=BUCKET_UNCHANGED", log)
        self.assertIn("DEADMAN_UTC_RESULT=HEALTHY", log)

    def test_stale_progress_still_sends_one_deadman_alert(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "BotA"
            write_progress(root, "boot-a", 0.0)
            write_credentials(root)

            with (
                patch.object(
                    heartbeat_runtime,
                    "authoritative_server_epoch",
                    return_value=(SERVER_EPOCH, 3),
                ),
                patch.object(
                    heartbeat_runtime.delivery,
                    "boot_identity",
                    return_value="boot-a",
                ),
                patch.object(
                    heartbeat_boottime._BootTimeClock,
                    "monotonic",
                    return_value=6000.0,
                ),
                patch.object(
                    heartbeat_runtime.delivery,
                    "send_telegram",
                    return_value=(True, "http_status:200"),
                ) as sender,
            ):
                result = heartbeat_boottime.run(root)

            flag_exists = (root / "logs" / "state" / "deadman.flag").exists()
            state = json.loads(
                (root / "state" / "deadman_delivery.json").read_text(
                    encoding="utf-8"
                )
            )
            log = (root / "logs" / "cron.heartbeat.log").read_text(
                encoding="utf-8"
            )

        self.assertEqual(result, 0)
        sender.assert_called_once()
        self.assertIn("DEADMAN", sender.call_args.args[2])
        self.assertTrue(flag_exists)
        self.assertFalse(state["delivery_failure"])
        self.assertIn("HB_UTC_RESULT=LOG_ONLY", log)
        self.assertIn("DEADMAN_UTC_RESULT=ALERT_SENT", log)


if __name__ == "__main__":
    unittest.main()
