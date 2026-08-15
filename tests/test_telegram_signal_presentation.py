from __future__ import annotations

import csv
import importlib.util
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


HERE = Path(__file__).resolve().parents[1]
CORE = HERE / "tools" / "signal_watcher_core.sh"


def load_module(name: str, relative: str):
    path = HERE / relative
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    if spec.loader is None:
        raise RuntimeError(f"missing loader for {relative}")
    spec.loader.exec_module(module)
    return module


telegram = load_module("telegram_delivery_presentation", "tools/telegram_delivery.py")
sys.modules["telegram_delivery"] = telegram
guard = load_module("telegram_send_guard_presentation", "tools/telegram_send_guard.py")


def render(tier: str) -> str:
    source = CORE.read_text(encoding="utf-8")
    match = re.search(r"^format_telegram_signal_message\(\) \{.*?^\}", source, re.MULTILINE | re.DOTALL)
    if match is None:
        raise AssertionError("production Telegram formatter not found")
    command = match.group(0) + '\nformat_telegram_signal_message "$@"'
    emoji = "🟢" if tier == "GREEN" else "🟡"
    result = subprocess.run(
        [
            "bash", "-c", command, "formatter", tier, emoji, "EURUSD", "M15", "BUY",
            "82" if tier == "GREEN" else "68",
            "78" if tier == "GREEN" else "61",
            "1.12345", "1.12000", "1.13000",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


class TelegramSignalPresentationTests(unittest.TestCase):
    def test_green_is_multiline_complete_and_parser_compatible(self):
        message = render("GREEN")
        self.assertEqual(
            message.splitlines(),
            [
                "🟢 BotA EURUSD M15 BUY",
                "━━━━━━━━━━━━━━",
                "📊 Score: 82 | Confidence: 78",
                "💰 Entry: 1.12345",
                "🛑 SL: 1.12000",
                "🎯 TP: 1.13000",
            ],
        )
        self.assertNotIn(r"\n", message)
        self.assertEqual(
            telegram.parse_message(message),
            {"pair": "EURUSD", "timeframe": "M15", "direction": "BUY", "score": "82", "entry": "1.12345"},
        )

    def test_yellow_is_multiline_readable_without_trade_levels(self):
        message = render("YELLOW")
        self.assertEqual(
            message.splitlines(),
            [
                "🟡 BotA EURUSD M15 BUY",
                "━━━━━━━━━━━━━━",
                "📊 Score: 68 | Confidence: 61",
                "👀 Watchlist — confirmation pending",
            ],
        )
        self.assertNotIn(r"\n", message)
        for forbidden in ("Entry:", "SL:", "TP:", "macro6=", "H1_trend_"):
            self.assertNotIn(forbidden, message)
        self.assertEqual(
            telegram.parse_message(message),
            {"pair": "EURUSD", "timeframe": "M15", "direction": "BUY", "score": "68", "entry": ""},
        )

    def test_current_cycle_guard_accepts_green_and_yellow(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            alerts = root / "logs" / "alerts.csv"
            alerts.parent.mkdir(parents=True)
            rows = []
            for tier, score, confidence, entry in (
                ("GREEN", "82", "78", "1.12345"),
                ("YELLOW", "68", "61", "1.12345"),
            ):
                row = dict.fromkeys(telegram.CURRENT_FIELDS, "")
                row.update(
                    pair="EURUSD", tf="M15", direction="BUY", score=score,
                    confidence=confidence, entry=entry, filter_rejected="false", tier=tier,
                )
                rows.append([row[field] for field in telegram.CURRENT_FIELDS])

            with alerts.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerows(rows)

            env = {"BOTA_ROOT": str(root), "BOTA_ALERTS_OFFSET": "0"}
            with mock.patch.dict(os.environ, env, clear=False):
                self.assertEqual(guard.matching_rows(render("GREEN")), 1)
                self.assertEqual(guard.matching_rows(render("YELLOW")), 1)


if __name__ == "__main__":
    unittest.main()
