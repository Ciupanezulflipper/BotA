from __future__ import annotations

import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parents[1]


def load_module(name: str, relative: str):
    path = HERE / relative
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    if spec.loader is None:
        raise RuntimeError(f"missing loader for {relative}")
    spec.loader.exec_module(module)
    return module


telegram = load_module("telegram_delivery_commit_ordering", "tools/telegram_delivery.py")


class TelegramCommitOrderingTests(unittest.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.root = Path(td.name)
        self.delivery_state = self.root / "logs" / "state"
        self.delivery_state.mkdir(parents=True)
        self.env = {
            "BOTA_ROOT": str(self.root),
            "BOTA_DELIVERY_STATE_DIR": str(self.delivery_state),
        }
        self.identity = {
            "pair": "GBPUSD",
            "timeframe": "M15",
            "direction": "BUY",
            "score": "84.90",
            "entry": "1.35379",
            "sl": "1.35222",
            "tp": "1.35692",
        }
        self.provenance = {
            "boot_id": "boot-test",
            "monotonic_ns": 123_000_000_000,
        }

    def test_structured_result_failure_leaves_delivery_hash_absent(self):
        with mock.patch.dict(os.environ, self.env, clear=False):
            with mock.patch.object(telegram, "emit_cycle_result", return_value=False):
                ok = telegram.finalize_confirmed_delivery(
                    self.identity,
                    self.provenance,
                    "sent",
                    {"message_id": 7812},
                )
        self.assertFalse(ok)
        cooldown = self.delivery_state / "last_sent_GBPUSD_M15.txt"
        delivery_hash = self.delivery_state / "last_hash_GBPUSD_M15.txt"
        self.assertTrue(cooldown.exists())
        self.assertFalse(delivery_hash.exists())

    def test_success_orders_cooldown_then_evidence_then_hash(self):
        calls: list[str] = []
        with mock.patch.object(
            telegram,
            "prepare_legacy_cooldown",
            side_effect=lambda *_args, **_kwargs: calls.append("cooldown") or True,
        ), mock.patch.object(
            telegram,
            "emit_cycle_result",
            side_effect=lambda *_args, **_kwargs: calls.append("evidence") or True,
        ), mock.patch.object(
            telegram,
            "commit_legacy_delivery_hash",
            side_effect=lambda *_args, **_kwargs: calls.append("hash") or True,
        ):
            ok = telegram.finalize_confirmed_delivery(
                self.identity,
                self.provenance,
                "sent",
                {"message_id": 7812},
            )
        self.assertTrue(ok)
        self.assertEqual(calls, ["cooldown", "evidence", "hash"])


if __name__ == "__main__":
    unittest.main()
