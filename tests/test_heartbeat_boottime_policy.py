#!/usr/bin/env python3
"""Regression tests for Android boot-time heartbeat and shadow progress."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import heartbeat_boottime
from tools import heartbeat_runtime


ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "tools" / "heartbeat.sh"
SHADOW_SERVICE = ROOT / "services" / "bota-shadow" / "run"


class HeartbeatBootTimeSourcePolicyTests(unittest.TestCase):
    """Keep the launcher and shadow producer in one explicit clock domain."""

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

        def fake_cycle(root: Path) -> int:
            self.assertEqual(root, Path("/tmp/BotA"))
            self.assertEqual(
                heartbeat_boottime.heartbeat_runtime.time.monotonic(),
                700_000.0,
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


if __name__ == "__main__":
    unittest.main()
