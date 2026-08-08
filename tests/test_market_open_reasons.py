"""Regression tests for tools/market_open.sh reason-code emissions.

These tests do not touch the network. The upstream server-clock probe is
overridden by injecting a shim ``python3`` on PATH that returns a scripted
gate line to the script's ``compute_server_utc_fields`` helper. Every
scenario asserts:

* the stdout is either exactly "Open" or "Closed" (backward-compatibility),
* the exit code matches the reason (0 for MARKET_OPEN, 1 otherwise),
* the reason file, when configured, contains exactly the expected code.
"""
from __future__ import annotations

import os
import shutil
import stat
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
GATE = REPO / "tools" / "market_open.sh"


def make_python_shim(shim_dir: Path, gate_line: str | None) -> Path:
    """Create a python3 shim on PATH that returns a scripted gate line.

    When ``gate_line`` is ``None`` the shim prints nothing, mimicking a
    completely failed clock probe.
    """
    shim = shim_dir / "python3"
    real_python = shutil.which("python3") or "/data/data/com.termux/files/usr/bin/python3"
    if gate_line is None:
        script = textwrap.dedent(
            f"""            #!/data/data/com.termux/files/usr/bin/bash
            # No-op shim: pretend python3 was invoked but produced no gate line.
            if [[ "${{1:-}}" = "-" ]]; then
              exit 0
            fi
            exec "{real_python}" "$@"
            """
        ).lstrip()
    else:
        script = textwrap.dedent(
            f"""            #!/data/data/com.termux/files/usr/bin/bash
            # Scripted-clock shim: intercept the here-doc invocation.
            if [[ "${{1:-}}" = "-" ]]; then
              printf '%s\\n' "{gate_line}"
              exit 0
            fi
            exec "{real_python}" "$@"
            """
        ).lstrip()
    shim.write_text(script, encoding="utf-8")
    shim.chmod(shim.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    return shim


class MarketOpenReasonTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp.name)
        self.shim_dir = self.tmp_path / "shim"
        self.shim_dir.mkdir()
        self.reason_file = self.tmp_path / "reason.txt"
        self.epoch_file = self.tmp_path / "epoch.txt"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def run_gate(
        self,
        gate_line: str | None,
        *,
        skip_session: bool = False,
    ) -> tuple[int, str, str]:
        make_python_shim(self.shim_dir, gate_line)
        env = os.environ.copy()
        env["PATH"] = f"{self.shim_dir}:{env.get('PATH','')}"
        env["MARKET_OPEN_REASON_FILE"] = str(self.reason_file)
        env["BOTA_SERVER_EPOCH_FILE"] = str(self.epoch_file)
        if skip_session:
            env["SKIP_SESSION_FILTER"] = "1"
        else:
            env.pop("SKIP_SESSION_FILTER", None)
        completed = subprocess.run(
            ["bash", str(GATE)],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        reason = ""
        if self.reason_file.exists():
            reason = self.reason_file.read_text(encoding="utf-8").strip()
        return completed.returncode, completed.stdout.strip(), reason

    def test_open_within_london_ny_session_emits_market_open(self) -> None:
        # Monday 12:00 UTC
        rc, stdout, reason = self.run_gate("1 1200 2026-08-10T12:00:00Z 4 3 1786363200")
        self.assertEqual(stdout, "Open")
        self.assertEqual(rc, 0)
        self.assertEqual(reason, "MARKET_OPEN")

    def test_saturday_emits_market_closed_saturday(self) -> None:
        rc, stdout, reason = self.run_gate("6 1200 2026-08-08T12:00:00Z 4 3 1786190400")
        self.assertEqual(stdout, "Closed")
        self.assertEqual(rc, 1)
        self.assertEqual(reason, "MARKET_CLOSED_SATURDAY")

    def test_sunday_emits_market_closed_sunday(self) -> None:
        rc, stdout, reason = self.run_gate("7 1200 2026-08-09T12:00:00Z 4 3 1786276800")
        self.assertEqual(stdout, "Closed")
        self.assertEqual(rc, 1)
        self.assertEqual(reason, "MARKET_CLOSED_SUNDAY")

    def test_friday_after_2000_emits_friday_post_close(self) -> None:
        rc, stdout, reason = self.run_gate("5 2015 2026-08-07T20:15:00Z 4 3 1786104900")
        self.assertEqual(stdout, "Closed")
        self.assertEqual(rc, 1)
        self.assertEqual(reason, "MARKET_CLOSED_FRIDAY_POST_2000")

    def test_asian_pre_0700_emits_asian_reason(self) -> None:
        rc, stdout, reason = self.run_gate("1 0500 2026-08-10T05:00:00Z 4 3 1786338000")
        self.assertEqual(stdout, "Closed")
        self.assertEqual(rc, 1)
        self.assertEqual(reason, "MARKET_CLOSED_ASIAN_PRE_0700")

    def test_weekday_midnight_is_asian_closed_not_clock_unavailable(self) -> None:
        # 00:00 UTC is a valid trusted-clock value. It must reach the normal
        # Asian-session gate instead of being mistaken for the old 0000
        # clock-unavailable sentinel.
        rc, stdout, reason = self.run_gate("1 0000 2026-08-10T00:00:00Z 4 3 1786320000")
        self.assertEqual(stdout, "Closed")
        self.assertEqual(rc, 1)
        self.assertEqual(reason, "MARKET_CLOSED_ASIAN_PRE_0700")

    def test_post_ny_emits_post_ny_reason(self) -> None:
        rc, stdout, reason = self.run_gate("1 2100 2026-08-10T21:00:00Z 4 3 1786395600")
        self.assertEqual(stdout, "Closed")
        self.assertEqual(rc, 1)
        self.assertEqual(reason, "MARKET_CLOSED_POST_NY")

    def test_clock_probe_missing_emits_clock_unavailable(self) -> None:
        rc, stdout, reason = self.run_gate("0 0000 NA 0 999999 0")
        self.assertEqual(stdout, "Closed")
        self.assertEqual(rc, 1)
        self.assertEqual(reason, "CLOCK_UNAVAILABLE")

    def test_empty_gate_output_emits_clock_unavailable(self) -> None:
        rc, stdout, reason = self.run_gate(None)
        self.assertEqual(stdout, "Closed")
        self.assertEqual(rc, 1)
        self.assertEqual(reason, "CLOCK_UNAVAILABLE")

    def test_skip_session_filter_bypasses_only_intraday_gates(self) -> None:
        # Asian session hour, but SKIP_SESSION_FILTER=1 opens the gate.
        rc, stdout, reason = self.run_gate(
            "1 0500 2026-08-10T05:00:00Z 4 3 1786338000",
            skip_session=True,
        )
        self.assertEqual(stdout, "Open")
        self.assertEqual(rc, 0)
        self.assertEqual(reason, "MARKET_OPEN")

    def test_skip_session_filter_does_not_open_saturday(self) -> None:
        # SKIP_SESSION_FILTER must NEVER override weekend closure.
        rc, stdout, reason = self.run_gate(
            "6 1200 2026-08-08T12:00:00Z 4 3 1786190400",
            skip_session=True,
        )
        self.assertEqual(stdout, "Closed")
        self.assertEqual(rc, 1)
        self.assertEqual(reason, "MARKET_CLOSED_SATURDAY")

    def test_server_epoch_file_written_only_when_probe_succeeds(self) -> None:
        # Success path
        self.run_gate("1 1200 2026-08-10T12:00:00Z 4 3 1786363200")
        self.assertTrue(self.epoch_file.exists())
        self.assertEqual(self.epoch_file.read_text(encoding="utf-8").strip(), "1786363200")
        # Failure path leaves the previous file untouched; verify by using a
        # fresh path.
        self.epoch_file = self.tmp_path / "epoch2.txt"
        self.reason_file = self.tmp_path / "reason2.txt"
        self.run_gate("0 0000 NA 0 999999 0")
        self.assertFalse(self.epoch_file.exists())


if __name__ == "__main__":
    unittest.main()
