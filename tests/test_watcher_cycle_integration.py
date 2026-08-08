"""Integration regression tests for the Monday-readiness watcher cycle.

These tests target process boundaries that dry-run unit tests do not cover:

1. The outer gated cycle, inner watcher runner, and reconciler must share one
   exact cycle ID during a real MARKET_OPEN execution path.
2. A failed authoritative terminal ledger write must be visible as a non-zero
   wrapper exit instead of being swallowed by ``|| true``.
3. A non-zero inner watcher/runner exit code must dominate any healthy-looking
   semantic aggregate produced from pre-existing on-disk evidence. Recording
   the aggregate as the authoritative terminal outcome in that case would be a
   false-green — the pipeline_health evaluator, runit error log, and any
   operator reading ``last_terminal_outcome`` would see a normal terminal
   state while the underlying execution actually failed. The pre-failure
   aggregate must be preserved inside ``details`` for forensic reconstruction.
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


class WatcherCycleInnerFailureDominatesTests(unittest.TestCase):
    """`inner_rc != 0` must dominate any healthy-looking reconciled aggregate.

    Historically the outer gated cycle only escalated to INTERNAL_ERROR when
    BOTH ``inner_rc != 0`` AND the reconciled aggregate was already
    ``INTERNAL_ERROR``. When the reconciler surfaced a healthy semantic
    aggregate from historical evidence — for example EVALUATED_REJECTED from
    filter-rejected alerts.csv rows appended by the fake watcher before it
    crashed — the outer cycle silently recorded ``completed`` /
    ``EVALUATED_REJECTED`` as the authoritative terminal outcome. That
    false-green would make ``pipeline_health.evaluate`` report Monday-ready
    while the inner runner was actually failing every cycle.

    These tests drive the real process boundary
    ``watcher_gated_cycle.sh`` -> ``run_signal_watcher_with_ledger.sh`` ->
    fake ``signal_watcher_pro.sh`` (which appends valid evidence then exits
    non-zero) -> real ``watcher_cycle_ledger.py`` -> real ``pipeline_ledger.py``
    to pin the new contract.
    """

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
            "watcher_cycle_ledger.py",
        ):
            shutil.copy2(
                TOOLS / name,
                self.root / "tools" / name,
            )

    def tearDown(self) -> None:
        self.tmp.cleanup()
        super().tearDown()

    def _install_fake_watcher(self, exit_code: int) -> None:
        """Install a fake watcher that appends healthy evidence and exits."""
        # The evidence intentionally mirrors what a genuine watcher scan
        # would append: alerts.csv rows keyed by the production three-pair
        # scope, plus cron.signals.log lines matching the reconciler's
        # `rejected_by_filter` classifier. If the outer gated cycle honored
        # this aggregate as authoritative it would record EVALUATED_REJECTED
        # even though the fake watcher itself exited with a fatal code.
        fake = self.root / "tools" / "signal_watcher_pro.sh"
        fake.write_text(
            textwrap.dedent(
                f"""\
                #!/data/data/com.termux/files/usr/bin/bash
                set -uo pipefail

                LOGS="${{BOTA_ROOT}}/logs"
                mkdir -p "${{LOGS}}"

                alerts="${{LOGS}}/alerts.csv"
                log="${{LOGS}}/cron.signals.log"

                if [[ ! -s "${{alerts}}" ]]; then
                  printf '%s\\n' \\
                    'ts,pair,tf,score,filter_rejected,filter_reasons,provider' \\
                    >"${{alerts}}"
                fi

                for pair in EURUSD GBPUSD USDJPY; do
                  printf 'now,%s,M15,55,true,adx_regime_block,oanda\\n' \\
                    "${{pair}}" \\
                    >>"${{alerts}}"

                  printf '[FILTER now] %s M15 rejected_by_filter score=55 filters=adx_regime_block\\n' \\
                    "${{pair}}" \\
                    >>"${{log}}"
                done

                # Simulate the inner runner crashing after evidence lands on
                # disk. The reconciler will still see healthy per-pair rows
                # and derive EVALUATED_REJECTED — the false-green the outer
                # cycle must refuse to trust.
                exit {exit_code}
                """
            ),
            encoding="utf-8",
        )
        fake.chmod(0o755)

    def _install_clean_healthy_watcher(self) -> None:
        """Install a fake watcher that emits healthy evidence and exits 0."""
        fake = self.root / "tools" / "signal_watcher_pro.sh"
        fake.write_text(
            textwrap.dedent(
                """\
                #!/data/data/com.termux/files/usr/bin/bash
                set -uo pipefail

                LOGS="${BOTA_ROOT}/logs"
                mkdir -p "${LOGS}"

                alerts="${LOGS}/alerts.csv"
                log="${LOGS}/cron.signals.log"

                if [[ ! -s "${alerts}" ]]; then
                  printf '%s\\n' \\
                    'ts,pair,tf,score,filter_rejected,filter_reasons,provider' \\
                    >"${alerts}"
                fi

                for pair in EURUSD GBPUSD USDJPY; do
                  printf 'now,%s,M15,55,true,adx_regime_block,oanda\\n' \\
                    "${pair}" \\
                    >>"${alerts}"

                  printf '[FILTER now] %s M15 rejected_by_filter score=55 filters=adx_regime_block\\n' \\
                    "${pair}" \\
                    >>"${log}"
                done

                exit 0
                """
            ),
            encoding="utf-8",
        )
        fake.chmod(0o755)

    def _run_gate(self) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["BOTA_ROOT"] = str(self.root)
        env["WATCHER_GATED_MARKET_HINT"] = "MARKET_OPEN"
        env.pop("WATCHER_GATED_DRY_RUN", None)
        env.pop("BOTA_CYCLE_ID", None)
        env.pop("BOTA_REQUIRED_DECISIONS", None)
        env.pop("PAIRS", None)
        env.pop("TIMEFRAMES", None)
        return subprocess.run(
            ["bash", str(self.root / "tools" / "watcher_gated_cycle.sh")],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

    def _state(self) -> dict:
        return json.loads(
            (self.root / "state" / "pipeline_progress.json").read_text(
                encoding="utf-8"
            )
        )

    def test_inner_failure_with_healthy_aggregate_records_internal_error(
        self,
    ) -> None:
        self._install_fake_watcher(exit_code=17)

        completed = self._run_gate()

        # The outer contract: exit 0 means an authoritative terminal outcome
        # was persisted. The nonzero *inner* rc must not leak out because the
        # outer already recorded INTERNAL_ERROR for it.
        self.assertEqual(completed.returncode, 0, completed.stderr)

        state = self._state()
        watcher = state.get("components", {}).get("watcher", {})

        self.assertEqual(
            watcher.get("status"),
            "failed",
            "inner failure must produce status=failed regardless of aggregate",
        )
        self.assertEqual(
            watcher.get("terminal_outcome"),
            "INTERNAL_ERROR",
            "inner failure must produce terminal_outcome=INTERNAL_ERROR",
        )

        details = str(watcher.get("details") or "")
        self.assertIn("run_rc=17", details)
        # The pre-failure aggregate is what forensic reconstruction depends
        # on; without it, an operator cannot tell whether the failure hid
        # something benign (EVALUATED_REJECTED) or something dangerous
        # (DELIVERY_ATTEMPTED, DATA_FETCH_FAILED).
        self.assertIn(
            "aggregate=EVALUATED_REJECTED",
            details,
            f"pre-failure aggregate must be preserved in details: {details!r}",
        )

        summary = state.get("last_terminal_outcome", {})
        self.assertEqual(summary.get("terminal_outcome"), "INTERNAL_ERROR")
        self.assertEqual(summary.get("component"), "watcher")

        # Per-pair reconciled decisions must remain in the ledger for
        # forensic reconstruction — the fact that the outer cycle recorded
        # INTERNAL_ERROR does not erase the per-pair evidence.
        decisions = state.get("decisions", {})
        cycle_id = str(watcher.get("cycle_id") or "")
        self.assertTrue(cycle_id, "watcher terminal event must carry cycle_id")

        matching = [
            event
            for event in decisions.values()
            if isinstance(event, dict)
            and str(event.get("cycle_id") or "") == cycle_id
        ]
        self.assertTrue(
            matching,
            "per-pair reconciled decisions must remain in ledger for forensics",
        )

    def test_inner_success_still_records_healthy_aggregate(self) -> None:
        self._install_clean_healthy_watcher()

        completed = self._run_gate()

        self.assertEqual(completed.returncode, 0, completed.stderr)

        watcher = self._state().get("components", {}).get("watcher", {})

        self.assertEqual(watcher.get("status"), "completed")
        self.assertEqual(
            watcher.get("terminal_outcome"),
            "EVALUATED_REJECTED",
            "clean inner run must retain the healthy semantic aggregate",
        )
        details = str(watcher.get("details") or "")
        self.assertIn("run_rc=0", details)

    def test_inner_failure_with_no_reconciled_evidence_still_internal_error(
        self,
    ) -> None:
        # The fake watcher below never writes evidence and exits nonzero.
        # The reconciler will produce no per-pair events for this cycle, so
        # the aggregate falls through to DATA_FETCH_FAILED. Even so, the
        # inner rc must dominate — the outer terminal outcome must be
        # INTERNAL_ERROR and details must preserve the DATA_FETCH_FAILED
        # aggregate for forensics.
        fake = self.root / "tools" / "signal_watcher_pro.sh"
        fake.write_text(
            "#!/data/data/com.termux/files/usr/bin/bash\n"
            "exit 42\n",
            encoding="utf-8",
        )
        fake.chmod(0o755)

        completed = self._run_gate()
        self.assertEqual(completed.returncode, 0, completed.stderr)

        watcher = self._state().get("components", {}).get("watcher", {})
        self.assertEqual(watcher.get("status"), "failed")
        self.assertEqual(watcher.get("terminal_outcome"), "INTERNAL_ERROR")

        details = str(watcher.get("details") or "")
        self.assertIn("run_rc=42", details)
        self.assertIn("aggregate=", details)


if __name__ == "__main__":
    unittest.main()
