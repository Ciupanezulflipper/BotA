#!/usr/bin/env python3
from __future__ import annotations

import csv
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


present = load_module("telegram_signal_present", ROOT / "tools" / "telegram_signal_present.py")
daily = load_module("daily_report_modern", ROOT / "tools" / "daily_report_modern.py")


class TelegramPresentationTests(unittest.TestCase):
    def test_modern_signal_preserves_delivery_parser_contract(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "logs").mkdir(parents=True)
            alerts = root / "logs" / "alerts.csv"
            header = list(present.CURRENT_FIELDS)
            row = [
                "2026-09-11T11:20:03+0000", "GBPUSD", "M15", "SELL", "78.00", "78.00",
                "1.35082", "1.35182", "1.34883", "engine_A3", "false", "", 
                "ok|pullback_entry|adx=21.7", "1.2", "2.8", "9.9", "6.0", "21.7", "45.3",
                "-0.000099", "3", "SELL", "GREEN", "London", "trending",
            ]
            with alerts.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(header)
                offset = handle.tell()
                writer.writerow(row)

            old_env = os.environ.copy()
            try:
                os.environ["BOTA_MUTABLE_ROOT"] = str(root)
                os.environ["BOTA_ALERTS_OFFSET"] = str(offset)
                os.environ["BOTA_SERVER_EPOCH"] = "1789125601"
                legacy = (
                    "🔴 BotA GBPUSD M15 SELL\n━━━━━━━━━━━━━━\n"
                    "📊 Score: 78.00 | Confidence: 78.00\n"
                    "💰 Entry: 1.35082\n🛑 SL: 1.35182\n🎯 TP: 1.34883"
                )
                rendered = present.render(legacy)
            finally:
                os.environ.clear()
                os.environ.update(old_env)

            self.assertIn("BOTA · SELL SIGNAL", rendered)
            self.assertIn("GBP/USD · M15", rendered)
            self.assertIn("Signal Score: 78/100", rendered)
            self.assertIn("ADX: 21.7", rendered)
            self.assertIn("BotA GBPUSD M15 SELL", rendered)
            self.assertRegex(rendered, present.PAIR_RE)
            self.assertRegex(rendered, present.SCORE_RE)
            self.assertRegex(rendered, present.ENTRY_RE)

    def test_daily_report_proves_clean_zero_signal_day(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "logs").mkdir(parents=True)
            (root / "state").mkdir(parents=True)
            health = {
                "lifecycle": "RUNNING",
                "process_liveness": True,
                "release_git_sha": "e9e6bc31b1a0bba74a9947060372f7bd19ddaac3",
                "useful_progress": {
                    "updater": {"status": "PASS"},
                    "watcher": {"status": "PASS"},
                },
            }
            (root / "state" / "vps_orchestrator_health.json").write_text(json.dumps(health), encoding="utf-8")
            events = []
            cycle = "boot:1"
            for pair in daily.PAIRS:
                events.append({
                    "timestamp_utc": "2026-09-11T11:20:01+00:00",
                    "component": "watcher", "event_type": "decision", "cycle_id": cycle,
                    "pair": pair, "timeframe": "M15", "filter_rejected": True,
                    "outcome": "filter_rejected", "telegram_result": "not_attempted",
                    "rejection_gate": "score<65",
                })
            events.append({
                "timestamp_utc": "2026-09-11T11:20:01+00:00",
                "component": "watcher", "event_type": "component", "cycle_id": cycle,
                "status": "completed", "market_reason": "MARKET_OPEN",
            })
            with (root / "logs" / "pipeline_events.jsonl").open("w", encoding="utf-8") as handle:
                for event in events:
                    handle.write(json.dumps(event) + "\n")

            old_env = os.environ.copy()
            try:
                os.environ["BOTA_MUTABLE_ROOT"] = str(root)
                os.environ["BOTA_CODE_ROOT"] = str(root)
                with mock.patch.object(daily, "outcome_summary", return_value={"available": False}):
                    rendered = daily.render("2026-09-11")
            finally:
                os.environ.clear()
                os.environ.update(old_env)

            self.assertIn("System: ONLINE", rendered)
            self.assertIn("Scans: 3/3 completed", rendered)
            self.assertIn("0 signals — market scanned normally", rendered)
            self.assertIn("Status: NORMAL", rendered)


if __name__ == "__main__":
    unittest.main()
