from __future__ import annotations

import importlib.util
import os
import sys
import unittest
from pathlib import Path
from unittest import mock


HERE = Path(__file__).resolve().parents[1]
MODULE_PATH = HERE / "tools" / "telegram_public_presentation.py"


def load_module():
    spec = importlib.util.spec_from_file_location("telegram_public_presentation_test", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    if spec.loader is None:
        raise RuntimeError("missing loader")
    spec.loader.exec_module(module)
    return module


presentation = load_module()


class TelegramPublicPresentationTests(unittest.TestCase):
    def test_green_legacy_message_becomes_modern_actionable_signal(self):
        legacy = (
            "🟢 BotA EURUSD M15 BUY\n"
            "━━━━━━━━━━━━━━\n"
            "📊 Score: 82 | Confidence: 78\n"
            "💰 Entry: 1.12345\n"
            "🛑 SL: 1.12000\n"
            "🎯 TP: 1.13000"
        )
        with mock.patch.dict(os.environ, {"BOTA_SERVER_EPOCH": "1789125601"}, clear=False):
            rendered = presentation.format_public_signal(legacy)
        self.assertIn("🟢 BOTA · BUY SIGNAL", rendered)
        self.assertIn("EUR/USD · M15", rendered)
        self.assertIn("🎯 Entry: 1.12345", rendered)
        self.assertIn("🛑 Stop Loss: 1.12000", rendered)
        self.assertIn("💰 Take Profit: 1.13000", rendered)
        self.assertIn("⚖️ R:R: 1:", rendered)
        self.assertIn("📊 Signal Score: 82/100", rendered)
        self.assertIn("BOTA • EURUSD • M15", rendered)
        self.assertNotIn("macro6=", rendered)

    def test_yellow_has_no_trade_levels(self):
        legacy = (
            "🟡 BotA GBPUSD M15 SELL\n"
            "━━━━━━━━━━━━━━\n"
            "📊 Score: 71 | Confidence: 70\n"
            "👀 Watchlist — confirmation pending"
        )
        rendered = presentation.format_public_signal(legacy)
        self.assertIn("🟡 BOTA · WATCHLIST", rendered)
        self.assertIn("GBP/USD · M15 · SELL", rendered)
        self.assertIn("Confirmation pending", rendered)
        for forbidden in ("Entry:", "Stop Loss:", "Take Profit:"):
            self.assertNotIn(forbidden, rendered)

    def test_invalid_identity_fails_closed_to_caller(self):
        with self.assertRaises(ValueError):
            presentation.format_public_signal("not a signal")


if __name__ == "__main__":
    unittest.main()
