from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools import deploy_weekend_production_final as deployer


class FinalWeekendProductionDeployerTests(unittest.TestCase):
    def test_self_check(self) -> None:
        self.assertEqual(deployer.self_check(), 0)

    def test_source_and_scope_are_frozen(self) -> None:
        self.assertEqual(
            deployer.SOURCE_COMMIT,
            "080e930a2150c7fcb60fbefb4892f1e7d05424fb",
        )
        self.assertEqual(deployer.PAIRS, ("EURUSD", "GBPUSD", "USDJPY"))
        self.assertEqual(len(deployer.FILES), 13)
        self.assertFalse(any("replay" in item.path for item in deployer.FILES))
        self.assertIn('export PAIRS="EURUSD GBPUSD USDJPY"', deployer.WATCHER_RUN)
        self.assertIn('export POLICY_B_SCORE_MIN="70"', deployer.WATCHER_RUN)
        self.assertIn('export POLICY_B_ADX_MAX="30"', deployer.WATCHER_RUN)
        self.assertIn('export NEWS_ON="0"', deployer.WATCHER_RUN)

    def test_cron_block_replacement_preserves_unrelated_jobs(self) -> None:
        current = "\n".join(
            [
                "1 2 * * * echo keep-one",
                deployer.BOTA_BEGIN,
                "*/15 * * * * old-bota",
                deployer.BOTA_END,
                "3 4 * * * echo keep-two",
            ]
        )
        preserved = deployer._strip_bota_block(current)
        self.assertIn("keep-one", preserved)
        self.assertIn("keep-two", preserved)
        self.assertNotIn("old-bota", preserved)

    def test_malformed_cron_markers_fail_closed(self) -> None:
        with self.assertRaises(deployer.DeploymentError):
            deployer._strip_bota_block(
                deployer.BOTA_BEGIN + "\nold\n" + deployer.BOTA_BEGIN
            )
        with self.assertRaises(deployer.DeploymentError):
            deployer._strip_bota_block(deployer.BOTA_END)

    def test_cache_validator_requires_all_three_pairs(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            cache = root / "cache"
            cache.mkdir()
            for pair in ("EURUSD", "GBPUSD"):
                for tf in deployer.TIMEFRAMES:
                    (cache / f"indicators_{pair}_{tf}.json").write_text(
                        '{"pair":"%s","timeframe":"%s","tf_ok":true,"error":""}'
                        % (pair, tf),
                        encoding="utf-8",
                    )
                (cache / f"d1_trend_{pair}.json").write_text(
                    '{"pair":"%s","trend":"BUY"}' % pair,
                    encoding="utf-8",
                )
            self.assertFalse(deployer._validate_cache(root))


if __name__ == "__main__":
    unittest.main()
