from __future__ import annotations

import os
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCORING = ROOT / "tools" / "scoring_engine.sh"
MARKET_GATE = ROOT / "tools" / "market_open.sh"


class ScoringMarketPhaseInvocationTests(unittest.TestCase):
    def test_scoring_engine_invokes_termux_shebang_gate_through_bash(self) -> None:
        source = SCORING.read_text(encoding="utf-8")

        correct_with_epoch_file = (
            'BOTA_SERVER_EPOCH_FILE="$_market_epoch_file" '
            'bash "${TOOLS}/market_open.sh"'
        )
        correct_without_epoch_file = 'bash "${TOOLS}/market_open.sh" 2>/dev/null || true'

        broken_with_epoch_file = (
            'BOTA_SERVER_EPOCH_FILE="$_market_epoch_file" '
            '"${TOOLS}/market_open.sh"'
        )
        broken_without_epoch_file = '_raw="$("${TOOLS}/market_open.sh" 2>/dev/null || true)"'

        self.assertIn(correct_with_epoch_file, source)
        self.assertIn(correct_without_epoch_file, source)
        self.assertNotIn(broken_with_epoch_file, source)
        self.assertNotIn(broken_without_epoch_file, source)

    def test_explicit_bash_gate_returns_open_for_known_market_timestamp(self) -> None:
        environment = os.environ.copy()
        environment["BOTA_SERVER_EPOCH"] = "1791883803"  # 2026-10-13 09:30:03 UTC
        result = subprocess.run(
            ["bash", str(MARKET_GATE)],
            cwd=ROOT,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
            timeout=5,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "Open")


if __name__ == "__main__":
    unittest.main()
