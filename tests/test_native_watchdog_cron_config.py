from __future__ import annotations

import unittest
from pathlib import Path

from tools import native_watchdog_cron_config as cron


class WatchdogCronConfigTests(unittest.TestCase):
    def render(self, text: str) -> str:
        return cron.render_crontab(
            text,
            python=Path("/prefix/bin/python3"),
            guard=Path("/home/BotA/tools/native_watchdog_guard.py"),
            root=Path("/home/BotA"),
            log=Path("/home/BotA/logs/native_watchdog_guard.cron.log"),
        )

    def test_adds_one_managed_guard_block(self) -> None:
        rendered = self.render("0 0 * * * echo daily\n")
        self.assertEqual(rendered.count(cron.BEGIN), 1)
        self.assertEqual(rendered.count(cron.END), 1)
        self.assertEqual(rendered.count("native_watchdog_guard.py"), 1)
        self.assertIn("--ensure", rendered)
        self.assertIn("0 0 * * * echo daily", rendered)

    def test_render_is_idempotent(self) -> None:
        first = self.render("")
        second = self.render(first)
        self.assertEqual(first, second)

    def test_replaces_existing_managed_block(self) -> None:
        old = (
            f"{cron.BEGIN}\n"
            "* * * * * old-native_watchdog_guard.py --ensure\n"
            f"{cron.END}\n"
        )
        rendered = self.render(old)
        self.assertEqual(rendered.count("native_watchdog_guard.py"), 1)
        self.assertNotIn("old-native_watchdog_guard.py", rendered)

    def test_refuses_unmanaged_active_guard(self) -> None:
        text = "* * * * * python native_watchdog_guard.py --ensure\n"
        with self.assertRaisesRegex(cron.CronConfigError, "unmanaged_guard_present"):
            self.render(text)

    def test_commented_historical_guard_is_allowed(self) -> None:
        rendered = self.render("# native_watchdog_guard.py old note\n")
        self.assertIn("# native_watchdog_guard.py old note", rendered)
        self.assertEqual(
            sum(
                1
                for line in rendered.splitlines()
                if "native_watchdog_guard.py" in line
                and line.strip()
                and not line.lstrip().startswith("#")
            ),
            1,
        )

    def test_refuses_malformed_managed_markers(self) -> None:
        with self.assertRaisesRegex(cron.CronConfigError, "managed_block_invalid"):
            self.render(f"{cron.END}\n{cron.BEGIN}\n")


if __name__ == "__main__":
    unittest.main()
