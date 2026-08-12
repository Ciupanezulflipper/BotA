from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]


def load_module(name: str, relative: str):
    path = HERE / relative
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    if spec.loader is None:
        raise RuntimeError(f"missing loader for {relative}")
    spec.loader.exec_module(module)
    return module


ledger = load_module("watcher_cycle_ledger_fail_closed", "tools/watcher_cycle_ledger.py")


class TelegramEvidenceFailClosedTests(unittest.TestCase):
    def test_canonical_sender_failure_without_structured_result_is_unknown(self):
        outcome, telegram, _supabase, _rejection = ledger.log_outcome([
            "[TELEGRAM 2026-08-12T12:00:00-0400] GBPUSD M15 accepted score=84.90",
            "[TELEGRAM 2026-08-12T12:00:01-0400] FAILED: tools/telegram_send.sh error",
        ])
        self.assertEqual(outcome, "telegram_unknown_outcome")
        self.assertEqual(telegram, "unknown_outcome")
        self.assertIn(outcome, ledger.UNHEALTHY_OUTCOMES)

    def test_structured_definite_failure_refines_unknown_fallback(self):
        outcome, telegram = ledger.apply_structured_telegram(
            "telegram_unknown_outcome", "unknown_outcome", "definite_failure"
        )
        self.assertEqual((outcome, telegram), ("telegram_failed", "failed"))

    def test_structured_reconciled_success_refines_unknown_fallback(self):
        outcome, telegram = ledger.apply_structured_telegram(
            "telegram_unknown_outcome", "unknown_outcome", "reconciled_sent"
        )
        self.assertEqual((outcome, telegram), ("telegram_sent", "sent"))


if __name__ == "__main__":
    unittest.main()
