from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

from tools import bota_runtime_owner as owner


ROOT = Path(__file__).resolve().parents[1]
OWNER = ROOT / "tools" / "bota_runtime_owner.py"
DUMMY = ROOT / "tools" / "bota_dummy_runtime.py"


def _events(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


class RuntimeOwnerUnitTests(unittest.TestCase):
    def test_heartbeat_missing_is_stale(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertTrue(owner.heartbeat_is_stale(Path(tmp) / "missing.json", 10.0, now=20.0))

    def test_fresh_heartbeat_is_not_stale(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "heartbeat.json"
            path.write_text('{"heartbeat_write_utc":95.0}\n', encoding="utf-8")
            self.assertFalse(owner.heartbeat_is_stale(path, 10.0, now=100.0))

    def test_old_heartbeat_is_stale(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "heartbeat.json"
            path.write_text('{"heartbeat_write_utc":80.0}\n', encoding="utf-8")
            self.assertTrue(owner.heartbeat_is_stale(path, 10.0, now=100.0))

    def test_nonfinite_cli_values_rejected(self) -> None:
        with self.assertRaises(SystemExit):
            owner.parse_args(["--state-dir", "/tmp/x", "--stale-seconds", "nan", "--", "true"])


class RuntimeOwnerIntegrationTests(unittest.TestCase):
    def _owner_command(self, state_dir: Path, *dummy_args: str, starts: int = 2) -> list[str]:
        return [
            sys.executable,
            str(OWNER),
            "--state-dir",
            str(state_dir),
            "--poll-seconds",
            "0.05",
            "--stale-seconds",
            "0.30",
            "--terminate-grace-seconds",
            "0.10",
            "--restart-backoff-seconds",
            "0.01",
            "--max-runtime-starts",
            str(starts),
            "--",
            sys.executable,
            str(DUMMY),
            "--heartbeat-interval",
            "0.05",
            *dummy_args,
        ]

    def test_runtime_exit_is_restarted_exact_number_of_times(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            completed = subprocess.run(
                self._owner_command(state_dir, "--exit-after", "0.12", starts=2),
                check=False,
                timeout=5,
            )
            self.assertEqual(completed.returncode, owner.EXIT_MAX_STARTS_REACHED)
            events = _events(state_dir / "owner_events.jsonl")
            self.assertEqual(sum(e["event"] == "runtime_started" for e in events), 2)
            self.assertEqual(sum(e["event"] == "runtime_exited" for e in events), 2)

    def test_stale_runtime_is_terminated_and_restarted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            completed = subprocess.run(
                self._owner_command(state_dir, "--stale-after", "0.10", starts=2),
                check=False,
                timeout=5,
            )
            self.assertEqual(completed.returncode, owner.EXIT_MAX_STARTS_REACHED)
            events = _events(state_dir / "owner_events.jsonl")
            self.assertEqual(sum(e["event"] == "runtime_started" for e in events), 2)
            self.assertEqual(sum(e["event"] == "runtime_zombie_detected" for e in events), 2)
            self.assertEqual(sum(e["event"] == "runtime_zombie_terminated" for e in events), 2)

    def test_second_owner_is_rejected_by_flock(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            first = subprocess.Popen(
                self._owner_command(state_dir, starts=1),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            try:
                deadline = time.time() + 3
                while time.time() < deadline:
                    if (state_dir / "owner_events.jsonl").exists():
                        break
                    time.sleep(0.05)
                second = subprocess.run(
                    self._owner_command(state_dir, starts=1),
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=3,
                )
                self.assertEqual(second.returncode, owner.EXIT_ALREADY_RUNNING)
                self.assertIn("BOTA_RUNTIME_OWNER=ALREADY_RUNNING", second.stdout)
            finally:
                first.terminate()
                first.wait(timeout=3)


if __name__ == "__main__":
    unittest.main()
