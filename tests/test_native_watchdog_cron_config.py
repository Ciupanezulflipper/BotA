from __future__ import annotations

import shlex
import unittest
from pathlib import Path

from tools import native_watchdog_cron_config as cron


class WatchdogCronConfigTests(unittest.TestCase):
    @staticmethod
    def render(
        text: str,
        *,
        python: Path = Path("/prefix/bin/python3"),
        guard: Path = Path("/home/BotA/tools/native_watchdog_guard.py"),
        root: Path = Path("/home/BotA"),
        log: Path = Path("/home/BotA/logs/native_watchdog_guard.cron.log"),
    ) -> str:
        return cron.render_crontab(
            text, python=python, guard=guard, root=root, log=log
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

    def test_rejects_paths_containing_carriage_return(self) -> None:
        with self.assertRaisesRegex(cron.CronConfigError, "path_contains_newline"):
            self.render("", root=Path("/home/BotA\rrm -rf /"))

    def test_rejects_paths_containing_newline(self) -> None:
        with self.assertRaisesRegex(cron.CronConfigError, "path_contains_newline"):
            self.render("", log=Path("/tmp/log\nrm -rf /"))

    def test_paths_with_shell_metacharacters_are_quoted(self) -> None:
        tricky = Path("/tmp/has space and $var and \"quote\"")
        rendered = self.render("", root=tricky)
        managed = [
            line
            for line in rendered.splitlines()
            if "native_watchdog_guard.py" in line
            and not line.lstrip().startswith("#")
        ]
        self.assertEqual(len(managed), 1)
        expected = shlex.quote(str(tricky))
        self.assertIn(f"cd {expected}", managed[0])

    def test_paths_with_single_quote_are_shell_quoted(self) -> None:
        awkward = Path("/tmp/it's-fine")
        rendered = self.render("", guard=awkward)
        quoted = shlex.quote(str(awkward))
        managed = [
            line for line in rendered.splitlines() if quoted in line
        ]
        self.assertEqual(len(managed), 1)
        # shlex.quote wraps single-quoted segments and escapes embedded
        # apostrophes; the literal path substring must not appear naked.
        self.assertNotIn(" /tmp/it's-fine ", managed[0])


if __name__ == "__main__":
    unittest.main()
