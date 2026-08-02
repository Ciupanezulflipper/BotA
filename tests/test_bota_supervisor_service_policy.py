#!/usr/bin/env python3
"""Policy tests for the tracked non-mutating bota-supervisor runit wrapper."""

from __future__ import annotations

import os
import subprocess
import tempfile
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SERVICE = ROOT / "services" / "bota-supervisor" / "run"


class SupervisorServicePolicyTests(unittest.TestCase):
    """Verify the wrapper schedules health checks without mutating topology."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.source = SERVICE.read_text(encoding="utf-8")

    def test_forbids_manager_and_service_mutation_commands(self) -> None:
        forbidden = (
            "runsvdir ",
            "runsv ",
            "sv up",
            "sv down",
            "sv restart",
            "service start",
            "service stop",
            "pkill",
            "killall",
        )
        for token in forbidden:
            with self.subTest(token=token):
                self.assertNotIn(token, self.source)

    def test_does_not_probe_processes_to_decide_manager_creation(self) -> None:
        self.assertNotIn("pgrep", self.source)
        self.assertNotIn("pidof", self.source)
        self.assertNotIn("/proc/", self.source)

    def test_invokes_deployed_supervisor_with_bota_root(self) -> None:
        self.assertIn('SCRIPT="${ROOT}/tools/bota_supervisor.sh"', self.source)
        self.assertIn('BOTA_ROOT="${ROOT}" bash "${SCRIPT}"', self.source)

    def test_has_bounded_configurable_cadence(self) -> None:
        self.assertIn("BOTA_SUPERVISOR_INTERVAL_SEC", self.source)
        self.assertIn('sleep "${INTERVAL}"', self.source)
        self.assertIn("if (( INTERVAL < 1 )); then", self.source)

    def test_missing_supervisor_is_observable_not_repaired(self) -> None:
        self.assertIn("supervisor_script_missing", self.source)
        self.assertNotIn("mkdir -p \"${ROOT}/tools\"", self.source)

    def test_runtime_smoke_calls_supervisor_without_topology_tools(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            tools = root / "tools"
            tools.mkdir(parents=True)
            marker = root / "called.txt"
            fake_supervisor = tools / "bota_supervisor.sh"
            fake_supervisor.write_text(
                "#!/usr/bin/env bash\n"
                f"printf called >> {marker!s}\n",
                encoding="utf-8",
            )
            fake_supervisor.chmod(0o755)

            environment = os.environ.copy()
            environment.update(
                {
                    "BOTA_ROOT": str(root),
                    "BOTA_SUPERVISOR_INTERVAL_SEC": "1",
                }
            )

            process = subprocess.Popen(
                ["bash", str(SERVICE)],
                cwd=ROOT,
                env=environment,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            try:
                deadline = time.monotonic() + 3.0
                while time.monotonic() < deadline and not marker.exists():
                    time.sleep(0.05)
            finally:
                process.terminate()
                process.communicate(timeout=5)

            self.assertTrue(marker.exists())
            self.assertGreaterEqual(marker.read_text(encoding="utf-8").count("called"), 1)


if __name__ == "__main__":
    unittest.main()
