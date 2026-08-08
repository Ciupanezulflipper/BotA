"""Regression coverage for the production runit watcher wrapper.

The wrapper must:
  * remain a persistent runit service (never exit normally),
  * invoke each scheduled iteration through tools/watcher_gated_cycle.sh so
    every cycle records exactly one terminal outcome in the ledger,
  * NOT invoke tools/signal_watcher_pro.sh directly (that path bypasses the
    gated ledger contract and hides pipeline failures),
  * preserve the exact three-pair Policy B / Telegram production env
    (any change here is a strategy change, out of scope for observability),
  * have a bounded sleep between iterations so a one-shot cycle exit cannot
    be turned into a tight CPU spin.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "ops" / "runit" / "bota-watcher.run"


class PersistentWatcherScopeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.text = RUNNER.read_text(encoding="utf-8")

    def test_runner_pins_three_pair_policy_b_scope(self) -> None:
        required = (
            'export PAIRS="EURUSD GBPUSD USDJPY"',
            'export TIMEFRAMES="M15"',
            'export POLICY_B_ENABLED="1"',
            'export POLICY_B_SCORE_MIN="70"',
            'export POLICY_B_ADX_MAX="30"',
            'export NEWS_ON="0"',
            'export FILTER_SCORE_MIN="65"',
            'export FILTER_SCORE_MIN_ALL="65"',
            'export TELEGRAM_MIN_SCORE="70"',
            'export TELEGRAM_TIER_YELLOW_MIN="70"',
            'export TELEGRAM_TIER_GREEN_MIN="75"',
            'export TELEGRAM_COOLDOWN_SECONDS="1800"',
            'export CANDLE_MAX_AGE_SECS="2700"',
            'export DRY_RUN_MODE="0"',
            'export TELEGRAM_ENABLED="1"',
        )
        for token in required:
            with self.subTest(token=token):
                self.assertIn(token, self.text)

    def test_runtime_env_is_loaded_before_pinned_nonsecret_scope(self) -> None:
        source_at = self.text.index('source "${RUNTIME_ENV}"')
        pairs_at = self.text.index('export PAIRS="EURUSD GBPUSD USDJPY"')
        self.assertLess(source_at, pairs_at)

    def test_runner_invokes_gated_cycle_not_signal_watcher_pro(self) -> None:
        self.assertIn('tools/watcher_gated_cycle.sh', self.text)

    def test_runner_does_not_directly_invoke_signal_watcher_pro(self) -> None:
        # The gated path calls signal_watcher_pro.sh indirectly through
        # run_signal_watcher_with_ledger.sh; this wrapper must never call it
        # itself, since that would bypass the terminal-outcome ledger.
        forbidden_patterns = (
            r'bash\s+"?\$\{?ROOT\}?[^"\n]*tools/signal_watcher_pro\.sh',
            r'exec\s+bash\s+"?\$\{?ROOT\}?[^"\n]*tools/signal_watcher_pro\.sh',
            r'"\$\{?ROOT\}?/tools/signal_watcher_pro\.sh"',
        )
        for pattern in forbidden_patterns:
            with self.subTest(pattern=pattern):
                self.assertIsNone(
                    re.search(pattern, self.text),
                    msg=f"wrapper must not directly invoke signal_watcher_pro.sh; found {pattern}",
                )

    def test_runner_has_bounded_sleep_between_cycles(self) -> None:
        # A sleep call between iterations is what guarantees the runit
        # supervisor does not tight-restart after a one-shot gated cycle.
        self.assertRegex(self.text, r'sleep\s+"\$\{SLEEP_SECONDS\}"')
        self.assertIn(': "${SLEEP_SECONDS:=300}"', self.text)
        # Enforce a lower-bound clamp so a misconfigured SLEEP_SECONDS
        # cannot devolve into a CPU spin.
        self.assertRegex(
            self.text,
            r'SLEEP_SECONDS\s*<\s*30',
        )

    def test_runner_uses_persistent_scheduler_loop(self) -> None:
        # Persistent loop: `while true; do ... done` around the gated cycle
        # is what keeps runit supervision alive between iterations rather
        # than exec-ing the one-shot script directly.
        self.assertRegex(self.text, r'while\s+true\s*;\s*do')
        self.assertNotRegex(self.text, r'exec\s+bash\s+"[^"]*watcher_gated_cycle\.sh"')

    def test_runner_logs_nonzero_gated_cycle_result(self) -> None:
        # A failed one-shot cycle must be visibly recorded, not swallowed.
        self.assertRegex(
            self.text,
            r'gated_cycle_rc',
        )
        self.assertIn('logs/error.log', self.text)


if __name__ == "__main__":
    unittest.main()
