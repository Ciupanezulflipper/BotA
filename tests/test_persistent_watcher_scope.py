from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "ops" / "runit" / "bota-watcher.run"


class PersistentWatcherScopeTests(unittest.TestCase):
    def test_runner_pins_three_pair_policy_b_scope(self) -> None:
        text = RUNNER.read_text(encoding="utf-8")
        required = (
            'export PAIRS="EURUSD GBPUSD USDJPY"',
            'export TIMEFRAMES="M15"',
            'export POLICY_B_ENABLED="1"',
            'export POLICY_B_SCORE_MIN="70"',
            'export POLICY_B_ADX_MAX="30"',
            'export NEWS_ON="0"',
            'export TELEGRAM_MIN_SCORE="70"',
            'export TELEGRAM_TIER_GREEN_MIN="75"',
            'export TELEGRAM_COOLDOWN_SECONDS="1800"',
            'exec bash "${ROOT}/tools/signal_watcher_pro.sh"',
        )
        for token in required:
            with self.subTest(token=token):
                self.assertIn(token, text)

    def test_runtime_env_is_loaded_before_pinned_nonsecret_scope(self) -> None:
        text = RUNNER.read_text(encoding="utf-8")
        source_at = text.index('source "${RUNTIME_ENV}"')
        pairs_at = text.index('export PAIRS="EURUSD GBPUSD USDJPY"')
        self.assertLess(source_at, pairs_at)


if __name__ == "__main__":
    unittest.main()
