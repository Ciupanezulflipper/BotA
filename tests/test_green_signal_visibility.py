#!/usr/bin/env python3
"""Regression tests for GREEN signal visibility across Telegram cooldown."""
from __future__ import annotations

import os
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CORE = REPO / "tools" / "signal_watcher_core.sh"


def process_pair_tf_source() -> str:
    source = CORE.read_text(encoding="utf-8")
    start = source.index("process_pair_tf() {")
    end = source.index("\nscan_once() {", start)
    return source[start:end]


class GreenSignalCooldownVisibilityTests(unittest.TestCase):
    @staticmethod
    def run_case(score: str) -> tuple[subprocess.CompletedProcess[str], bool, bool]:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            tools = root / "tools"
            state = root / "state"
            tools.mkdir()
            state.mkdir()
            (tools / "news_filter_real.py").write_text(
                "def news_risk_gate(_pair):\n    return True, 'ok'\n",
                encoding="utf-8",
            )
            sent_marker = root / "telegram-sent"
            transaction_marker = root / "transaction-complete"

            shell = textwrap.dedent(
                f"""
                set -euo pipefail
                {process_pair_tf_source()}

                log() {{ :; }}
                candle_age_info() {{ printf '0\\t2026-10-30T11:45:00Z\\tfixture\\n'; }}
                raw_cache_path() {{ printf '/tmp/cache.json\\n'; }}
                indicators_mtime_age_secs() {{ printf '0\\n'; }}
                run_fusion() {{ printf '{{}}\\n'; }}
                payload_is_blank() {{ return 1; }}
                parse_payload_tsv() {{
                  printf 'USDJPY\\tM15\\tSELL\\t{score}\\t{score}\\t157.09801\\t157.38907\\t156.51589\\tengine_A3\\tfalse\\tmacro6=3 | H1_trend_confirmed\\tok|adx=29.9|rsi=37.5|macd_hist=-0.024673\\n'
                }}
                append_alert_csv() {{ :; }}
                ts_iso() {{ printf '2026-10-30T11:45:03+0000\\n'; }}
                telegram_cooldown_check() {{ return 1; }}
                signal_delivery_is_new() {{ return 0; }}
                format_telegram_signal_message() {{ printf 'message\\n'; }}
                send_telegram_message() {{ : > "$SENT_MARKER"; return 0; }}
                telegram_cooldown_mark() {{ :; }}
                complete_delivery_transaction() {{ : > "$TRANSACTION_MARKER"; return 0; }}
                is_true() {{ [[ "${1:-}" == "true" || "${1:-}" == "1" ]]; }}
                is_false() {{ [[ "${1:-}" == "false" || "${1:-}" == "0" ]]; }}

                process_pair_tf USDJPY M15
                """
            )

            env = os.environ.copy()
            env.update(
                {
                    "TOOLS": str(tools),
                    "STATE": str(state),
                    "MUTABLE_ROOT": str(root),
                    "CANDLE_MAX_AGE_SECS": "900",
                    "INDICATOR_LAG_WARN_SECS": "0",
                    "TELEGRAM_MIN_SCORE": "0",
                    "TELEGRAM_TIER_GREEN_MIN_INT": "75",
                    "TELEGRAM_TIER_YELLOW_MIN_INT": "70",
                    "TELEGRAM_COOLDOWN_SECONDS": "300",
                    "DRY_RUN_MODE": "false",
                    "TELEGRAM_ENABLED": "1",
                    "TELEGRAM_BOT_TOKEN": "synthetic-token",
                    "TELEGRAM_CHAT_ID": "synthetic-chat",
                    "ERRLOG": str(root / "error.log"),
                    "SENT_MARKER": str(sent_marker),
                    "TRANSACTION_MARKER": str(transaction_marker),
                }
            )
            completed = subprocess.run(
                ["/bin/bash", "-c", shell],
                cwd=REPO,
                env=env,
                text=True,
                capture_output=True,
                check=False,
                timeout=30,
            )
            return completed, sent_marker.exists(), transaction_marker.exists()

    def test_distinct_green_signal_bypasses_pair_cooldown(self) -> None:
        completed, sent, transaction = self.run_case("76.00")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertTrue(sent)
        self.assertTrue(transaction)

    def test_yellow_watchlist_remains_suppressed_by_pair_cooldown(self) -> None:
        completed, sent, transaction = self.run_case("71.50")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertFalse(sent)
        self.assertFalse(transaction)


if __name__ == "__main__":
    unittest.main()
