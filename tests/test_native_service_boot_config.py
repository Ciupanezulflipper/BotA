from __future__ import annotations

import unittest
from pathlib import Path

from tools import native_service_boot_config as boot


class BootConfigTests(unittest.TestCase):
    launcher = Path("/data/data/com.termux/files/home/BotA/tools/start_native_service_daemon_watchdog.sh")
    log_path = Path("/data/data/com.termux/files/home/BotA/logs/native_service_daemon_watchdog.boot.log")

    def render(self, text: str) -> str:
        return boot.render_boot_config(text, self.launcher, self.log_path)

    def test_appends_one_managed_block_when_legacy_guard_is_only_commented(self) -> None:
        source = "#!/bin/bash\n# RUNSVDIR_GUARD_START=DISABLED\n# start_runsvdir_guard.sh\n"
        rendered = self.render(source)
        self.assertEqual(rendered.count(boot.BEGIN), 1)
        self.assertEqual(rendered.count(boot.END), 1)
        self.assertEqual(rendered.count(str(self.launcher)), 1)
        self.assertIn("# start_runsvdir_guard.sh", rendered)

    def test_render_is_idempotent(self) -> None:
        first = self.render("#!/bin/bash\n")
        second = self.render(first)
        self.assertEqual(first, second)

    def test_replaces_existing_managed_block_without_duplication(self) -> None:
        source = (
            "#!/bin/bash\n"
            f"{boot.BEGIN}\n"
            '"/old/watchdog.sh" >> "/old/log" 2>&1\n'
            f"{boot.END}\n"
            "echo after\n"
        )
        rendered = self.render(source)
        self.assertNotIn("/old/watchdog.sh", rendered)
        self.assertEqual(rendered.count(str(self.launcher)), 1)
        self.assertIn("echo after", rendered)

    def test_rejects_active_legacy_guard(self) -> None:
        with self.assertRaisesRegex(boot.BootConfigError, "active_legacy_guard_present"):
            self.render("#!/bin/bash\n$HOME/BotA/tools/start_runsvdir_guard.sh\n")

    def test_rejects_unmanaged_active_watchdog(self) -> None:
        with self.assertRaisesRegex(
            boot.BootConfigError, "unmanaged_watchdog_launcher_present"
        ):
            self.render(
                "#!/bin/bash\n"
                "$HOME/BotA/tools/start_native_service_daemon_watchdog.sh\n"
            )

    def test_rejects_unbalanced_managed_block(self) -> None:
        with self.assertRaisesRegex(boot.BootConfigError, "managed_block_invalid"):
            self.render(f"#!/bin/bash\n{boot.BEGIN}\n")


if __name__ == "__main__":
    unittest.main()
