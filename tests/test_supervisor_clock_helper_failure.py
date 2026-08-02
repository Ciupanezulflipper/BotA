#!/usr/bin/env python3
"""Regression proof for supervisor clock-helper failure containment."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SUPERVISOR = REPOSITORY_ROOT / "tools" / "bota_supervisor.sh"


def write_executable(path: Path, content: str) -> None:
    """Write one executable fixture."""
    path.write_text(content, encoding="utf-8")
    path.chmod(0o755)


def prepare_failed_helper_runtime(base: Path) -> Path:
    """Create a healthy runtime whose clock helper exits nonzero."""
    root = base / "BotA"
    tools = root / "tools"
    for directory in (
        tools,
        root / "logs" / "state",
        root / "state",
        root / "config",
    ):
        directory.mkdir(parents=True, exist_ok=True)

    supervisor = tools / "bota_supervisor.sh"
    supervisor.write_text(SUPERVISOR.read_text(encoding="utf-8"), encoding="utf-8")
    supervisor.chmod(0o755)

    write_executable(
        tools / "control_plane_status.py",
        "#!/usr/bin/env python3\n"
        "import json\n"
        "print(json.dumps({"
        "'owned': 7, 'required': 7, 'running': 7, 'orphaned': 0, "
        "'failure_reasons': []}))\n",
    )
    write_executable(
        tools / "pipeline_health.py",
        "#!/usr/bin/env python3\n"
        "import json\n"
        "import sys\n"
        "from pathlib import Path\n"
        f"root = Path({str(root)!r})\n"
        "(root / 'state' / 'pipeline_args.txt').write_text("
        "' '.join(sys.argv[1:]), encoding='utf-8')\n"
        "print(json.dumps({'healthy': True, 'failure_reasons': []}))\n",
    )
    write_executable(
        tools / "market_open.sh",
        "#!/usr/bin/env bash\n"
        "printf '%s\\n' 'Closed'\n"
        "printf '%s\\n' 'Saturday UTC -> Closed' >&2\n"
        "exit 1\n",
    )
    write_executable(
        tools / "supervisor_clock_status.py",
        "#!/usr/bin/env python3\n"
        "raise SystemExit(3)\n",
    )
    return root


def run_supervisor(root: Path) -> subprocess.CompletedProcess[str]:
    """Run the production supervisor against the isolated fixture."""
    bash_path = shutil.which("bash")
    if bash_path is None:
        raise RuntimeError("bash executable not found")
    environment = os.environ.copy()
    environment.update(
        {
            "HOME": str(root.parent),
            "BOTA_ROOT": str(root),
            "PATH": os.environ["PATH"],
        }
    )
    return subprocess.run(
        [bash_path, str(root / "tools" / "bota_supervisor.sh")],
        cwd=root,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )


class SupervisorClockHelperFailureTests(unittest.TestCase):
    """Ensure helper failure cannot erase runtime observability."""

    def test_failed_clock_helper_writes_nonfatal_fallback_health(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = prepare_failed_helper_runtime(Path(temporary))
            result = run_supervisor(root)
            health = json.loads(
                (root / "state" / "runtime_health.json").read_text(
                    encoding="utf-8"
                )
            )
            pipeline_args = (
                root / "state" / "pipeline_args.txt"
            ).read_text(encoding="utf-8")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIsInstance(health, dict)
        self.assertEqual(health["bot_mode"], "HEALTHY")
        self.assertEqual(health["failure_reasons"], [])
        self.assertEqual(health["market_state"], "error")
        self.assertEqual(health["market_gate"]["reason"], "clock_status_tool_failed")
        self.assertEqual(health["clock_observability"]["status"], "TOOL_FAILED")
        self.assertFalse(health["clock_observability"]["runtime_failure"])
        self.assertEqual(pipeline_args, "--market-closed")
        self.assertIn("CLOCK_STATUS_TOOL_FAILED: rc=3", result.stdout)


if __name__ == "__main__":
    unittest.main()
