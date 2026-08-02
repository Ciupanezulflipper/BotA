#!/usr/bin/env python3
"""Source-policy regression for supervisor clock-helper failure containment."""

from __future__ import annotations

import unittest
from pathlib import Path


SUPERVISOR = Path(__file__).resolve().parents[1] / "tools" / "bota_supervisor.sh"


class SupervisorClockHelperFailurePolicyTests(unittest.TestCase):
    """Ensure helper failure cannot erase runtime observability."""

    def test_helper_failure_has_complete_nonfatal_fallback(self) -> None:
        source = SUPERVISOR.read_text(encoding="utf-8")

        required = (
            "clock_status_rc=0",
            "|| clock_status_rc=$?",
            "CLOCK_STATUS_TOOL_FAILED: rc=${clock_status_rc}",
            '"state": "error"',
            '"reason": "clock_status_tool_failed"',
            '"status": "TOOL_FAILED"',
            '"runtime_failure": false',
            'print(str(market_gate.get("state") or "error"))',
            "--market-closed",
        )
        for marker in required:
            with self.subTest(marker=marker):
                self.assertIn(marker, source)

        helper_position = source.index('python3 "${TOOLS}/supervisor_clock_status.py"')
        fallback_position = source.index("if (( clock_status_rc != 0 )); then")
        pipeline_position = source.index('if [ "${market_state}" = "open" ]; then')
        self.assertLess(helper_position, fallback_position)
        self.assertLess(fallback_position, pipeline_position)


if __name__ == "__main__":
    unittest.main()
