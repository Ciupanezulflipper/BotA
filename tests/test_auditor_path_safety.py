#!/usr/bin/env python3
"""Regression tests for auditor CLI path containment."""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDITOR = ROOT / "tools" / "auditor.py"
HEADER = "timestamp,action,pair,tf,entry_price,stop_loss,tp1,tp2,tp3\n"


class AuditorPathSafetyTests(unittest.TestCase):
    @staticmethod
    def run_auditor(*arguments: str) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary) / "home"
            bota = home / "BotA"
            bota.mkdir(parents=True)
            (bota / "signals.csv").write_text(HEADER, encoding="utf-8")
            (home / "escape.csv").write_text(HEADER, encoding="utf-8")
            environment = os.environ.copy()
            environment["HOME"] = str(home)
            return subprocess.run(
                [sys.executable, str(AUDITOR), *arguments],
                cwd=ROOT,
                env=environment,
                text=True,
                capture_output=True,
                check=False,
                timeout=30,
            )

    def test_signals_path_cannot_escape_bota_directory(self) -> None:
        completed = self.run_auditor("--signals", "../escape.csv")
        self.assertEqual(completed.returncode, 2, completed.stderr)
        self.assertIn("path must stay within", completed.stderr)

    def test_output_path_is_validated_before_processing(self) -> None:
        completed = self.run_auditor("--out", "../escape-output.csv")
        self.assertEqual(completed.returncode, 2, completed.stderr)
        self.assertIn("path must stay within", completed.stderr)


if __name__ == "__main__":
    unittest.main()
