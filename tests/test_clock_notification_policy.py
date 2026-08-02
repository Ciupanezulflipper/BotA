#!/usr/bin/env python3
"""Regression tests for BotA clock-health and heartbeat-delivery policy.

These tests intentionally describe the required corrected behavior.

Production requirements:

1. Trading processes remain fail-closed when trusted server UTC is unavailable.
2. A transient server-clock outage alone must not label an otherwise healthy
   BotA runtime as malfunctioning.
3. Failed Telegram delivery must be rate-limited rather than attempted every
   60-second heartbeat service cycle.
"""

from __future__ import annotations

import ast
import re
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SUPERVISOR = REPOSITORY_ROOT / "tools" / "bota_supervisor.sh"
HEARTBEAT = REPOSITORY_ROOT / "tools" / "heartbeat.sh"
MARKET_GATE = REPOSITORY_ROOT / "tools" / "market_open.sh"
WATCHER = REPOSITORY_ROOT / "tools" / "signal_watcher_pro.sh"
CLOSER = REPOSITORY_ROOT / "tools" / "signal_closer.py"
UPDATER_SERVICE = REPOSITORY_ROOT / "services" / "bota-updater" / "run"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class TradingClockSafetyTests(unittest.TestCase):
    """Protect fail-closed trading behavior from notification-policy changes."""

    def test_market_gate_remains_fail_closed(self) -> None:
        source = read(MARKET_GATE)

        self.assertIn("server_clock_unavailable", source)
        self.assertRegex(
            source,
            r'echo\s+"Closed"\s*\n\s*exit\s+1',
        )

    def test_watcher_remains_fail_closed(self) -> None:
        source = read(WATCHER)

        self.assertIn(
            "server_clock_unavailable -> SKIP_SCAN fail_closed",
            source,
        )

    def test_closer_remains_fail_closed(self) -> None:
        source = read(CLOSER)

        self.assertIn(
            "server_clock_unavailable -> FAIL_CLOSED",
            source,
        )

    def test_updater_remains_market_gated(self) -> None:
        source = read(UPDATER_SERVICE)

        self.assertIn("market_closed_or_clock_unavailable", source)
        self.assertIn('if ! "${MARKET_GATE}"', source)


class SupervisorNotificationPolicyTests(unittest.TestCase):
    """Specify that clock transport outages are not runtime failures alone."""

    def test_server_clock_unavailable_is_not_added_to_runtime_failures(self) -> None:
        source = read(SUPERVISOR)

        prohibited = re.compile(
            r'if\s+status\s*==\s*["\']SERVER_CLOCK_UNAVAILABLE["\']'
            r'\s*:\s*\n'
            r'\s*print\(["\']server_clock_unavailable["\']\)',
            re.MULTILINE,
        )

        self.assertIsNone(
            prohibited.search(source),
            "Transient server-clock unavailability is still promoted to "
            "a full BotA runtime failure.",
        )

    def test_clock_status_may_remain_observable(self) -> None:
        source = read(SUPERVISOR)

        self.assertIn("clock_failure", source)
        self.assertIn("clock_drift_status.json", source)


class HeartbeatRetryPolicyTests(unittest.TestCase):
    """Require explicit retry throttling after Telegram transport failures."""

    def test_heartbeat_defines_retry_state(self) -> None:
        source = read(HEARTBEAT)

        required_markers = (
            "delivery_failure",
            "next_retry",
            "retry",
        )

        normalized = source.lower()

        self.assertTrue(
            all(marker in normalized for marker in required_markers),
            "Heartbeat has no persisted delivery-failure retry policy.",
        )

    def test_heartbeat_persists_state_after_delivery_failure(self) -> None:
        source = read(HEARTBEAT)

        failure_position = source.find(
            'log(f"heartbeat failed: {type(exc).__name__}")'
        )
        state_write_position = source.find("temporary.write_text")

        self.assertGreaterEqual(
            failure_position,
            0,
            "Expected Telegram exception handling was not found.",
        )
        self.assertGreaterEqual(
            state_write_position,
            0,
            "Expected heartbeat state persistence was not found.",
        )

        failure_block = source[
            failure_position : state_write_position
            if state_write_position > failure_position
            else len(source)
        ]

        self.assertRegex(
            failure_block.lower(),
            r"(write_text|replace|save|persist).*(retry|failure)"
            r"|(retry|failure).*(write_text|replace|save|persist)",
            "Telegram failure exits without persisting retry suppression state.",
        )

    def test_embedded_python_remains_parseable(self) -> None:
        source = read(HEARTBEAT)
        marker = "<<'PYTHON'\n"

        self.assertIn(marker, source)

        python_source = source.split(marker, 1)[1].rsplit("\nPYTHON", 1)[0]
        ast.parse(python_source)


if __name__ == "__main__":
    unittest.main()
