#!/usr/bin/env python3
"""Tests for the runit updater market gate."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SERVICE_RUN = REPOSITORY_ROOT / "services" / "bota-updater" / "run"


class UpdaterMarketGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "BotA"

        for directory in (
            self.root / "tools",
            self.root / "logs",
            self.root / "state",
        ):
            directory.mkdir(parents=True, exist_ok=True)

        self.marker = self.root / "state" / "updater_called.txt"
        self.gate = self.root / "tools" / "market_open.sh"
        self.updater = self.root / "tools" / "indicators_updater.sh"

        self.updater.write_text(
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            f"printf 'called\\n' > {self.marker!s}\n",
            encoding="utf-8",
        )
        self.updater.chmod(0o755)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write_gate(self, exit_code: int) -> None:
        self.gate.write_text(
            "#!/usr/bin/env bash\n"
            f"exit {exit_code}\n",
            encoding="utf-8",
        )
        self.gate.chmod(0o755)

    def run_service_once(self) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment.update(
            {
                "BOTA_ROOT": str(self.root),
                "BOTA_UPDATER_RUN_ONCE": "1",
                "BOTA_UPDATER_INTERVAL": "5",
            }
        )

        return subprocess.run(
            ["bash", str(SERVICE_RUN)],
            cwd=REPOSITORY_ROOT,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )

    def test_closed_market_does_not_run_updater(self) -> None:
        self.write_gate(1)

        result = self.run_service_once()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.marker.exists())
        self.assertIn(
            "SKIP: market_closed_or_clock_unavailable",
            result.stdout,
        )

    def test_open_market_runs_updater(self) -> None:
        self.write_gate(0)

        result = self.run_service_once()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(self.marker.exists())
        self.assertIn("RUN_ONCE_COMPLETE", result.stdout)

    def test_missing_market_gate_fails_closed(self) -> None:
        if self.gate.exists():
            self.gate.unlink()

        result = self.run_service_once()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.marker.exists())
        self.assertIn(
            "SKIP: market_gate_missing_or_not_executable",
            result.stdout,
        )


if __name__ == "__main__":
    unittest.main()
