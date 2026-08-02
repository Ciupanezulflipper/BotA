#!/usr/bin/env python3
"""Regression tests for BotA's cache-only Telegram status policy."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUTOSTATUS = ROOT / "tools" / "autostatus.sh"
FORMAT_STATUS = ROOT / "tools" / "format_status.py"


def indicator_bundle(pair: str, timeframe: str, direction: int) -> dict[str, object]:
    """Return a valid indicator bundle with a deterministic trend direction."""
    bullish = direction > 0
    return {
        "pair": pair,
        "timeframe": timeframe,
        "price": 1.23456,
        "age_min": 10.0,
        "tf_ok": True,
        "tf_actual_min": {"H1": 60.0, "H4": 240.0, "D1": 1440.0}[timeframe],
        "weak": False,
        "error": "",
        "ema9": 2.0 if bullish else 1.0,
        "ema21": 1.0 if bullish else 2.0,
        "rsi": 60.0 if bullish else 40.0,
        "macd_hist": 0.1 if bullish else -0.1,
        "adx": 25.0,
        "atr": 0.001,
        "atr_pips": 10.0,
        "bb_upper": 1.3,
        "bb_middle": 1.2,
        "bb_lower": 1.1,
        "bb_squeeze": False,
    }


class StatusSourcePolicyTests(unittest.TestCase):
    """Protect the status path from hidden network and messaging regressions."""

    def test_formatter_uses_no_snapshot_or_budget_subprocess(self) -> None:
        source = FORMAT_STATUS.read_text(encoding="utf-8")
        self.assertNotIn("emit_snapshot.py", source)
        self.assertNotIn("api_credit_tracker.py", source)
        self.assertNotIn("subprocess", source)
        self.assertNotIn("urllib", source)
        self.assertNotIn("requests", source)

    def test_formatter_exposes_only_user_facing_labels(self) -> None:
        source = FORMAT_STATUS.read_text(encoding="utf-8")
        for label in ("STRONG BUY", "BUY", "HOLD", "SELL", "STRONG SELL"):
            self.assertIn(label, source)
        self.assertIn("not a trade entry", source.lower())
        self.assertNotIn("Vote ", source)
        self.assertNotIn("/9", source)

    def test_market_gate_runs_before_formatter(self) -> None:
        source = AUTOSTATUS.read_text(encoding="utf-8")
        self.assertIn("market_open.sh", source)
        self.assertLess(source.index("MARKET_STATE="), source.index("format_status.py"))


class FormatterBehaviorTests(unittest.TestCase):
    """Exercise the formatter against isolated canonical cache files."""

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "BotA"
        (self.root / "cache").mkdir(parents=True)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write_bundle(self, pair: str, timeframe: str, direction: int) -> None:
        path = self.root / "cache" / f"indicators_{pair}_{timeframe}.json"
        path.write_text(
            json.dumps(indicator_bundle(pair, timeframe, direction)),
            encoding="utf-8",
        )

    def run_formatter(self) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment["BOTA_ROOT"] = str(self.root)
        return subprocess.run(
            [sys.executable, str(FORMAT_STATUS)],
            cwd=ROOT,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )

    def test_cached_bull_and_bear_context_is_clear_and_non_actionable(self) -> None:
        for timeframe in ("H1", "H4", "D1"):
            self.write_bundle("EURUSD", timeframe, 1)
            self.write_bundle("GBPUSD", timeframe, -1)

        result = self.run_formatter()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("EUR/USD", result.stdout)
        self.assertIn("GBP/USD", result.stdout)
        self.assertIn("Overall trend: STRONG BUY", result.stdout)
        self.assertIn("Overall trend: STRONG SELL", result.stdout)
        self.assertIn("not a trade entry", result.stdout.lower())
        self.assertNotIn("Vote ", result.stdout)
        self.assertNotIn("/9", result.stdout)
        self.assertNotIn("API", result.stdout)
        self.assertNotIn(" UTC", result.stdout)

    def test_invalid_daily_cache_is_visible_and_fail_closed(self) -> None:
        for timeframe in ("H1", "H4", "D1"):
            self.write_bundle("EURUSD", timeframe, 1)
            self.write_bundle("GBPUSD", timeframe, -1)

        invalid_path = self.root / "cache" / "indicators_EURUSD_D1.json"
        invalid = indicator_bundle("EURUSD", "D1", 1)
        invalid.update(
            {
                "tf_ok": False,
                "tf_actual_min": 0.0,
                "weak": True,
                "error": "tf_mismatch",
            }
        )
        invalid_path.write_text(json.dumps(invalid), encoding="utf-8")

        result = self.run_formatter()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("D1: unavailable (tf_mismatch)", result.stdout)
        self.assertIn("Coverage: 2 of 3 timeframes", result.stdout)


class AutostatusMarketGateTests(unittest.TestCase):
    """Prove market closure prevents both formatting and Telegram delivery."""

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "BotA"
        for directory in (
            self.root / "tools",
            self.root / "tmp",
            self.root / "logs",
            self.root / "config",
        ):
            directory.mkdir(parents=True, exist_ok=True)
        self.marker = self.root / "formatter_called.txt"
        self.gate = self.root / "tools" / "market_open.sh"
        self.formatter = self.root / "tools" / "format_status.py"
        self.formatter.write_text(
            "#!/usr/bin/env python3\n"
            "from pathlib import Path\n"
            f"Path({str(self.marker)!r}).write_text('called', encoding='utf-8')\n"
            "print('cached technical context')\n",
            encoding="utf-8",
        )
        self.formatter.chmod(0o755)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write_gate(self, state: str, exit_code: int) -> None:
        self.gate.write_text(
            "#!/usr/bin/env bash\n"
            f"printf '%s\\n' {state!r}\n"
            f"exit {exit_code}\n",
            encoding="utf-8",
        )
        self.gate.chmod(0o755)

    def run_autostatus(self) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment.update(
            {
                "HOME": str(self.root.parent),
                "BOTA_ROOT": str(self.root),
                "AUTOSTATUS_DRY_RUN": "1",
            }
        )
        return subprocess.run(
            ["bash", str(AUTOSTATUS)],
            cwd=ROOT,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )

    def test_closed_market_skips_formatter(self) -> None:
        self.write_gate("Closed", 1)

        result = self.run_autostatus()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.marker.exists())
        log = (self.root / "logs" / "cron.autostatus.log").read_text(
            encoding="utf-8"
        )
        self.assertIn("SKIP: market_closed_or_clock_unavailable", log)

    def test_missing_market_gate_fails_closed(self) -> None:
        result = self.run_autostatus()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.marker.exists())
        log = (self.root / "logs" / "cron.autostatus.log").read_text(
            encoding="utf-8"
        )
        self.assertIn("SKIP: market_gate_missing_or_not_executable", log)

    def test_open_market_renders_cache_only_status(self) -> None:
        self.write_gate("Open", 0)

        result = self.run_autostatus()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(self.marker.exists())
        self.assertEqual(result.stdout.strip(), "cached technical context")
        log = (self.root / "logs" / "cron.autostatus.log").read_text(
            encoding="utf-8"
        )
        self.assertIn("DRY_RUN: status rendered; Telegram not called", log)


if __name__ == "__main__":
    unittest.main()
