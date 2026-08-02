#!/usr/bin/env python3
"""Behavioral tests for BotA's market-gated Telegram status sender."""

from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUTOSTATUS = ROOT / "tools" / "autostatus.sh"


def prepare_root(base: Path) -> tuple[Path, Path, Path]:
    """Create an isolated BotA runtime tree for one test."""
    root = base / "BotA"
    tools = root / "tools"
    for directory in (tools, root / "tmp", root / "logs", root / "config"):
        directory.mkdir(parents=True, exist_ok=True)
    return root, tools / "market_open.sh", tools / "format_status.py"


def write_gate(path: Path, state: str, exit_code: int) -> None:
    """Write a deterministic market gate."""
    path.write_text(
        "#!/usr/bin/env bash\n"
        f"printf '%s\\n' {state!r}\n"
        f"exit {exit_code}\n",
        encoding="utf-8",
    )
    path.chmod(0o755)


def write_formatter(path: Path, marker: Path, *, fail: bool = False) -> None:
    """Write a formatter that records execution and optionally fails."""
    if fail:
        body = (
            "#!/usr/bin/env python3\n"
            "import sys\n"
            "from pathlib import Path\n"
            f"Path({str(marker)!r}).write_text('called', encoding='utf-8')\n"
            "print('formatter exploded', file=sys.stderr)\n"
            "raise SystemExit(2)\n"
        )
    else:
        body = (
            "#!/usr/bin/env python3\n"
            "from pathlib import Path\n"
            f"Path({str(marker)!r}).write_text('called', encoding='utf-8')\n"
            "print('cached technical context')\n"
        )
    path.write_text(body, encoding="utf-8")
    path.chmod(0o755)


def write_telegram_env(root: Path) -> None:
    """Write non-secret test credentials."""
    (root / "config" / "tele.env").write_text(
        "TELEGRAM_BOT_TOKEN=unit-test-token\n"
        "TELEGRAM_CHAT_ID=unit-test-chat\n",
        encoding="utf-8",
    )


def write_fake_curl(path: Path, *, success: bool) -> None:
    """Write a fake curl transport for success or timeout behavior."""
    if success:
        body = (
            "#!/usr/bin/env bash\n"
            "printf '%s\\n' '{\"ok\":true}'\n"
            "printf '%s\\n' 'HTTP_STATUS:200'\n"
            "exit 0\n"
        )
    else:
        body = (
            "#!/usr/bin/env bash\n"
            "printf '%s\\n' 'curl: (28) Operation timed out' >&2\n"
            "printf '%s\\n' 'HTTP_STATUS:000'\n"
            "exit 28\n"
        )
    path.write_text(body, encoding="utf-8")
    path.chmod(0o755)


