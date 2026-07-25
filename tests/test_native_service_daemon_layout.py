from __future__ import annotations

import ast
import unittest
from pathlib import Path


MIGRATION = Path("tools/native_service_daemon_migration.py")


class NativeServiceDaemonLayoutTests(unittest.TestCase):
    def test_migration_uses_packaged_termux_service_daemon_path(self) -> None:
        source = MIGRATION.read_text(encoding="utf-8")
        tree = ast.parse(source)
        matches: list[str] = []

        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign):
                continue
            if not any(
                isinstance(target, ast.Name) and target.id == "service_daemon"
                for target in node.targets
            ):
                continue
            matches.append(ast.unparse(node.value))

        self.assertEqual(matches, ["prefix / 'bin/service-daemon'"])
        self.assertNotIn("etc/init.d/service-daemon", source)


if __name__ == "__main__":
    unittest.main()
