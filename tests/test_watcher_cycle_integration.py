"""Integration regression tests for the Monday-readiness watcher cycle.

These tests target process boundaries that dry-run unit tests do not cover:

1. The outer gated cycle, inner watcher runner, and reconciler must share one
   exact cycle ID during a real MARKET_OPEN execution path.
2. A failed authoritative terminal ledger write must be visible as a non-zero
   wrapper exit instead of being swallowed by ``|| true``.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
TOOLS = REPO / "tools"


class WatcherCycleProcessBoundaryTests(unittest.TestCase):
    def setUp(self) -> None:
        super().setUp()

        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

        (self.root / "state").mkdir(parents=True)
        (self.root / "logs").mkdir(parents=True)
        (self.root / "tools").mkdir(parents=True)

        for name in (
            "pipeline_ledger.py",
            "watcher_gated_cycle.sh",
            "run_signal_watcher_with_ledger.sh",
        ):
            shutil.copy2(
                TOOLS / name,
                self.root / "tools" / name,
            )

        signal_watcher = self.root / "tools" / "signal_watcher_pro.sh"

        signal_watcher.write_text(
            "#!/data/data/com.termux/files/usr/bin/bash\n"
            "exit 0\n",
            encoding="utf-8",
        )

        signal_watcher.chmod(0o755)

        reconciler = self.root / "tools" / "watcher_cycle_ledger.py"

        reconciler.write_text(
            textwrap.dedent(
                """\
                from __future__ import annotations

                import argparse
                import os
                import pathlib
                import subprocess
                import sys

                parser = argparse.ArgumentParser()

                parser.add_argument(
                    "--cycle-id",
                    required=True,
                )
                parser.add_argument(
                    "--alerts-offset",
                    required=True,
                )
                parser.add_argument(
                    "--log-offset",
                    required=True,
                )
                parser.add_argument(
                    "--server-epoch",
                    required=True,
                )

                args = parser.parse_args()

                root = pathlib.Path(
                    os.environ["BOTA_ROOT"]
                )

                (
                    root
                    / "state"
                    / "captured_cycle_id.txt"
                ).write_text(
                    args.cycle_id,
                    encoding="utf-8",
                )

                subprocess.run(
                    [
                        sys.executable,
                        str(
                            root
                            / "tools"
                            / "pipeline_ledger.py"
                        ),
                        "decision",
                        "--pair",
                        "EURUSD",
                        "--timeframe",
                        "M15",
                        "--outcome",
                        "filter_rejected",
                        "--cycle-id",
                        args.cycle_id,
                        "--status",
                        "completed",
                        "--component",
                        "watcher",
                    ],
                    check=True,
                )
                """
            ),
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()
        super().tearDown()

    def run_gate(
        self,
        hint: str,
    ) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()

        env["BOTA_ROOT"] = str(self.root)
        env["WATCHER_GATED_MARKET_HINT"] = hint

        env.pop(
            "WATCHER_GATED_DRY_RUN",
            None,
        )
        env.pop(
            "BOTA_CYCLE_ID",
            None,
        )

        return subprocess.run(
            [
                "bash",
                str(
                    self.root
                    / "tools"
                    / "watcher_gated_cycle.sh"
                ),
            ],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

    def state(self) -> dict:
        return json.loads(
            (
                self.root
                / "state"
                / "pipeline_progress.json"
            ).read_text(
                encoding="utf-8"
            )
        )

    def test_real_open_market_path_reuses_one_cycle_id_end_to_end(
        self,
    ) -> None:
        completed = self.run_gate(
            "MARKET_OPEN"
        )

        self.assertEqual(
            completed.returncode,
            0,
            completed.stderr,
        )

        state = self.state()

        watcher = (
            state
            .get("components", {})
            .get("watcher", {})
        )

        terminal_cycle_id = str(
            watcher.get("cycle_id") or ""
        )

        self.assertTrue(
            terminal_cycle_id
        )

        self.assertEqual(
            watcher.get(
                "terminal_outcome"
            ),
            "EVALUATED_REJECTED",
        )

        self.assertEqual(
            watcher.get("status"),
            "completed",
        )

        reconciler_cycle_id = (
            self.root
            / "state"
            / "captured_cycle_id.txt"
        ).read_text(
            encoding="utf-8"
        )

        self.assertEqual(
            reconciler_cycle_id,
            terminal_cycle_id,
        )

        decisions = state.get(
            "decisions",
            {},
        )

        matching = [
            event
            for event in decisions.values()
            if isinstance(event, dict)
            and str(
                event.get("cycle_id") or ""
            ) == terminal_cycle_id
        ]

        self.assertEqual(
            len(matching),
            1,
        )

        self.assertEqual(
            matching[0].get("outcome"),
            "filter_rejected",
        )

    def test_terminal_ledger_failure_returns_nonzero(
        self,
    ) -> None:
        broken_ledger = (
            self.root
            / "tools"
            / "pipeline_ledger.py"
        )

        broken_ledger.write_text(
            "raise SystemExit(23)\n",
            encoding="utf-8",
        )

        completed = self.run_gate(
            "MARKET_CLOSED_SUNDAY"
        )

        self.assertNotEqual(
            completed.returncode,
            0,
        )

        self.assertEqual(
            completed.returncode,
            23,
        )

        self.assertIn(
            "terminal ledger write failed",
            completed.stderr,
        )

        error_log = (
            self.root
            / "logs"
            / "error.log"
        ).read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "terminal ledger write failed",
            error_log,
        )


if __name__ == "__main__":
    unittest.main()
