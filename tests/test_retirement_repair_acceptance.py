"""Offline D1 acceptance tests. Exposure tests now exercise the shared watcher boundary in test_retirement_exposure.py."""
from __future__ import annotations

import contextlib
import io
import json
from datetime import datetime, timezone
import os
import tempfile
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]


class D1RetirementTests(unittest.TestCase):
    def decision(self, mutable_trend, release_trend=None):
        source = (ROOT / "tools/scoring_engine.sh").read_text(encoding="utf-8")
        start = source.index("# D1 trend filter")
        end = source.index("# Store pullback status", start)
        block = compile(source[start:end], "scoring_engine_d1_block", "exec")
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            release, mutable = base / "release", base / "mutable"
            for directory, trend in ((release, release_trend), (mutable, mutable_trend)):
                (directory / "cache").mkdir(parents=True)
                if trend is not None:
                    (directory / "cache/d1_trend_EURUSD.json").write_text(
                        json.dumps({"trend": trend, "updated_at": datetime.now(timezone.utc).isoformat()}), encoding="utf-8"
                    )
            namespace = {"os": os, "pair": "EURUSD", "direction": "BUY"}
            stderr = io.StringIO()
            with mock.patch.dict(os.environ, {
                "ROOT": str(release), "BOTA_ROOT": str(release),
                "BOTA_MUTABLE_ROOT": str(mutable),
            }, clear=True), contextlib.redirect_stderr(stderr):
                with mock.patch.object(sys, "path", [str(ROOT / "tools"), *sys.path]):
                    exec(block, namespace)
            return namespace, stderr.getvalue()

    def test_mutable_d1_overrides_conflicting_release_cache(self):
        result, _ = self.decision("SELL", "BUY")
        self.assertEqual(result["d1_trend"], "SELL")
        self.assertEqual(result["direction"], "HOLD")

    def test_missing_mutable_cache_blocks_signal_even_if_release_cache_exists(self):
        result, _ = self.decision(None, "BUY")
        self.assertEqual(result["direction"], "HOLD")
        self.assertNotEqual(result["d1_trend"], "ANY")

    def test_invalid_mutable_trend_blocks_signal(self):
        result, _ = self.decision("INVALID", None)
        self.assertEqual(result["direction"], "HOLD")
        self.assertNotEqual(result["d1_trend"], "ANY")


if __name__ == "__main__":
    unittest.main()
