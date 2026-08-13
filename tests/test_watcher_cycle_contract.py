from __future__ import annotations

import csv
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools import watcher_cycle_contract as contract


CURRENT_HEADER = [
    "ts", "pair", "tf", "direction", "score", "confidence", "entry", "sl", "tp", "provider",
    "filter_rejected", "filter_reasons", "reasons", "ema_comp", "rsi_comp", "macd_comp",
    "adx_comp", "adx_raw", "rsi_raw", "macd_hist_raw", "macro6", "h1_trend", "tier", "session",
    "adx_regime",
]


def row(pair: str, *, rejected: bool = True, tier: str = "LOW") -> list[str]:
    return [
        "2026-08-13T12:00:00+0000", pair, "M15", "HOLD" if rejected else "BUY",
        "0.00" if rejected else "84.90", "40.00" if rejected else "84.90",
        "0.00000" if rejected else "1.35379",
        "0.00000" if rejected else "1.35222",
        "0.00000" if rejected else "1.35692",
        "engine_A3", "true" if rejected else "false", "filter" if rejected else "", "reason",
        "", "", "", "", "", "", "", "", "", tier, "NY", "trending",
    ]


class WatcherCycleContractTests(unittest.TestCase):
    def make_cycle(self, td: str, rows: list[list[str]]):
        root = Path(td)
        logs = root / "logs"
        state = root / "state"
        logs.mkdir()
        state.mkdir()
        alerts = logs / "alerts.csv"
        with alerts.open("w", newline="", encoding="utf-8") as handle:
            csv.writer(handle).writerow(CURRENT_HEADER)
        offset = alerts.stat().st_size
        with alerts.open("a", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerows(rows)
        cycle_log = state / "watcher_cycle.test.log"
        cycle_log.write_text("cycle\n", encoding="utf-8")
        telegram = state / "watcher_telegram.test.jsonl"
        supabase = state / "watcher_supabase.test.jsonl"
        telegram.write_text("", encoding="utf-8")
        supabase.write_text("", encoding="utf-8")
        return root, alerts, offset, cycle_log, telegram, supabase

    def base_env(self, root: Path):
        return mock.patch.dict(os.environ, {
            "BOTA_ROOT": str(root),
            "PAIRS": "EURUSD GBPUSD USDJPY",
            "TIMEFRAMES": "M15",
        }, clear=False)

    def test_three_rejected_decisions_with_no_delivery_pass(self):
        with tempfile.TemporaryDirectory() as td:
            root, alerts, offset, log, tg, sb = self.make_cycle(
                td, [row("EURUSD"), row("GBPUSD"), row("USDJPY")]
            )
            with self.base_env(root):
                parsed = contract.parse_rows(alerts, offset)
                sent = contract.validate_telegram(parsed, contract.read_jsonl(tg))
                contract.validate_supabase(parsed, contract.read_jsonl(sb), "cycle-1", sent)

    def test_duplicate_current_cycle_decision_fails(self):
        with tempfile.TemporaryDirectory() as td:
            root, alerts, offset, _log, _tg, _sb = self.make_cycle(
                td, [row("EURUSD"), row("EURUSD"), row("GBPUSD"), row("USDJPY")]
            )
            with self.base_env(root):
                with self.assertRaisesRegex(ValueError, "decision_count_invalid:EURUSD:M15:2"):
                    contract.parse_rows(alerts, offset)

    def test_exact_terminal_skip_allows_one_missing_scope(self):
        with tempfile.TemporaryDirectory() as td:
            root, alerts, offset, log, _tg, _sb = self.make_cycle(
                td, [row("GBPUSD"), row("USDJPY")]
            )
            log.write_text(
                "[STALE 2026-08-13T12:00:00+0000] EURUSD M15 candle_stale age=9999s max=2700s last=x src=oanda -> SKIP\n",
                encoding="utf-8",
            )
            with self.base_env(root):
                skipped = contract.terminal_skip_scopes(log.read_text(encoding="utf-8"))
                parsed = contract.parse_rows(alerts, offset, skipped)
            self.assertNotIn(("EURUSD", "M15"), parsed)
            self.assertIn(("GBPUSD", "M15"), parsed)
            self.assertIn(("USDJPY", "M15"), parsed)

    def test_unknown_missing_scope_stays_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root, alerts, offset, log, _tg, _sb = self.make_cycle(
                td, [row("GBPUSD"), row("USDJPY")]
            )
            log.write_text(
                "[DEBUG 2026-08-13T12:00:00+0000] EURUSD M15 parse_error(tsv_empty)\n",
                encoding="utf-8",
            )
            with self.base_env(root):
                skipped = contract.terminal_skip_scopes(log.read_text(encoding="utf-8"))
                with self.assertRaisesRegex(ValueError, "decision_count_invalid:EURUSD:M15:0"):
                    contract.parse_rows(alerts, offset, skipped)

    def test_terminal_skip_for_unexpected_scope_fails(self):
        with tempfile.TemporaryDirectory() as td:
            root, _alerts, _offset, log, _tg, _sb = self.make_cycle(
                td, [row("EURUSD"), row("GBPUSD"), row("USDJPY")]
            )
            log.write_text(
                "[PAUSE 2026-08-13T12:00:00+0000] AUDUSD M15 skipped — daily -3R circuit breaker active\n",
                encoding="utf-8",
            )
            with self.base_env(root):
                with self.assertRaisesRegex(ValueError, "terminal_skip_scope_unexpected"):
                    contract.terminal_skip_scopes(log.read_text(encoding="utf-8"))

    def test_telegram_definite_failure_is_unhealthy(self):
        with tempfile.TemporaryDirectory() as td:
            root, alerts, offset, _log, tg, _sb = self.make_cycle(
                td, [row("EURUSD", rejected=False, tier="GREEN"), row("GBPUSD"), row("USDJPY")]
            )
            tg.write_text(json.dumps({
                "pair": "EURUSD", "timeframe": "M15", "direction": "BUY",
                "score": "84.90", "entry": "1.35379", "sl": "1.35222", "tp": "1.35692",
                "status": "definite_failure",
            }) + "\n", encoding="utf-8")
            with self.base_env(root):
                parsed = contract.parse_rows(alerts, offset)
                with self.assertRaisesRegex(ValueError, "telegram_delivery_unhealthy:definite_failure"):
                    contract.validate_telegram(parsed, contract.read_jsonl(tg))

    def test_supabase_failure_is_unhealthy(self):
        with tempfile.TemporaryDirectory() as td:
            root, alerts, offset, _log, tg, sb = self.make_cycle(
                td, [row("EURUSD", rejected=False, tier="GREEN"), row("GBPUSD"), row("USDJPY")]
            )
            tg_record = {
                "pair": "EURUSD", "timeframe": "M15", "direction": "BUY",
                "score": "84.90", "entry": "1.35379", "sl": "1.35222", "tp": "1.35692",
                "status": "sent",
            }
            tg.write_text(json.dumps(tg_record) + "\n", encoding="utf-8")
            sb.write_text(json.dumps({
                "cycle_id": "cycle-1", "pair": "EURUSD", "timeframe": "M15",
                "direction": "BUY", "entry": "1.35379", "tier": "GREEN",
                "status": "failed_publish",
            }) + "\n", encoding="utf-8")
            with self.base_env(root):
                parsed = contract.parse_rows(alerts, offset)
                sent = contract.validate_telegram(parsed, contract.read_jsonl(tg))
                with self.assertRaisesRegex(ValueError, "supabase_delivery_unhealthy:failed_publish"):
                    contract.validate_supabase(parsed, contract.read_jsonl(sb), "cycle-1", sent)

    def test_missing_supabase_after_green_telegram_send_fails_when_configured(self):
        with tempfile.TemporaryDirectory() as td:
            root, alerts, offset, _log, tg, sb = self.make_cycle(
                td, [row("EURUSD", rejected=False, tier="GREEN"), row("GBPUSD"), row("USDJPY")]
            )
            tg.write_text(json.dumps({
                "pair": "EURUSD", "timeframe": "M15", "direction": "BUY",
                "score": "84.90", "entry": "1.35379", "sl": "1.35222", "tp": "1.35692",
                "status": "sent",
            }) + "\n", encoding="utf-8")
            with self.base_env(root), mock.patch.dict(os.environ, {"SUPABASE_SERVICE_KEY": "configured"}):
                parsed = contract.parse_rows(alerts, offset)
                sent = contract.validate_telegram(parsed, contract.read_jsonl(tg))
                with self.assertRaisesRegex(ValueError, "supabase_evidence_missing_after_telegram_send"):
                    contract.validate_supabase(parsed, contract.read_jsonl(sb), "cycle-1", sent)

    def test_supabase_cycle_mismatch_fails(self):
        with tempfile.TemporaryDirectory() as td:
            root, alerts, offset, _log, _tg, sb = self.make_cycle(
                td, [row("EURUSD"), row("GBPUSD"), row("USDJPY")]
            )
            sb.write_text(json.dumps({
                "cycle_id": "other-cycle", "pair": "EURUSD", "timeframe": "M15",
                "direction": "BUY", "entry": "1.35379", "tier": "GREEN", "status": "published",
            }) + "\n", encoding="utf-8")
            with self.base_env(root):
                parsed = contract.parse_rows(alerts, offset)
                with self.assertRaisesRegex(ValueError, "supabase_cycle_id_mismatch"):
                    contract.validate_supabase(parsed, contract.read_jsonl(sb), "cycle-1", set())

    def test_supabase_unexpected_scope_fails(self):
        rows = {("EURUSD", "M15"): {
            "pair": "EURUSD", "timeframe": "M15", "direction": "BUY", "score": "84.90",
            "entry": "1.35379", "sl": "1.35222", "tp": "1.35692", "rejected": "false", "tier": "GREEN",
        }}
        record = {
            "cycle_id": "cycle-1", "pair": "GBPUSD", "timeframe": "M15",
            "direction": "BUY", "entry": "1.20000", "tier": "GREEN", "status": "published",
        }
        with self.assertRaisesRegex(ValueError, "supabase_scope_unexpected"):
            contract.validate_supabase(rows, [record], "cycle-1", set())

    def test_green_cannot_use_skipped_non_green_status(self):
        rows = {("EURUSD", "M15"): {
            "pair": "EURUSD", "timeframe": "M15", "direction": "BUY", "score": "84.90",
            "entry": "1.35379", "sl": "1.35222", "tp": "1.35692", "rejected": "false", "tier": "GREEN",
        }}
        record = {
            "cycle_id": "cycle-1", "pair": "EURUSD", "timeframe": "M15",
            "direction": "BUY", "entry": "1.35379", "tier": "GREEN", "status": "skipped_non_green",
        }
        with self.assertRaisesRegex(ValueError, "supabase_green_status_invalid"):
            contract.validate_supabase(rows, [record], "cycle-1", {("EURUSD", "M15")})

    def test_oversized_segment_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "evidence.log"
            path.write_bytes(b"x" * (contract.MAX_SEGMENT_BYTES + 1))
            with self.assertRaisesRegex(ValueError, "segment_too_large"):
                contract.bounded_segment(path, 0)


if __name__ == "__main__":
    unittest.main()
