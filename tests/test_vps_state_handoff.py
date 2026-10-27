from __future__ import annotations
import json, tempfile, unittest
from pathlib import Path
from ops import vps_state_handoff as handoff

class HandoffTests(unittest.TestCase):
    def source(self, root: Path) -> Path:
        src=root/"phone"; (src/"logs/state").mkdir(parents=True); (src/"state/telegram_delivery").mkdir(parents=True)
        alerts=b"header\npending-row\n"; (src/"logs/alerts.csv").write_bytes(alerts)
        (src/"state/profitlab_delivery_cursor.json").write_text(json.dumps({"schema_version":"1.0","offset":7,"source_size":len(alerts)}))
        (src/"state/telegram_delivery"/("a"*64+".json")).write_text(json.dumps({"status":"unknown_outcome"}))
        (src/"logs/state/last_hash_EURUSD_M15.txt").write_text("b"*32+"\n")
        (src/"state/pause").write_text("export PAUSE_EURUSD=1\nexport PAUSE_USDJPY=1\n")
        (src/".env.runtime").write_text("TELEGRAM_BOT_TOKEN=secret")
        (src/"logs/state/last_sent_EURUSD_M15.txt").write_text("old-boot:123")
        return src
    def test_allowlist_validate_apply_preserves_pending_and_unknown(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); src=self.source(root); bundle=root/"bundle"; dest=root/"vps"
            manifest=handoff.build(src,bundle); handoff.validate(bundle); handoff.apply(bundle,dest)
            paths={x["path"] for x in manifest["files"]}
            self.assertIn("state/telegram_delivery/"+"a"*64+".json",paths)
            self.assertNotIn(".env.runtime",paths); self.assertFalse((dest/"logs/state/last_sent_EURUSD_M15.txt").exists())
            self.assertEqual(json.loads((dest/"state/profitlab_delivery_cursor.json").read_text())["offset"],7)
            self.assertEqual(json.loads((dest/"state/telegram_delivery"/("a"*64+".json")).read_text())["status"],"unknown_outcome")
            pause=(dest/"state/pause").read_text().splitlines()
            self.assertIn("export PAUSE_EURUSD=1",pause)
            self.assertTrue(any(line == "export PAUSE_EURUSD=1" for line in pause))
    def test_out_of_range_cursor_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); src=self.source(root); (src/"state/profitlab_delivery_cursor.json").write_text('{"offset":999}')
            with self.assertRaisesRegex(handoff.HandoffError,"out_of_range"): handoff.build(src,root/"bundle")
    def test_malformed_telegram_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); src=self.source(root); next((src/"state/telegram_delivery").glob("*.json")).write_text('{bad')
            with self.assertRaisesRegex(handoff.HandoffError,"malformed_json"): handoff.build(src,root/"bundle")
    def test_profitlab_pair_must_be_complete(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); src=self.source(root); (src/"state/profitlab_delivery_cursor.json").unlink()
            with self.assertRaisesRegex(handoff.HandoffError,"pair_incomplete"): handoff.build(src,root/"bundle")

    def test_invalid_pause_representations_are_rejected(self):
        invalid = [
            '{"paused":true}', "PAUSE_EURUSD=1\n", "export PAUSE_AUDUSD=1\n",
            "export PAUSE_EURUSD=0\n", "export PAUSE_EURUSD=1\nexport PAUSE_EURUSD=1\n",
            "export PAUSE_EURUSD=1\necho unsafe\n",
        ]
        for index, value in enumerate(invalid):
            with self.subTest(index=index), tempfile.TemporaryDirectory() as td:
                root=Path(td); src=self.source(root); (src/"state/pause").write_text(value)
                with self.assertRaisesRegex(handoff.HandoffError,"pause_state_"):
                    handoff.build(src,root/"bundle")
