from __future__ import annotations

import unittest
from pathlib import Path

from tests.test_predeploy_crash_consistency import (
    ControlPlaneZombieTests,
    PersistenceGateTests,
    TelegramCrashConsistencyTests,
)

HERE = Path(__file__).resolve().parents[1]


class WrapperHardeningV2Tests(unittest.TestCase):
    """Current wrapper invariants after the 2026-08-13 adversarial review."""

    def test_wrapper_enforces_persistence_contract_and_retains_failed_evidence(self):
        text = (HERE / "tools" / "run_signal_watcher_with_ledger.sh").read_text(encoding="utf-8")
        self.assertIn("watcher_persistence_gate.py", text)
        self.assertIn("watcher_cycle_contract.py", text)
        self.assertIn("persistence_exit_code=", text)
        self.assertIn("contract_exit_code=", text)
        self.assertIn('export BOTA_ALERTS_OFFSET="${alerts_offset}"', text)
        self.assertIn('export BOTA_TELEGRAM_RESULT_LOG="${telegram_result_log}"', text)
        self.assertIn('export BOTA_DELIVERY_STATE_DIR="${DELIVERY_STATE}"', text)
        self.assertIn("retained cycle_log=", text)
        self.assertIn("Success-only cleanup", text)
        self.assertNotIn("trap ", text)
        self.assertNotIn("assert ", text)

    def test_generation_barrier_precedes_all_runtime_setup(self):
        text = (HERE / "tools" / "run_signal_watcher_with_ledger.sh").read_text(encoding="utf-8")
        barrier = text.index("deployment_generation_barrier_active")
        mkdir = text.index('mkdir -p "${LOGS}"')
        sender = text.index("canonical telegram sender missing")
        watcher = text.index('bash "${TOOLS}/signal_watcher_pro.sh" --once')
        self.assertLess(barrier, mkdir)
        self.assertLess(barrier, sender)
        self.assertLess(barrier, watcher)
        self.assertIn('[[ -e "${DEPLOY_MARKER}" || -L "${DEPLOY_MARKER}" ]]', text)

    def test_canonical_boundary_repairs_only_sender_mode_and_fails_closed(self):
        outer = (HERE / "tools" / "run_signal_watcher_with_ledger.sh").read_text(encoding="utf-8")
        boundary = (HERE / "tools" / "signal_watcher_pro.sh").read_text(encoding="utf-8")

        # The outer runner checks identity/presence but does not reject the
        # GitHub contents API's default 100644 mode before the canonical boundary.
        self.assertIn('[[ ! -f "${TOOLS}/telegram_send.sh" ]]', outer)
        self.assertNotIn('[[ ! -x "${TOOLS}/telegram_send.sh" ]]', outer)

        # Only the canonical sender gets conditional owner-only mode repair.
        self.assertIn('if [[ ! -x "${SENDER}" ]]; then', boundary)
        self.assertIn('chmod 700 "${SENDER}"', boundary)
        self.assertIn('canonical_sender_chmod_failed=', boundary)
        self.assertIn('canonical_sender_not_executable=', boundary)
        executable_lines = [
            line.strip()
            for line in boundary.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        chmod_commands = [line for line in executable_lines if line.startswith("if ! chmod ")]
        self.assertEqual(chmod_commands, ['if ! chmod 700 "${SENDER}"; then'])
        self.assertTrue((HERE / "tools" / "telegram_send.sh").is_file())
        self.assertTrue((HERE / "tools" / "telegram_delivery.py").is_file())

    def test_wrapper_state_contract_does_not_trust_ambient_state(self):
        text = (HERE / "tools" / "run_signal_watcher_with_ledger.sh").read_text(encoding="utf-8")
        self.assertIn('WATCHER_STATE_RAW="${BOTA_WATCHER_STATE:-logs/state}"', text)
        self.assertIn('export BOTA_WATCHER_STATE="${DELIVERY_STATE}"', text)
        self.assertIn('export STATE="${DELIVERY_STATE}"', text)
        self.assertNotIn('WATCHER_STATE_RAW="${STATE:-}"', text)


if __name__ == "__main__":
    unittest.main()
