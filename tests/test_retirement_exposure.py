"""Local exposure admission, real watcher decision and closer, offline sinks."""
from __future__ import annotations
import csv
import importlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import profitlab_delivery
import signal_closer

T0 = 1800000000
HOUR = 3600
PAIR = "USDJPY"

def iso(epoch):
    return datetime.fromtimestamp(epoch, timezone.utc).isoformat()

class ExposureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "state").mkdir()
        (self.root / "logs").mkdir()
        self.alerts = self.root / "logs/alerts.csv"
        self.sent = self.root / "sent.txt"
        text = (ROOT / "tools/signal_watcher_core.sh").read_text()
        append = text[text.index("append_alert_csv() {"):text.index("append_alert_csv() {")+text[text.index("append_alert_csv() {"):].index("\n}\n")+3]
        start = text.index("  local pair_o tf_o direction score conf entry sl tp provider rejected filter_str reasons")
        stop = text.index("\n}\n\nscan_once() {", start)
        self.harness = self.root / "watcher.sh"
        self.harness.write_text("""set -uo pipefail
MUTABLE_ROOT="$TEST_ROOT"
TOOLS="$TEST_TOOLS"
ALERTS_CSV="$TEST_ROOT/logs/alerts.csv"
ERRLOG="$TEST_ROOT/logs/error.log"
TELEGRAM_MIN_SCORE=70
TELEGRAM_TIER_GREEN_MIN_INT=75
TELEGRAM_TIER_YELLOW_MIN_INT=70
DRY_RUN_MODE=false
TELEGRAM_ENABLED=1
ts_iso() { date -u +%FT%TZ; }
log() { printf '%s %s\\n' "$1" "$2" >&2; }
is_true() { [[ "$1" == true ]]; }
is_false() { [[ "$1" == false ]]; }
signal_delivery_is_new() { return 0; }
telegram_cooldown_check() { return 0; }
telegram_cooldown_mark() { :; }
format_telegram_signal_message() { printf '%s' "$*"; }
send_telegram_message() { printf '%s\\n' "$1" >>"$TEST_ROOT/sent.txt"; }
# Telegram succeeds; the independent ProfitLab worker is still retrying.
complete_delivery_transaction() { return 1; }
"""+append+"\nprocess_pair_tf() {\n  local tsv=\"$TEST_TSV\"\n"+text[start:stop]+"\n}\nprocess_pair_tf\n")

    def run_watcher(self, entry="158.01", direction="SELL", epoch=T0):
        sl,tp=("158.5","156.8") if direction=="SELL" else ("157.5","159.2")
        tsv="\\t".join((PAIR,"M15",direction,"80","80",entry,sl,tp,"fixture","false","ok","fixture"))
        # Use literal tabs; the watcher consumes the real TSV decision.
        tsv=tsv.replace("\\t","\t")
        env={**os.environ,"TEST_ROOT":str(self.root),"TEST_TOOLS":str(ROOT/"tools"),"TEST_TSV":tsv,"BOTA_SERVER_EPOCH":str(epoch),"BOTA_MUTABLE_ROOT":str(self.root)}
        result=subprocess.run(["bash",str(self.harness)],env=env,capture_output=True,text=True)
        self.assertIn(result.returncode,(0,1),result.stderr)
        with self.alerts.open() as handle:
            row=dict(zip(profitlab_delivery.ALERT_FIELDS,list(csv.reader(handle))[-1]))
        return row, result

    def test_second_distinct_same_direction_blocks_both_sinks(self):
        first,_=self.run_watcher()
        self.assertTrue(profitlab_delivery.eligible(first))
        second,_=self.run_watcher("157.99",epoch=T0+300)
        self.assertFalse(profitlab_delivery.eligible(second))
        self.assertEqual(len(self.sent.read_text().splitlines()),1)
        self.assertIn("exposure",second["filter_reasons"])

    def test_opposite_direction_allowed(self):
        self.run_watcher()
        row,_=self.run_watcher("158.02","BUY",T0+300)
        self.assertTrue(profitlab_delivery.eligible(row))
        self.assertEqual(len(self.sent.read_text().splitlines()),2)

    def test_exact_retry_keeps_original_open_record(self):
        self.run_watcher()
        record=self.root/"state/open_exposure/USDJPY-SELL.json"
        self.assertTrue(record.is_file())
        old=record.read_bytes()
        row,_=self.run_watcher(epoch=T0+300)
        self.assertTrue(profitlab_delivery.eligible(row))
        self.assertEqual(record.read_bytes(),old)

    def test_closer_confirmed_matching_row_allows_reentry(self):
        self.run_watcher()
        record=self.root/"state/open_exposure/USDJPY-SELL.json"
        self.assertTrue(record.is_file())
        closed={"id":"first","status":"CLOSED","pair":PAIR,"direction":"SELL","timeframe":"M15",
                "entry_price":158.01,"stop_loss":158.5,"take_profit":156.8,"created_at":iso(T0+1)}
        with mock.patch.object(signal_closer,"MUTABLE_ROOT",self.root), mock.patch.object(signal_closer,"log"), mock.patch.object(signal_closer,"supabase_request",return_value=[closed]):
            signal_closer.close_signal("first","CLOSED",1.0,False,iso(T0+300))
        self.assertFalse(record.exists())
        row,_=self.run_watcher("157.99",epoch=T0+301)
        self.assertTrue(profitlab_delivery.eligible(row))

    def test_failed_patch_and_unrelated_close_do_not_release(self):
        self.run_watcher()
        record=self.root/"state/open_exposure/USDJPY-SELL.json"
        self.assertTrue(record.is_file())
        other={"id":"other","status":"CLOSED","pair":PAIR,"direction":"SELL","timeframe":"M15",
                "entry_price":157.99,"stop_loss":158.5,"take_profit":156.8,"created_at":iso(T0+1)}
        with mock.patch.object(signal_closer,"MUTABLE_ROOT",self.root), mock.patch.object(signal_closer,"log"), mock.patch.object(signal_closer,"supabase_request",side_effect=OSError("offline")):
            signal_closer.close_signal("first","CLOSED",1.0,False,iso(T0+300))
        self.assertTrue(record.is_file())
        with mock.patch.object(signal_closer,"MUTABLE_ROOT",self.root), mock.patch.object(signal_closer,"log"), mock.patch.object(signal_closer,"supabase_request",return_value=[other]):
            signal_closer.close_signal("other","CLOSED",1.0,False,iso(T0+300))
        self.assertTrue(record.is_file())

    def test_closer_normal_expiry_with_usable_candles(self):
        self.run_watcher()
        record=self.root/"state/open_exposure/USDJPY-SELL.json"
        self.assertTrue(record.is_file())
        for hours, expected in ((23,True),(24,False)):
            with mock.patch.object(sys,"argv",["closer"]), mock.patch.object(signal_closer,"MUTABLE_ROOT",self.root), mock.patch.object(signal_closer,"SUPABASE_KEY","fixture"), mock.patch.object(signal_closer,"safety_gate",return_value=False), mock.patch.object(signal_closer,"bulk_gate"), mock.patch.object(signal_closer,"compute_server_clock_epoch",return_value=T0+hours*HOUR), mock.patch.object(signal_closer,"configured_candle_provider",return_value="yahoo"), mock.patch.object(signal_closer,"get_active_signals",return_value=[]), mock.patch.object(signal_closer,"fetch_candles",return_value=([{"t":T0,"h":158.1,"l":157.9}],"fixture")), mock.patch.object(signal_closer,"log"), mock.patch.object(signal_closer.telegram_closure_delivery,"retry_pending_closures",return_value={"candidates":0,"sent":0,"skipped":0}):
                signal_closer.main()
            self.assertEqual(record.exists(),expected)
        row,_=self.run_watcher("157.99",epoch=T0+24*HOUR+1)
        self.assertTrue(profitlab_delivery.eligible(row))

    def test_hard_expiry_clears_stuck_record(self):
        self.run_watcher()
        row,_=self.run_watcher("157.99",epoch=T0+167*HOUR)
        self.assertFalse(profitlab_delivery.eligible(row))
        row,_=self.run_watcher("157.99",epoch=T0+168*HOUR)
        self.assertTrue(profitlab_delivery.eligible(row))

if __name__=="__main__":
    unittest.main()
