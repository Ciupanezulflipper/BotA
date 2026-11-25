"""Pre-registered 36-hour D1 freshness contract (2026-11-25).
Fresh <=36h; stale >36h; missing, invalid, or timezone-less updated_at
must return UNAVAILABLE/stale. No production connections.
"""
import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from d1_cache_contract import read_d1_trend
from test_runtime_health_hetzner_publisher import MOD, healthy_orchestrator_health

PREREGISTERED_MAX_AGE_HOURS = 36

class StalenessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root/"cache").mkdir()
        (self.root/"state").mkdir()
        (self.root/"state/vps_orchestrator_health.json").write_text(json.dumps(healthy_orchestrator_health()))
        self.now = datetime.now(timezone.utc)
        for pair in ("EURUSD","GBPUSD","USDJPY"):
            self.write(pair, self.now.isoformat())

    def write(self, pair, timestamp):
        data={"pair":pair,"trend":"BUY"}
        if timestamp is not None:
            data["updated_at"]=timestamp
        (self.root/"cache"/f"d1_trend_{pair}.json").write_text(json.dumps(data))

    def assert_stale(self, timestamp):
        self.write("EURUSD",timestamp)
        self.assertEqual(read_d1_trend(self.root,"EURUSD"),("UNAVAILABLE","stale"))
        payload=MOD.build_payload_hetzner(self.root)
        self.assertEqual(payload["bot_mode"],"DEGRADED")
        self.assertIn("d1_cache:EURUSD:stale",payload["failure_reasons"])

    def test_fresh_passes(self):
        self.write("EURUSD",(self.now-timedelta(hours=PREREGISTERED_MAX_AGE_HOURS-1)).isoformat())
        self.assertEqual(read_d1_trend(self.root,"EURUSD"),("BUY",None))
        self.assertEqual(MOD.build_payload_hetzner(self.root)["bot_mode"],"HEALTHY")

    def test_37_hours_blocks(self):
        self.assert_stale((self.now-timedelta(hours=PREREGISTERED_MAX_AGE_HOURS+1)).isoformat())

    def test_missing_updated_at_blocks(self):
        self.assert_stale(None)

    def test_unparseable_updated_at_blocks(self):
        self.assert_stale("invalid")

    def test_naive_timestamp_blocks(self):
        self.assert_stale("2026-11-25T10:00:00")

if __name__ == "__main__":
    unittest.main()
