from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools import deploy_weekend_production as deployer


class WeekendProductionDeployerTests(unittest.TestCase):
    def test_manifest_is_exact_pinned_runtime_closure(self) -> None:
        deployer._validate_manifest()
        self.assertEqual(deployer.SOURCE_COMMIT, "588624cba9eb905ca2c4c3fb46303eb692e6ea61")
        self.assertEqual(deployer.PAIRS, ("EURUSD", "GBPUSD", "USDJPY"))
        self.assertEqual(len(deployer.FILES), 13)
        paths = {item.path for item in deployer.FILES}
        self.assertEqual(
            paths,
            {
                "tools/signal_watcher_pro.sh",
                "tools/scoring_engine.sh",
                "tools/quality_filter.py",
                "tools/indicators_updater.sh",
                "tools/data_fetch_candles.sh",
                "tools/build_indicators.py",
                "tools/sr_score.py",
                "tools/market_open.sh",
                "tools/emit_snapshot.py",
                "tools/m15_h1_fusion.sh",
                "tools/production_signal_policy.py",
                "tools/sync_d1_trend_cache.py",
                "ops/bota_crontab.canonical",
            },
        )
        self.assertFalse(any("replay" in path for path in paths))

    def test_self_check_is_offline_and_nonmutating(self) -> None:
        self.assertEqual(deployer.self_check(), 0)

    def test_existing_bota_cron_block_is_replaced_without_touching_other_jobs(self) -> None:
        current = "\n".join(
            [
                "# unrelated job",
                "1 2 * * * echo keep-me",
                "",
                deployer.BOTA_BEGIN,
                "*/15 * * * * old-bota-job",
                deployer.BOTA_END,
                "",
                "# dividend job",
                "3 4 * * * echo dividend-keep",
            ]
        )
        preserved = deployer._strip_bota_block(current)
        self.assertIn("echo keep-me", preserved)
        self.assertIn("echo dividend-keep", preserved)
        self.assertNotIn("old-bota-job", preserved)
        self.assertNotIn(deployer.BOTA_BEGIN, preserved)

    def test_invalid_existing_cron_markers_fail_closed(self) -> None:
        with self.assertRaisesRegex(deployer.DeploymentError, "invalid existing"):
            deployer._strip_bota_block(
                deployer.BOTA_BEGIN + "\nold\n" + deployer.BOTA_BEGIN + "\n"
            )
        with self.assertRaisesRegex(deployer.DeploymentError, "unmatched"):
            deployer._strip_bota_block(deployer.BOTA_END + "\n")

    def test_extract_live_bota_block_requires_exactly_one_complete_block(self) -> None:
        text = "\n".join(
            [
                "# keep",
                deployer.BOTA_BEGIN,
                "*/15 * * * * watcher",
                deployer.BOTA_END,
                "# keep2",
            ]
        )
        block = deployer._extract_bota_block(text)
        self.assertEqual(
            block,
            deployer.BOTA_BEGIN
            + "\n*/15 * * * * watcher\n"
            + deployer.BOTA_END
            + "\n",
        )

    def test_indicator_cache_validation_covers_twelve_streams_and_three_trends(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            cache = root / "cache"
            cache.mkdir()
            for pair in deployer.PAIRS:
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
            self.assertTrue(deployer._validate_indicator_cache(root))

    def test_indicator_cache_validation_fails_on_missing_third_pair(self) -> None:
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
            self.assertFalse(deployer._validate_indicator_cache(root))


if __name__ == "__main__":
    unittest.main()
