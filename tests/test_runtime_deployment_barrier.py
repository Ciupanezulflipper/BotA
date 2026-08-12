from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
RUNNER = HERE / "tools" / "run_signal_watcher_with_ledger.sh"


class RuntimeDeploymentBarrierTests(unittest.TestCase):
    def run_runner(self, root: Path) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["BOTA_ROOT"] = str(root)
        return subprocess.run(
            ["bash", str(RUNNER)],
            text=True,
            capture_output=True,
            check=False,
            env=env,
            timeout=10,
        )

    def test_regular_marker_blocks_before_any_runtime_setup(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            state = root / "state"
            state.mkdir()
            marker = state / "runtime_deploy_in_progress.json"
            marker.write_text('{"deployment_id":"test"}\n', encoding="utf-8")

            result = self.run_runner(root)

            self.assertEqual(result.returncode, 78)
            self.assertIn("deployment_generation_barrier_active", result.stderr)
            self.assertFalse((root / "logs").exists())

    def test_symlink_marker_also_blocks_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            state = root / "state"
            state.mkdir()
            marker = state / "runtime_deploy_in_progress.json"
            marker.symlink_to(root / "missing-target")

            result = self.run_runner(root)

            self.assertEqual(result.returncode, 78)
            self.assertIn("deployment_generation_barrier_active", result.stderr)
            self.assertFalse((root / "logs").exists())

    def test_without_marker_runner_proceeds_to_normal_tool_validation(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            result = self.run_runner(root)

            self.assertEqual(result.returncode, 66)
            self.assertIn("canonical telegram sender missing", result.stderr)
            self.assertTrue((root / "logs").is_dir())
            self.assertTrue((root / "state").is_dir())

    def test_barrier_check_precedes_sender_and_watcher_execution(self):
        text = RUNNER.read_text(encoding="utf-8")
        barrier = text.index("deployment_generation_barrier_active")
        sender = text.index("canonical telegram sender missing")
        watcher = text.index('bash "${TOOLS}/signal_watcher_pro.sh" --once')
        self.assertLess(barrier, sender)
        self.assertLess(barrier, watcher)


if __name__ == "__main__":
    unittest.main()
