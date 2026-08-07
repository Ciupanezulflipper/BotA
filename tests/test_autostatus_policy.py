#!/usr/bin/env python3
"""Behavioral tests for BotA's local-only technical context refresher."""

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


def run_autostatus(
    root: Path,
    *,
    dry_run: bool,
) -> subprocess.CompletedProcess[str]:
    """Run the production refresher in an isolated environment."""
    environment = os.environ.copy()
    environment.update(
        {
            "HOME": str(root.parent),
            "BOTA_ROOT": str(root),
            "AUTOSTATUS_DRY_RUN": "1" if dry_run else "0",
        }
    )
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
    """Return any workspace entries left after a refresher run."""
    return list((root / "tmp").iterdir())


class AutostatusSourcePolicyTests(unittest.TestCase):
    """Prevent notification transport and gate-order regressions."""

    def test_market_gate_executes_before_formatter(self) -> None:
        source = AUTOSTATUS.read_text(encoding="utf-8")
        gate_execution = source.index('if MARKET_STATE="$(')
        formatter_execution = source.index('"${PYTHON_BIN}" "${FORMATTER}"')
        self.assertLess(gate_execution, formatter_execution)

    def test_scheduled_context_has_no_telegram_transport(self) -> None:
        source = AUTOSTATUS.read_text(encoding="utf-8")
        for token in (
            "api.telegram.org",
            "sendMessage",
            "TELEGRAM_BOT_TOKEN",
            "TELEGRAM_CHAT_ID",
            "tele.env",
            "CURL_BIN",
            "curl ",
        ):
            with self.subTest(token=token):
                self.assertNotIn(token, source)
        self.assertIn("TECHNICAL_CONTEXT_RESULT=LOCAL_ONLY", source)

    def test_refresher_uses_isolated_non_recursive_cleanup(self) -> None:
        source = AUTOSTATUS.read_text(encoding="utf-8")
        self.assertIn('mktemp -d "${TMPDIR}/autostatus.XXXXXX"', source)
        self.assertIn(
            'rm -f -- "${OUT}" "${ERR}" "${LATEST_TMP}"',
            source,
        )
        self.assertIn('rmdir -- "${WORKDIR}"', source)
        self.assertNotIn("rm -rf", source)


class AutostatusBehaviorTests(unittest.TestCase):
    """Exercise fail-closed gating, local refresh, and cleanup."""

    def test_missing_market_gate_skips_formatter(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root, _, formatter = prepare_root(Path(temporary))
            marker = root / "formatter_called.txt"
            write_formatter(formatter, marker)
            result = run_autostatus(root, dry_run=True)
            log = read_log(root)
            marker_called = marker.exists()
            leftovers = temporary_files(root)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(marker_called)
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
            marker_called = marker.exists()
            leftovers = temporary_files(root)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(marker_called)
        self.assertIn("market_closed_or_clock_unavailable", log)
        self.assertEqual(leftovers, [])

    def test_open_market_dry_run_renders_without_writing_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root, gate, formatter = prepare_root(Path(temporary))
            marker = root / "formatter_called.txt"
            write_gate(gate, "Open", 0)
            write_formatter(formatter, marker)
            result = run_autostatus(root, dry_run=True)
            log = read_log(root)
            marker_called = marker.exists()
            latest_exists = (root / "logs" / "technical_context.latest.txt").exists()
            leftovers = temporary_files(root)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(marker_called)
        self.assertEqual(result.stdout.strip(), "cached technical context")
        self.assertIn("Telegram disabled by policy", log)
        self.assertFalse(latest_exists)
        self.assertEqual(leftovers, [])

    def test_open_market_refreshes_local_snapshot_only(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root, gate, formatter = prepare_root(Path(temporary))
            marker = root / "formatter_called.txt"
            write_gate(gate, "Open", 0)
            write_formatter(formatter, marker)
            result = run_autostatus(root, dry_run=False)
            log = read_log(root)
            snapshot = (root / "logs" / "technical_context.latest.txt").read_text(
                encoding="utf-8"
            )
            snapshot_mode = (
                root / "logs" / "technical_context.latest.txt"
            ).stat().st_mode & 0o777
            leftovers = temporary_files(root)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertEqual(snapshot.strip(), "cached technical context")
        self.assertEqual(snapshot_mode, 0o600)
        self.assertIn("TECHNICAL_CONTEXT_RESULT=LOCAL_ONLY", log)
        self.assertNotIn("sendMessage", log)
        self.assertEqual(leftovers, [])

    def test_formatter_failure_is_logged_and_workspace_is_cleaned(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root, gate, formatter = prepare_root(Path(temporary))
            marker = root / "formatter_called.txt"
            write_gate(gate, "Open", 0)
            write_formatter(formatter, marker, fail=True)
            result = run_autostatus(root, dry_run=False)
            log = read_log(root)
            latest_exists = (root / "logs" / "technical_context.latest.txt").exists()
            leftovers = temporary_files(root)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("format_status failed", log)
        self.assertIn("formatter exploded", log)
        self.assertFalse(latest_exists)
        self.assertEqual(leftovers, [])


if __name__ == "__main__":
    unittest.main()
