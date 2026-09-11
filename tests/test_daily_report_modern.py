from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parents[1]
MODULE_PATH = HERE / "tools" / "daily_report_modern.py"


def load_module():
    spec = importlib.util.spec_from_file_location("daily_report_modern_test", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    if spec.loader is None:
        raise RuntimeError("missing loader")
    spec.loader.exec_module(module)
    return module


report = load_module()


class DailyReportModernTests(unittest.TestCase):
    def test_clean_zero_signal_day_is_explicit(self):
        alerts = []
        for pair in ("EURUSD", "GBPUSD", "USDJPY"):
            alerts.append(
                {
                    "pair": pair,
                    "tf": "M15",
                    "direction": "HOLD",
                    "score": 0.0,
                    "confidence": 40.0,
                    "entry": "0",
                    "sl": "0",
                    "tp": "0",
                    "rejected": True,
                    "filter_reasons": "score<65",
                }
            )
        events = [
            {
                "component": "watcher",
                "event_type": "component",
                "status": "completed",
                "market_reason": "MARKET_OPEN",
                "cycle_id": "cycle-1",
            }
        ]
        health = {
            "lifecycle": "RUNNING",
            "process_liveness": True,
            "release_git_sha": "e9e6bc31b1a0bba74a9947060372f7bd19ddaac3",
            "runtime_instance_id": "0eed0f3e-936f-4db8-be3c-41d4ceab83d6",
        }
        rendered = report.build_report(
            day="2026-09-11", alerts=alerts, events=events, health=health
        )
        self.assertIn("📊 BOTA · DAILY MARKET REPORT", rendered)
        self.assertIn("EUR/USD · 1 scans · 0 qualified", rendered)
        self.assertIn("GBP/USD · 1 scans · 0 qualified", rendered)
        self.assertIn("USD/JPY · 1 scans · 0 qualified", rendered)
        self.assertIn(
            "0 signals — market scanned normally; no setup satisfied BotA policy.", rendered
        )
        self.assertIn("BOTA • STATUS: NORMAL", rendered)

    def test_incomplete_collection_never_claims_clean_zero_signal_day(self):
        rendered = report.build_report(
            day="2026-09-11",
            alerts=[],
            events=[],
            health={"lifecycle": "RUNNING", "process_liveness": True},
        )
        self.assertNotIn(
            "0 signals — market scanned normally; no setup satisfied BotA policy.", rendered
        )
        self.assertIn("REVIEW REQUIRED", rendered)

    def test_qualified_setup_is_deduplicated_across_repeated_cycles(self):
        signal = {
            "pair": "GBPUSD",
            "tf": "M15",
            "direction": "SELL",
            "score": 75.0,
            "confidence": 75.0,
            "entry": "1.35000",
            "sl": "1.35100",
            "tp": "1.34800",
            "rejected": False,
            "filter_reasons": "",
        }
        alerts = [signal.copy(), signal.copy()]
        for pair in ("EURUSD", "USDJPY"):
            alerts.append(
                {
                    "pair": pair,
                    "tf": "M15",
                    "direction": "HOLD",
                    "score": 0.0,
                    "confidence": 40.0,
                    "entry": "0",
                    "sl": "0",
                    "tp": "0",
                    "rejected": True,
                    "filter_reasons": "score<65",
                }
            )
        events = [
            {
                "component": "watcher",
                "event_type": "component",
                "status": "completed",
                "market_reason": "MARKET_OPEN",
                "cycle_id": "cycle-1",
            }
        ]
        health = {"lifecycle": "RUNNING", "process_liveness": True}
        rendered = report.build_report(
            day="2026-09-11", alerts=alerts, events=events, health=health
        )
        self.assertIn("Qualified setups: 1", rendered)
        self.assertIn("1 unique qualified setup(s): 0 BUY · 1 SELL.", rendered)


if __name__ == "__main__":
    unittest.main()