def run_autostatus(
    root: Path,
    *,
    dry_run: bool,
    curl_bin: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run the production sender in an isolated environment."""
    environment = os.environ.copy()
    environment.update(
        {
            "HOME": str(root.parent),
            "BOTA_ROOT": str(root),
            "AUTOSTATUS_DRY_RUN": "1" if dry_run else "0",
        }
    )
    if curl_bin is not None:
        environment["CURL_BIN"] = str(curl_bin)
    return subprocess.run(
        ["bash", str(AUTOSTATUS)],
        cwd=ROOT,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )


def read_log(root: Path) -> str:
    """Read the isolated autostatus log."""
    return (root / "logs" / "cron.autostatus.log").read_text(encoding="utf-8")


def temporary_files(root: Path) -> list[Path]:
    """Return any workspace entries left after a sender run."""
    return list((root / "tmp").iterdir())


class AutostatusSourcePolicyTests(unittest.TestCase):
    """Prevent gate-order, shared-file, and transport-diagnostic regressions."""

    def test_market_gate_executes_before_formatter(self) -> None:
        source = AUTOSTATUS.read_text(encoding="utf-8")
        gate_execution = source.index('if MARKET_STATE="$(')
        formatter_execution = source.index('"${PYTHON_BIN}" "${FORMATTER}"')
        self.assertLess(gate_execution, formatter_execution)

    def test_sender_uses_isolated_non_recursive_workspace_cleanup(self) -> None:
        source = AUTOSTATUS.read_text(encoding="utf-8")
        self.assertIn('mktemp -d "${TMPDIR}/autostatus.XXXXXX"', source)
        self.assertIn('rm -f -- "${OUT}" "${ERR}" "${RESP_FILE}" "${CURL_ERR}"', source)
        self.assertIn('rmdir -- "${WORKDIR}"', source)
        self.assertNotIn("rm -rf", source)
        self.assertNotIn('${TMPDIR}/as.out', source)
        self.assertNotIn('${TMPDIR}/as.err', source)

    def test_sender_captures_curl_status_and_stderr(self) -> None:
        source = AUTOSTATUS.read_text(encoding="utf-8")
        self.assertIn('2>"${CURL_ERR}"', source)
        self.assertIn("CURL_RC=$?", source)
        self.assertIn("stderr=${CURL_DETAIL:-none}", source)


class AutostatusBehaviorTests(unittest.TestCase):
    """Exercise fail-closed gating, rendering, cleanup, and transport behavior."""

    def test_missing_market_gate_skips_formatter(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root, _, formatter = prepare_root(Path(temporary))
            marker = root / "formatter_called.txt"
            write_formatter(formatter, marker)
            result = run_autostatus(root, dry_run=True)
            log = read_log(root)
            leftovers = temporary_files(root)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(marker.exists())
        self.assertIn("market_gate_missing_or_not_executable", log)
        self.assertEqual(leftovers, [])

    def test_closed_market_skips_formatter(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root, gate, formatter = prepare_root(Path(temporary))
            marker = root / "formatter_called.txt"
            write_gate(gate, "Closed", 1)
            write_formatter(formatter, marker)
            result = run_autostatus(root, dry_run=True)
            log = read_log(root)
            leftovers = temporary_files(root)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(marker.exists())
        self.assertIn("market_closed_or_clock_unavailable", log)
        self.assertEqual(leftovers, [])

    def test_open_market_dry_run_renders_and_cleans_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root, gate, formatter = prepare_root(Path(temporary))
            marker = root / "formatter_called.txt"
            write_gate(gate, "Open", 0)
            write_formatter(formatter, marker)
            result = run_autostatus(root, dry_run=True)
            log = read_log(root)
            marker_called = marker.exists()
            leftovers = temporary_files(root)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(marker_called)
        self.assertEqual(result.stdout.strip(), "cached technical context")
        self.assertIn("DRY_RUN: status rendered; Telegram not called", log)
        self.assertEqual(leftovers, [])

    def test_formatter_failure_is_logged_and_workspace_is_cleaned(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root, gate, formatter = prepare_root(Path(temporary))
            marker = root / "formatter_called.txt"
            write_gate(gate, "Open", 0)
            write_formatter(formatter, marker, fail=True)
            result = run_autostatus(root, dry_run=True)
            log = read_log(root)
            leftovers = temporary_files(root)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("format_status failed", log)
        self.assertIn("formatter exploded", log)
        self.assertEqual(leftovers, [])

    def test_telegram_success_is_logged_without_real_network(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root, gate, formatter = prepare_root(Path(temporary))
            marker = root / "formatter_called.txt"
            fake_curl = root / "tools" / "fake-curl.sh"
            write_gate(gate, "Open", 0)
            write_formatter(formatter, marker)
            write_telegram_env(root)
            write_fake_curl(fake_curl, success=True)
            result = run_autostatus(root, dry_run=False, curl_bin=fake_curl)
            log = read_log(root)
            leftovers = temporary_files(root)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("sendMessage OK plain_text http=200", log)
        self.assertEqual(leftovers, [])

    def test_telegram_timeout_retains_diagnostics_and_cleans_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root, gate, formatter = prepare_root(Path(temporary))
            marker = root / "formatter_called.txt"
            fake_curl = root / "tools" / "fake-curl.sh"
            write_gate(gate, "Open", 0)
            write_formatter(formatter, marker)
            write_telegram_env(root)
            write_fake_curl(fake_curl, success=False)
            result = run_autostatus(root, dry_run=False, curl_bin=fake_curl)
            log = read_log(root)
            leftovers = temporary_files(root)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("curl_rc=28", log)
        self.assertIn("http=000", log)
        self.assertIn("Operation timed out", log)
        self.assertEqual(leftovers, [])


if __name__ == "__main__":
    unittest.main()
