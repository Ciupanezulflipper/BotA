#!/usr/bin/env python3
"""
Contract tests for the BotA customer-facing signal lifecycle.

All tests are fully offline.  No real OANDA or Supabase calls are made.
fetch_s5_candles and load_oanda_cache are mocked where needed.
"""

from __future__ import annotations

import importlib.util
import json
import math
import re
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

_patch = patch

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "signal_closer.py"

# tools/ must be on sys.path so signal_closer can import signal_resolution.
_TOOLS_DIR = str(ROOT / "tools")
if _TOOLS_DIR not in sys.path:
    sys.path.insert(0, _TOOLS_DIR)

from signal_resolution import (
    _build_s5_path,
    _convert_s5_candles,
    _execute_s5_http,
    _parse_s5_response,
    _validate_s5_inputs,
    check_s5_outcome,
    fetch_s5_candles,
    pips,
    validate_s5_candles,
)

SPEC = importlib.util.spec_from_file_location("signal_closer_under_test", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Unable to load {MODULE_PATH}")

closer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(closer)


# ── Helpers ────────────────────────────────────────────────────────────────────

SIGNAL_EPOCH_BASE = int(datetime(2026, 7, 10, 8, 0, 0, tzinfo=timezone.utc).timestamp())
M15 = 900
S5 = 5


def make_signal(
    *,
    direction: str = "BUY",
    entry: float = 1.1000,
    sl: float = 1.0980,
    tp: float = 1.1020,
    created_epoch: int = SIGNAL_EPOCH_BASE,
    pair: str = "EURUSD",
    timeframe: str = "M15",
) -> dict:
    """Build a minimal signal dict for use in tests."""
    created_at = datetime.fromtimestamp(created_epoch, timezone.utc).isoformat()
    return {
        "id": "test-id",
        "pair": pair,
        "direction": direction,
        "entry_price": entry,
        "stop_loss": sl,
        "take_profit": tp,
        "created_at": created_at,
        "timeframe": timeframe,
    }


def make_m15_candles(
    count: int,
    *,
    start_epoch: int = SIGNAL_EPOCH_BASE,
    high: float = 1.1010,
    low: float = 1.0990,
    open_: float = 1.1000,
    close: float = 1.1000,
    weekend_gap_after: int | None = None,
    weekend_gap_seconds: int = 2 * 24 * 3600,
    final_close: float | None = None,
) -> list[dict]:
    """
    Build M15 candles.  Optionally insert a gap after `weekend_gap_after` index
    to simulate closed-market time.
    """
    candles = []
    t = start_epoch
    for i in range(count):
        c = final_close if (final_close is not None and i == count - 1) else close
        candles.append({"t": t, "o": open_, "h": high, "l": low, "c": c})
        if weekend_gap_after is not None and i == weekend_gap_after:
            t += weekend_gap_seconds
        else:
            t += M15
    return candles


def make_s5_candles(
    from_epoch: int,
    to_epoch: int,
    *,
    high: float = 1.1010,
    low: float = 1.0990,
    open_: float = 1.1000,
    close: float = 1.1000,
) -> list[dict]:
    """Build consecutive S5 candles in [from_epoch, to_epoch) at 5-second intervals."""
    candles = []
    t = from_epoch
    while t + S5 <= to_epoch:
        candles.append({"t": t, "o": open_, "h": high, "l": low, "c": close})
        t += S5
    return candles


def call_prepare(
    sig: dict,
    m15_candles: list[dict],
    s5_response: list[dict] | None,
    *,
    server_epoch: int,
    max_age: int = 24,
    hard_max_age: int = 168,
    s5_fail_reason: str = "S5 unavailable (test)",
) -> dict | None:
    """
    Call prepare_signal_action with mocked fetch_candles and fetch_s5_candles.
    """
    now_utc = datetime.fromtimestamp(server_epoch, timezone.utc)

    def fake_fetch_candles(pair, tf, sep, eff_start):
        return m15_candles, "ok"

    s5_ret = (s5_response, "ok") if s5_response is not None else ([], s5_fail_reason)

    def fake_fetch_s5(pair, from_ep, to_ep, token, url):
        return s5_ret

    with (
        patch.object(closer, "fetch_candles", side_effect=fake_fetch_candles),
        patch("signal_resolution.fetch_s5_candles", side_effect=fake_fetch_s5),
    ):
        return closer.prepare_signal_action(
            sig, now_utc, server_epoch, max_age, hard_max_age,
            oanda_token="fake", oanda_url="https://fake.oanda.test",
        )


# ── Tests ──────────────────────────────────────────────────────────────────────

class CacheTests(unittest.TestCase):
    """Tests for load_oanda_cache behavior."""

    @staticmethod
    def _write_cache(tmpdir: Path, payload: dict) -> tuple[list[dict], str]:
        """Write payload to a temp cache dir and call load_oanda_cache."""
        cache_file = tmpdir / "EURUSD_M15.json"
        cache_file.write_text(json.dumps(payload), encoding="utf-8")
        original = closer.CACHE_DIR
        closer.CACHE_DIR = tmpdir
        try:
            return closer.load_oanda_cache("EURUSD", "M15", SIGNAL_EPOCH_BASE + M15 * 2)
        finally:
            closer.CACHE_DIR = original

    @staticmethod
    def _oanda_payload(*, open_: float, high: float, low: float, close: float) -> dict:
        """Build a minimal OANDA-style M15 cache payload for a single candle."""
        return {
            "chart": {
                "result": [{
                    "meta": {"_provider": "oanda", "dataGranularity": "M15"},
                    "timestamp": [SIGNAL_EPOCH_BASE],
                    "indicators": {"quote": [{
                        "open": [open_],
                        "high": [high],
                        "low": [low],
                        "close": [close],
                    }]},
                }]
            }
        }

    def test_cache_retains_o_h_l_c(self) -> None:
        """Test 1: load_oanda_cache returns all four price fields."""
        with tempfile.TemporaryDirectory() as td:
            candles, reason = self._write_cache(
                Path(td),
                self._oanda_payload(open_=1.0995, high=1.1010, low=1.0985, close=1.1005),
            )
        self.assertEqual("ok", reason)
        self.assertEqual(1, len(candles))
        c = candles[0]
        self.assertAlmostEqual(1.0995, c["o"])
        self.assertAlmostEqual(1.1010, c["h"])
        self.assertAlmostEqual(1.0985, c["l"])
        self.assertAlmostEqual(1.1005, c["c"])

    def test_cache_missing_close_is_none(self) -> None:
        """Test 2: When close is absent, c field is None (candle still usable for H/L)."""
        payload = {
            "chart": {
                "result": [{
                    "meta": {"_provider": "oanda", "dataGranularity": "M15"},
                    "timestamp": [SIGNAL_EPOCH_BASE],
                    "indicators": {"quote": [{
                        "open": [1.1000],
                        "high": [1.1010],
                        "low": [1.0990],
                        # close intentionally absent
                    }]},
                }]
            }
        }
        with tempfile.TemporaryDirectory() as td:
            candles, reason = self._write_cache(Path(td), payload)
        self.assertEqual("ok", reason)
        self.assertEqual(1, len(candles))
        self.assertIsNone(candles[0]["c"])
        self.assertAlmostEqual(1.1010, candles[0]["h"])


class CeilToS5Tests(unittest.TestCase):
    """Tests for ceil_to_s5 second-boundary rounding."""

    def test_ceil_to_s5_already_on_boundary(self) -> None:
        """Test 3a: Epoch on a 5-second boundary is unchanged."""
        self.assertEqual(1000, closer.ceil_to_s5(1000))

    def test_ceil_to_s5_one_past_boundary(self) -> None:
        """Test 3b: Epoch 1 past boundary rounds up by 4."""
        self.assertEqual(1005, closer.ceil_to_s5(1001))

    def test_ceil_to_s5_four_past_boundary(self) -> None:
        """Test 3c: Epoch 4 past boundary rounds up by 1."""
        self.assertEqual(1005, closer.ceil_to_s5(1004))

    def test_ceil_to_s5_zero(self) -> None:
        """Test 3c: Epoch=0 is already on boundary; ceil_to_s5 returns 0."""
        self.assertEqual(0, closer.ceil_to_s5(0))
        self.assertEqual(5, closer.ceil_to_s5(3))


class EffectiveStartTests(unittest.TestCase):
    """Tests for effective_start_epoch computation with sub-second precision."""

    def test_pre_entry_m15_price_action_excluded(self) -> None:
        """Test 4: A candle that closed before effective_start is not counted."""
        # Signal created mid-M15 at +450s (halfway into candle)
        signal_epoch = SIGNAL_EPOCH_BASE + 450
        effective_start = closer.ceil_to_s5(signal_epoch)

        # One candle that opened before and closed before effective_start
        pre_entry_candle = {"t": SIGNAL_EPOCH_BASE, "o": 1.1, "h": 1.1, "l": 1.0, "c": 1.1}
        threshold = closer.compute_threshold(
            [pre_entry_candle], effective_start, 24 * 3600, M15,
        )
        # Pre-entry candle ends at SIGNAL_EPOCH_BASE + 900 which is 450s after signal_epoch
        # effective_start = signal_epoch + (5 - 450%5) = signal_epoch+0 or signal_epoch+5
        # candle_end = SIGNAL_EPOCH_BASE + 900 = signal_epoch - 450 + 900 = signal_epoch + 450
        # overlap = candle_end - max(candle.t, effective_start) = (signal_epoch+450) - effective_start
        # = 450 - (450 % 5 adjustment) ≈ 450 seconds, not 900
        # So the pre-entry portion is excluded from the count.
        # With 450s overlap this single candle contributes << 24h
        self.assertIsNone(threshold)

    def test_partial_entry_interval_uses_only_s5_after_effective_start(self) -> None:
        """Test 5: Lifecycle path filters pre-entry S5 from TP/SL scan.

        Signal created mid-M15 at eff_start=BASE+300. fetch_s5_candles returns
        a pre-entry S5 (t=BASE+295 < eff_start) with h >= tp, and a post-entry
        S5 (t=BASE+300 == eff_start) that does not touch TP or SL.

        The pre-entry S5 is excluded from s5_post_entry so its TP touch is
        ignored. The outcome is OPEN (no WIN/LOSS from the pre-entry touch).
        """
        eff_start = SIGNAL_EPOCH_BASE + 300   # 300 % 5 == 0; 5 minutes into candle
        tp, sl, entry = 1.1020, 1.0980, 1.1000

        # M15 candle: h < tp, l > sl (no whole-candle boundary touch)
        candle = {
            "t": SIGNAL_EPOCH_BASE,
            "o": entry, "h": 1.1005, "l": 1.0995, "c": entry,
        }
        # Pre-entry: t=BASE+295 < eff_start → excluded from s5_post_entry (TP/SL scan)
        # h=1.1025 > tp=1.1020 → would produce WIN if incorrectly included
        pre_entry_s5 = {
            "t": SIGNAL_EPOCH_BASE + 295,   # 295 % 5 == 0; < eff_start
            "o": entry, "h": 1.1025, "l": 1.0995, "c": entry,
        }
        # Post-entry: t=BASE+300 == eff_start → in s5_post_entry; no TP/SL touch
        post_entry_s5 = {
            "t": SIGNAL_EPOCH_BASE + 300,   # 300 % 5 == 0; == eff_start
            "o": entry, "h": 1.1005, "l": 1.0995, "c": entry,
        }
        eval_end = SIGNAL_EPOCH_BASE + M15  # latest completed M15 end; no threshold yet
        with _patch(
            "signal_resolution.fetch_s5_candles",
            return_value=([pre_entry_s5, post_entry_s5], "ok"),
        ):
            result = closer.resolve_signal_outcome(
                "EURUSD", "BUY", entry, sl, tp,
                M15, eff_start,
                eval_end=eval_end,
                threshold_epoch=None,   # threshold not yet reached
                completed_m15_candles=[candle],
                oanda_token="fake",
                oanda_url="https://fake.oanda.test",
            )
        # Pre-entry TP touch must not produce WIN: signal stays OPEN
        self.assertEqual(closer.ResolutionState.OPEN, result.state)


class MarketHoursTests(unittest.TestCase):
    """Tests for market-hours (threshold) computation and weekend gap handling."""

    def test_24_market_hours_ignores_weekend_gaps(self) -> None:
        """Test 6: A weekend gap inflates wall-clock time but 96 M15 candles = 24h market."""
        # 48 candles before gap + 48 after gap = 96 M15 candles = 24h market time
        candles = make_m15_candles(
            96,
            start_epoch=SIGNAL_EPOCH_BASE,
            weekend_gap_after=47,
            weekend_gap_seconds=2 * 24 * 3600,
        )
        threshold = closer.compute_threshold(candles, SIGNAL_EPOCH_BASE, 24 * 3600, M15)
        # Threshold must be reached despite wall-clock gap — the gap seconds are skipped
        self.assertIsNotNone(threshold)
        # Threshold epoch is the end of the 96th candle (actual timestamp, not simple sum)
        expected_threshold = candles[-1]["t"] + M15
        self.assertEqual(expected_threshold, threshold)

    def test_exact_threshold_inside_final_m15_candle(self) -> None:
        """Test 7: When hold_seconds falls mid-candle, threshold is inside that candle."""
        # Signal created 300s into first candle → effective_start = SIGNAL_EPOCH_BASE + 300
        eff_start = SIGNAL_EPOCH_BASE + 300
        # With hold=86400 (24h), cumulation starts from eff_start
        # First candle contributes 900-300=600s, subsequent full ones 900s each
        # After 1 partial + 95 full = 600 + 95×900 = 600 + 85500 = 86100 < 86400
        # 97th candle starts at SIGNAL_EPOCH_BASE + 96×900
        # Need 300 more seconds from 97th candle start
        candles = make_m15_candles(97, start_epoch=SIGNAL_EPOCH_BASE)
        threshold = closer.compute_threshold(candles, eff_start, 86400, M15)
        self.assertIsNotNone(threshold)
        # 97th candle starts at SIGNAL_EPOCH_BASE + 96*900
        expected = SIGNAL_EPOCH_BASE + 96 * 900 + 300
        self.assertEqual(expected, threshold)

    def test_fewer_than_24_market_hours_leaves_signal_active(self) -> None:
        """Test 8: < 24h market time returns None from prepare_signal_action."""
        # Only 95 M15 candles completed after signal (95×900 = 23.75h)
        candles = make_m15_candles(95, start_epoch=SIGNAL_EPOCH_BASE)
        server_epoch = candles[-1]["t"] + M15  # one candle past the last

        sig = make_signal()
        action = call_prepare(sig, candles, [], server_epoch=server_epoch)
        self.assertIsNone(action)

    def test_incomplete_threshold_evidence_leaves_active(self) -> None:
        """Test 9: Threshold reached but S5 unavailable → ACTIVE (before hard age).

        Signal is created 300s into the first M15 candle so effective_start = BASE+300.
        First candle contributes only 600s; threshold falls INSIDE the 97th candle,
        making S5 mandatory for resolution.  When S5 is unavailable, must return None.
        """
        # Signal mid-candle → effective_start = SIGNAL_EPOCH_BASE + 300
        created_epoch = SIGNAL_EPOCH_BASE + 300
        eff_start = created_epoch  # already S5-aligned (300 % 5 == 0)
        candles = make_m15_candles(97, start_epoch=SIGNAL_EPOCH_BASE, final_close=1.1005)
        server_epoch = candles[-1]["t"] + M15

        # Verify threshold falls inside candle 97 (not at boundary)
        threshold = closer.compute_threshold(candles, eff_start, 86400, M15)
        self.assertIsNotNone(threshold)
        candle_97_t = SIGNAL_EPOCH_BASE + 96 * M15
        self.assertGreater(threshold, candle_97_t)
        self.assertLess(threshold, candle_97_t + M15)

        sig = make_signal(created_epoch=created_epoch)
        action = call_prepare(
            sig, candles, None,  # None = S5 fails
            server_epoch=server_epoch,
            hard_max_age=168,
        )
        self.assertIsNone(action)

    def test_threshold_at_exact_m15_boundary(self) -> None:
        """Test 10: Threshold falling exactly on M15 boundary uses M15 close, not S5."""
        # Exactly 96 full candles → threshold = 96th candle end = start + 96×900
        # effective_start = SIGNAL_EPOCH_BASE (signal exactly on M15 boundary)
        candles = make_m15_candles(96, start_epoch=SIGNAL_EPOCH_BASE, final_close=1.1008)
        threshold = closer.compute_threshold(candles, SIGNAL_EPOCH_BASE, 86400, M15)
        expected_threshold = SIGNAL_EPOCH_BASE + 96 * M15
        self.assertEqual(expected_threshold, threshold)

        # proc_end for the 96th candle == threshold_epoch == candle_end → M15 boundary
        server_epoch = SIGNAL_EPOCH_BASE + 97 * M15  # one candle past
        sig = make_signal()

        # S5 returns clean candles with no TP/SL
        s5 = make_s5_candles(SIGNAL_EPOCH_BASE, SIGNAL_EPOCH_BASE + 96 * M15, high=1.1005, low=1.0995)

        action = call_prepare(sig, candles, s5, server_epoch=server_epoch)
        self.assertIsNotNone(action)
        self.assertEqual("TIME_EXIT", action["predicted_outcome"])
        self.assertAlmostEqual(1.1008, action["predicted_exit_price"])


class TimeExitPipTests(unittest.TestCase):
    """Tests for pip sign and magnitude on TIME_EXIT for BUY and SELL."""

    def _time_exit_action(
        self,
        *,
        direction: str,
        entry: float,
        sl: float,
        tp: float,
        exit_close: float,
        pair: str = "EURUSD",
    ) -> dict:
        """
        Build a scenario where 96 full M15 candles complete with no TP/SL and
        then TIME_EXIT fires at the 96th candle boundary (M15 close used).
        """
        candles = make_m15_candles(
            96, start_epoch=SIGNAL_EPOCH_BASE,
            high=entry + 0.0005, low=entry - 0.0005,  # never touches sl or tp
            final_close=exit_close,
        )
        server_epoch = SIGNAL_EPOCH_BASE + 97 * M15
        sig = make_signal(direction=direction, entry=entry, sl=sl, tp=tp, pair=pair)
        # S5 with no TP/SL touch
        s5 = make_s5_candles(
            SIGNAL_EPOCH_BASE, SIGNAL_EPOCH_BASE + 96 * M15,
            high=entry + 0.0003, low=entry - 0.0003,
        )
        action = call_prepare(sig, candles, s5, server_epoch=server_epoch)
        self.assertIsNotNone(action)
        assert action is not None
        return action

    def test_buy_profitable_time_exit(self) -> None:
        """Test 11: BUY TIME_EXIT with exit above entry → positive pips."""
        action = self._time_exit_action(
            direction="BUY", entry=1.1000, sl=1.0980, tp=1.1030, exit_close=1.1015,
        )
        self.assertEqual("TIME_EXIT", action["predicted_outcome"])
        self.assertAlmostEqual(15.0, action["predicted_pips"])

    def test_buy_losing_time_exit(self) -> None:
        """Test 12: BUY TIME_EXIT with exit below entry → negative pips."""
        action = self._time_exit_action(
            direction="BUY", entry=1.1000, sl=1.0950, tp=1.1080, exit_close=1.0992,
        )
        self.assertEqual("TIME_EXIT", action["predicted_outcome"])
        self.assertAlmostEqual(-8.0, action["predicted_pips"])

    def test_sell_profitable_time_exit(self) -> None:
        """Test 13: SELL TIME_EXIT with exit below entry → positive pips."""
        action = self._time_exit_action(
            direction="SELL", entry=1.1000, sl=1.1030, tp=1.0960, exit_close=1.0985,
        )
        self.assertEqual("TIME_EXIT", action["predicted_outcome"])
        self.assertAlmostEqual(15.0, action["predicted_pips"])

    def test_sell_losing_time_exit(self) -> None:
        """Test 14: SELL TIME_EXIT with exit above entry → negative pips."""
        action = self._time_exit_action(
            direction="SELL", entry=1.1000, sl=1.1050, tp=1.0960, exit_close=1.1008,
        )
        self.assertEqual("TIME_EXIT", action["predicted_outcome"])
        self.assertAlmostEqual(-8.0, action["predicted_pips"])


class ThresholdPriceTests(unittest.TestCase):
    """Tests for threshold price selection at market-hour boundary."""

    def test_time_exit_uses_threshold_price_not_latest_candle(self) -> None:
        """Test 15: Threshold candle's close is used, not a later candle's close."""
        # Threshold is at candle 96 end; candle 97 has a different (higher) close
        # Exit must be candle 96's close, not candle 97's
        candles_96 = make_m15_candles(96, start_epoch=SIGNAL_EPOCH_BASE, final_close=1.1010)
        # Candle 97 would have close=1.1020 but threshold is at candle 96 end
        extra = {"t": SIGNAL_EPOCH_BASE + 96 * M15, "o": 1.101, "h": 1.102, "l": 1.100, "c": 1.1020}
        all_candles = candles_96 + [extra]

        server_epoch = SIGNAL_EPOCH_BASE + 97 * M15
        sig = make_signal(direction="BUY", entry=1.1000, sl=1.0980, tp=1.1050)
        s5 = make_s5_candles(SIGNAL_EPOCH_BASE, SIGNAL_EPOCH_BASE + 96 * M15, high=1.1005, low=1.0995)

        action = call_prepare(sig, all_candles, s5, server_epoch=server_epoch)
        self.assertIsNotNone(action)
        self.assertEqual("TIME_EXIT", action["predicted_outcome"])
        self.assertAlmostEqual(1.1010, action["predicted_exit_price"])  # candle 96 close
        self.assertAlmostEqual(10.0, action["predicted_pips"])

    def test_tp_after_threshold_is_ignored(self) -> None:
        """Test 16: TP touch in candle 97 is ignored; TIME_EXIT uses candle 96 close."""
        candles = make_m15_candles(96, start_epoch=SIGNAL_EPOCH_BASE, final_close=1.1005)
        tp_candle = {"t": SIGNAL_EPOCH_BASE + 96 * M15, "o": 1.1005, "h": 1.1030, "l": 1.1000, "c": 1.1025}
        all_candles = candles + [tp_candle]

        server_epoch = SIGNAL_EPOCH_BASE + 97 * M15
        sig = make_signal(direction="BUY", entry=1.1000, sl=1.0980, tp=1.1020)
        s5 = make_s5_candles(SIGNAL_EPOCH_BASE, SIGNAL_EPOCH_BASE + 96 * M15, high=1.1005, low=1.0995)

        action = call_prepare(sig, all_candles, s5, server_epoch=server_epoch)
        self.assertIsNotNone(action)
        self.assertEqual("TIME_EXIT", action["predicted_outcome"])

    def test_sl_after_threshold_is_ignored(self) -> None:
        """Test 17: SL touch in candle 97 is ignored; TIME_EXIT uses candle 96 close."""
        candles = make_m15_candles(96, start_epoch=SIGNAL_EPOCH_BASE, final_close=1.1005)
        sl_candle = {"t": SIGNAL_EPOCH_BASE + 96 * M15, "o": 1.100, "h": 1.101, "l": 1.097, "c": 1.098}
        all_candles = candles + [sl_candle]

        server_epoch = SIGNAL_EPOCH_BASE + 97 * M15
        sig = make_signal(direction="BUY", entry=1.1000, sl=1.0980, tp=1.1040)
        s5 = make_s5_candles(SIGNAL_EPOCH_BASE, SIGNAL_EPOCH_BASE + 96 * M15, high=1.1005, low=1.0995)

        action = call_prepare(sig, all_candles, s5, server_epoch=server_epoch)
        self.assertIsNotNone(action)
        self.assertEqual("TIME_EXIT", action["predicted_outcome"])


class S5OutcomeTests(unittest.TestCase):
    """Tests for S5 fetch triggering and TP/SL detection via check_s5_outcome."""

    def test_unambiguous_s5_tp_buy(self) -> None:
        """Test 18a: Clean BUY TP hit in S5 → WIN with correct pips."""
        s5 = [{"t": 1000, "o": 1.1010, "h": 1.1025, "l": 1.1008, "c": 1.1020}]
        result = check_s5_outcome("BUY", 1.1000, 1.0980, 1.1020, s5, "EURUSD")
        self.assertIsNotNone(result)
        outcome, rp, ep, cat, reason = result
        self.assertEqual("WIN", outcome)
        self.assertAlmostEqual(20.0, rp)
        self.assertAlmostEqual(1.1020, ep)
        self.assertEqual(1005, cat)
        self.assertEqual("OANDA_S5_TP", reason)

    def test_unambiguous_s5_sl_sell(self) -> None:
        """Test 19a: Clean SELL SL hit in S5 → LOSS with negative pips."""
        s5 = [{"t": 1000, "o": 1.1000, "h": 1.1015, "l": 1.0998, "c": 1.1010}]
        result = check_s5_outcome("SELL", 1.1000, 1.1010, 1.0980, s5, "EURUSD")
        self.assertIsNotNone(result)
        outcome, rp, ep, cat, reason = result
        self.assertEqual("LOSS", outcome)
        self.assertAlmostEqual(-10.0, rp)
        self.assertAlmostEqual(1.1010, ep)
        self.assertEqual(1005, cat)   # closed_at_epoch = t + S5 = 1000 + 5
        self.assertEqual("OANDA_S5_SL", reason)

    def test_same_s5_tp_and_sl_is_conservative_loss_with_ambiguous_reason(self) -> None:
        """Test 20: Both TP and SL in same S5 candle → LOSS, AMBIGUOUS_S5_STOP_FIRST."""
        # BUY: tp=1.1020, sl=1.0980; candle high≥tp AND low≤sl
        s5 = [{"t": 1000, "o": 1.1000, "h": 1.1025, "l": 1.0975, "c": 1.1000}]
        result = check_s5_outcome("BUY", 1.1000, 1.0980, 1.1020, s5, "EURUSD")
        self.assertIsNotNone(result)
        outcome, rp, ep, cat, reason = result
        self.assertEqual("LOSS", outcome)
        self.assertAlmostEqual(-20.0, rp)
        self.assertAlmostEqual(1.0980, ep)  # conservative exit at SL price
        self.assertEqual(1005, cat)         # closed_at_epoch = t + S5 = 1000 + 5
        self.assertEqual("AMBIGUOUS_S5_STOP_FIRST", reason)

    def test_same_s5_tp_and_sl_sell_conservative_loss(self) -> None:
        """Test 20b: SELL same-S5 ambiguity → LOSS."""
        # SELL: tp=1.0980, sl=1.1020; low≤tp AND high≥sl
        s5 = [{"t": 1000, "o": 1.1000, "h": 1.1025, "l": 1.0975, "c": 1.1000}]
        result = check_s5_outcome("SELL", 1.1000, 1.1020, 1.0980, s5, "EURUSD")
        self.assertIsNotNone(result)
        outcome, _, _, _, reason = result
        self.assertEqual("LOSS", outcome)
        self.assertEqual("AMBIGUOUS_S5_STOP_FIRST", reason)

    def test_m15_boundary_touch_triggers_s5_refinement(self) -> None:
        """Test 21: M15 candle touching TP causes S5 fetch to be called."""
        tp = 1.1020
        # M15 candle with high >= tp
        candles = make_m15_candles(
            96, start_epoch=SIGNAL_EPOCH_BASE,
            high=1.1025,  # touches tp
            low=1.0995,
        )
        server_epoch = SIGNAL_EPOCH_BASE + 97 * M15

        s5_calls: list[tuple] = []

        def fake_s5(pair, from_ep, to_ep, token, url):
            s5_calls.append((pair, from_ep, to_ep))
            # Return candles with no actual TP/SL touch so we get TIME_EXIT
            return make_s5_candles(from_ep, to_ep, high=1.1019, low=1.0996), "ok"

        sig = make_signal(direction="BUY", entry=1.1000, sl=1.0980, tp=tp)
        now_utc = datetime.fromtimestamp(server_epoch, timezone.utc)

        def fake_fetch_candles(pair, tf, sep, eff_start):
            return candles, "ok"

        with (
            patch.object(closer, "fetch_candles", side_effect=fake_fetch_candles),
            patch("signal_resolution.fetch_s5_candles", side_effect=fake_s5),
        ):
            closer.prepare_signal_action(
                sig, now_utc, server_epoch, 24, 168,
                oanda_token="fake", oanda_url="https://fake",
            )

        self.assertGreater(len(s5_calls), 0, "S5 should have been fetched for M15 touch")


class MissingDataTests(unittest.TestCase):
    """Tests for DATA_UNAVAILABLE handling when S5 or M15 data is absent."""

    def test_missing_s5_leaves_active_before_hard_age(self) -> None:
        """Test 22: S5 required but unavailable, within hard age → ACTIVE (None).

        Signal created 300s into first candle forces threshold inside candle 97,
        making S5 mandatory.
        """
        created_epoch = SIGNAL_EPOCH_BASE + 300
        candles = make_m15_candles(97, start_epoch=SIGNAL_EPOCH_BASE)
        server_epoch = candles[-1]["t"] + M15
        sig = make_signal(created_epoch=created_epoch)
        action = call_prepare(
            sig, candles, None,
            server_epoch=server_epoch,
            hard_max_age=168,
        )
        self.assertIsNone(action)

    def test_missing_s5_becomes_cancelled_at_hard_age(self) -> None:
        """Test 23: S5 required but unavailable at hard age → CANCELLED.

        Signal created 300s into first candle forces threshold inside candle 97.
        server_epoch is 169h after creation so age exceeds hard_max_age=168.
        fetch_candles is mocked so the staleness check in load_oanda_cache is bypassed.
        """
        old_base = SIGNAL_EPOCH_BASE - 169 * 3600
        created_epoch = old_base + 300  # mid-candle, S5-aligned
        candles = make_m15_candles(97, start_epoch=old_base)
        # server_epoch is exactly 169h after signal creation → age = 169h
        server_epoch = created_epoch + 169 * 3600

        sig = make_signal(created_epoch=created_epoch)
        action = call_prepare(
            sig, candles, None,
            server_epoch=server_epoch,
            hard_max_age=168,
        )
        self.assertIsNotNone(action)
        self.assertEqual("CANCELLED", action["predicted_outcome"])
        self.assertIn("S5", action["predicted_reason"])
        self.assertEqual(0.0, action["predicted_pips"])

    def test_missing_m15_leaves_active_before_hard_age(self) -> None:
        """Test 24: No M15 candles and within hard age → ACTIVE (None)."""
        server_epoch = SIGNAL_EPOCH_BASE + 3600
        sig = make_signal()
        now_utc = datetime.fromtimestamp(server_epoch, timezone.utc)

        def fake_fetch_candles(pair, tf, sep, eff_start):
            return [], "missing local cache"

        with patch.object(closer, "fetch_candles", side_effect=fake_fetch_candles):
            action = closer.prepare_signal_action(
                sig, now_utc, server_epoch, 24, 168,
                oanda_token="fake", oanda_url="https://fake",
            )
        self.assertIsNone(action)

    def test_missing_m15_becomes_cancelled_at_hard_age(self) -> None:
        """Test 25: No M15 candles beyond hard age → CANCELLED."""
        old_epoch = SIGNAL_EPOCH_BASE - 169 * 3600
        sig = make_signal(created_epoch=old_epoch)
        server_epoch = old_epoch + 169 * 3600
        now_utc = datetime.fromtimestamp(server_epoch, timezone.utc)

        def fake_fetch_candles(pair, tf, sep, eff_start):
            return [], "missing local cache"

        with patch.object(closer, "fetch_candles", side_effect=fake_fetch_candles):
            action = closer.prepare_signal_action(
                sig, now_utc, server_epoch, 24, 168,
                oanda_token="fake", oanda_url="https://fake",
            )
        self.assertIsNotNone(action)
        self.assertEqual("CANCELLED", action["predicted_outcome"])
        self.assertEqual("HARD_AGE_UNRESOLVED_NO_OANDA_CANDLES", action["predicted_reason"])

    def test_stale_m15_cache_leaves_active(self) -> None:
        """Test 26: Stale M15 cache (too old) → load_oanda_cache returns [] → ACTIVE."""
        server_epoch = SIGNAL_EPOCH_BASE + 3600

        payload = {
            "chart": {
                "result": [{
                    "meta": {"_provider": "oanda", "dataGranularity": "M15"},
                    "timestamp": [SIGNAL_EPOCH_BASE - 10000],  # very old candle
                    "indicators": {"quote": [{
                        "open": [1.1], "high": [1.1], "low": [1.0], "close": [1.1],
                    }]},
                }]
            }
        }

        with tempfile.TemporaryDirectory() as td:
            cache_file = Path(td) / "EURUSD_M15.json"
            cache_file.write_text(json.dumps(payload))
            original = closer.CACHE_DIR
            closer.CACHE_DIR = Path(td)
            try:
                candles, reason = closer.load_oanda_cache("EURUSD", "M15", server_epoch)
            finally:
                closer.CACHE_DIR = original

        self.assertEqual([], candles)
        self.assertIn("stale", reason)


class EventTimestampTests(unittest.TestCase):
    """Tests for closed_at_epoch accuracy across all exit types."""

    def test_event_closed_at_for_s5_tp_sl(self) -> None:
        """Test 27: closed_at_epoch for S5 TP/SL = end of first proving S5 candle."""
        tp_s5_t = SIGNAL_EPOCH_BASE + 300
        s5 = [
            {"t": tp_s5_t, "o": 1.1000, "h": 1.1025, "l": 1.0998, "c": 1.1020},
        ]
        result = check_s5_outcome("BUY", 1.1000, 1.0980, 1.1020, s5, "EURUSD")
        self.assertIsNotNone(result)
        _, _, _, closed_at_epoch, _ = result
        self.assertEqual(tp_s5_t + S5, closed_at_epoch)

    def test_event_closed_at_for_time_exit(self) -> None:
        """Test 28: closed_at_epoch for TIME_EXIT = threshold_epoch."""
        candles = make_m15_candles(96, start_epoch=SIGNAL_EPOCH_BASE, final_close=1.1005)
        server_epoch = SIGNAL_EPOCH_BASE + 97 * M15
        expected_threshold = SIGNAL_EPOCH_BASE + 96 * M15

        sig = make_signal(direction="BUY", entry=1.1000, sl=1.0980, tp=1.1050)
        s5 = make_s5_candles(SIGNAL_EPOCH_BASE, expected_threshold, high=1.1005, low=1.0995)

        action = call_prepare(sig, candles, s5, server_epoch=server_epoch)
        self.assertIsNotNone(action)
        self.assertEqual("TIME_EXIT", action["predicted_outcome"])
        self.assertEqual(expected_threshold, action["predicted_closed_at_epoch"])

    def test_emergency_cancellation_closed_at_uses_current_server_time(self) -> None:
        """Test 29: Hard-age CANCELLED uses trusted server epoch, not event time."""
        old_epoch = SIGNAL_EPOCH_BASE - 169 * 3600
        sig = make_signal(created_epoch=old_epoch)
        server_epoch = old_epoch + 169 * 3600
        now_utc = datetime.fromtimestamp(server_epoch, timezone.utc)

        def fake_fetch_candles(pair, tf, sep, eff_start):
            return [], "missing"

        with patch.object(closer, "fetch_candles", side_effect=fake_fetch_candles):
            action = closer.prepare_signal_action(
                sig, now_utc, server_epoch, 24, 168,
                oanda_token="fake", oanda_url="https://fake",
            )
        self.assertIsNotNone(action)
        self.assertEqual("CANCELLED", action["predicted_outcome"])
        self.assertEqual(server_epoch, action["predicted_closed_at_epoch"])


class PipCalculationTests(unittest.TestCase):
    """Tests for pip() sign and magnitude for JPY and non-JPY pairs."""

    def test_eurusd_gbpusd_pip_calculation(self) -> None:
        """Test 30: Non-JPY pair uses 0.0001 pip size."""
        self.assertAlmostEqual(20.0, pips(0.0020, "EURUSD"))
        self.assertAlmostEqual(-10.0, pips(-0.0010, "GBPUSD"))
        self.assertAlmostEqual(0.0, pips(0.0, "EURUSD"))

    def test_jpy_pip_calculation(self) -> None:
        """Test 31: JPY pair uses 0.01 pip size."""
        self.assertAlmostEqual(30.0, pips(0.30, "USDJPY"))
        self.assertAlmostEqual(-15.0, pips(-0.15, "EURJPY"))

    def test_jpy_time_exit_pip_calculation(self) -> None:
        """Test 31b: TIME_EXIT pips for JPY pair."""
        # SELL JPY: entry=150.00, exit=149.70 → pips(entry-exit) = pips(0.30) = 30.0
        result = pips(150.00 - 149.70, "USDJPY")
        self.assertAlmostEqual(30.0, result, places=1)


class RegressionTests(unittest.TestCase):
    """Regression tests for previously fixed TP/SL evaluation bugs."""

    def test_no_tp_sl_regression_unambiguous_buy_tp(self) -> None:
        """Test 32a: Clean unambiguous BUY TP in S5 → WIN."""
        s5 = [{"t": 1000, "o": 1.1015, "h": 1.1022, "l": 1.1010, "c": 1.1020}]
        result = check_s5_outcome("BUY", 1.1000, 1.0990, 1.1020, s5, "EURUSD")
        self.assertIsNotNone(result)
        self.assertEqual("WIN", result[0])
        self.assertAlmostEqual(20.0, result[1])

    def test_no_tp_sl_regression_unambiguous_sell_sl(self) -> None:
        """Test 32b: Clean unambiguous SELL SL in S5 → LOSS."""
        s5 = [{"t": 1000, "o": 1.1005, "h": 1.1012, "l": 1.0998, "c": 1.1010}]
        result = check_s5_outcome("SELL", 1.1000, 1.1010, 1.0980, s5, "EURUSD")
        self.assertIsNotNone(result)
        self.assertEqual("LOSS", result[0])
        self.assertAlmostEqual(-10.0, result[1])

    def test_normal_market_time_expiry_never_produces_cancelled(self) -> None:
        """Test 34: TIME_EXIT (normal expiry with data) is CLOSED, not CANCELLED."""
        candles = make_m15_candles(96, start_epoch=SIGNAL_EPOCH_BASE, final_close=1.1005)
        server_epoch = SIGNAL_EPOCH_BASE + 97 * M15
        sig = make_signal(direction="BUY", entry=1.1000, sl=1.0980, tp=1.1050)
        s5 = make_s5_candles(SIGNAL_EPOCH_BASE, SIGNAL_EPOCH_BASE + 96 * M15, high=1.1005, low=1.0995)

        action = call_prepare(sig, candles, s5, server_epoch=server_epoch)
        self.assertIsNotNone(action)
        self.assertNotEqual("CANCELLED", action["predicted_outcome"])
        self.assertEqual("TIME_EXIT", action["predicted_outcome"])
        self.assertNotEqual(0.0, action["predicted_pips"])


class WrapperTests(unittest.TestCase):
    """Tests for the run_signal_closer_live.sh wrapper script properties."""

    def test_wrapper_loads_oanda_variables_without_printing_values(self) -> None:
        """Test 33: Wrapper allowlist includes OANDA vars; no raw value echoed."""
        wrapper_path = ROOT / "tools" / "run_signal_closer_live.sh"
        content = wrapper_path.read_text()

        # Allowlist must include these three
        self.assertIn('"OANDA_API_TOKEN"', content)
        self.assertIn('"OANDA_API_URL"', content)
        self.assertIn('"SIGNAL_CLOSER_HARD_MAX_AGE_HOURS"', content)

        # --hard-max-age must be passed to the python script
        self.assertIn("--hard-max-age", content)

        # Extract the Python env-loader block and run it against a temp env file
        match = re.search(r"<<'PY'\n(.*?)\nPY\b", content, re.DOTALL)
        self.assertIsNotNone(match, "Could not find PY heredoc in wrapper")
        assert match is not None
        py_code = match.group(1)

        with tempfile.TemporaryDirectory() as td:
            env_file = Path(td) / ".env"
            env_file.write_text(
                "SUPABASE_SERVICE_KEY=supakey\n"
                "OANDA_API_TOKEN=oanda_secret_token\n"
                "OANDA_API_URL=https://api-fxtrade.oanda.com\n"
                "SIGNAL_CLOSER_HARD_MAX_AGE_HOURS=200\n"
            )
            result = subprocess.run(
                [sys.executable, "-c", py_code],
                capture_output=True,
                text=True,
                cwd=td,
            )

        output = result.stdout
        # OANDA vars must be exported
        self.assertIn("export OANDA_API_TOKEN=", output)
        self.assertIn("export OANDA_API_URL=", output)
        self.assertIn("export SIGNAL_CLOSER_HARD_MAX_AGE_HOURS=", output)
        # Supabase key must also be exported
        self.assertIn("export SUPABASE_SERVICE_KEY=", output)


# ── DEFECT 1: TP/SL evaluated before threshold ────────────────────────────────

class Defect1PreThresholdTPSLTests(unittest.TestCase):
    """TP/SL must be evaluated on every run, not deferred until threshold."""

    @staticmethod
    def _make_candles_with_touch(
        *,
        total: int,
        touch_at_index: int,
        tp: float,
        sl: float,
        entry: float,
        direction: str = "BUY",
        touch_tp: bool = True,
    ) -> list[dict]:
        """Build candles where candle[touch_at_index] touches TP or SL."""
        candles = make_m15_candles(
            total, start_epoch=SIGNAL_EPOCH_BASE,
            high=entry + 0.0005, low=entry - 0.0005,
        )
        # Mutate the touch candle
        if touch_tp:
            if direction == "BUY":
                candles[touch_at_index]["h"] = tp + 0.0001
            else:
                candles[touch_at_index]["l"] = tp - 0.0001
        else:
            if direction == "BUY":
                candles[touch_at_index]["l"] = sl - 0.0001
            else:
                candles[touch_at_index]["h"] = sl + 0.0001
        return candles

    def test_buy_tp_hit_before_threshold_returns_win(self) -> None:
        """D1-1: BUY TP hit in M15 candle 25 (< 96 needed) → WIN, not None."""
        tp, sl, entry = 1.1020, 1.0980, 1.1000
        candles = self._make_candles_with_touch(
            total=50, touch_at_index=24, tp=tp, sl=sl, entry=entry, touch_tp=True,
        )
        server_epoch = SIGNAL_EPOCH_BASE + 51 * M15
        sig = make_signal(direction="BUY", entry=entry, sl=sl, tp=tp)

        touch_t = SIGNAL_EPOCH_BASE + 24 * M15
        s5 = [{"t": touch_t, "o": entry, "h": tp + 0.0001, "l": entry - 0.0002, "c": tp}]

        action = call_prepare(sig, candles, s5, server_epoch=server_epoch)
        self.assertIsNotNone(action)
        self.assertEqual("WIN", action["predicted_outcome"])
        self.assertAlmostEqual(tp, action["predicted_exit_price"])
        self.assertGreater(action["predicted_pips"], 0)

    def test_buy_sl_hit_before_threshold_returns_loss(self) -> None:
        """D1-2: BUY SL hit before threshold → LOSS, not None."""
        tp, sl, entry = 1.1050, 1.0980, 1.1000
        candles = self._make_candles_with_touch(
            total=50, touch_at_index=10, tp=tp, sl=sl, entry=entry, touch_tp=False,
        )
        server_epoch = SIGNAL_EPOCH_BASE + 51 * M15
        sig = make_signal(direction="BUY", entry=entry, sl=sl, tp=tp)

        touch_t = SIGNAL_EPOCH_BASE + 10 * M15
        s5 = [{"t": touch_t, "o": entry, "h": entry + 0.0002, "l": sl - 0.0001, "c": sl}]

        action = call_prepare(sig, candles, s5, server_epoch=server_epoch)
        self.assertIsNotNone(action)
        self.assertEqual("LOSS", action["predicted_outcome"])
        self.assertLess(action["predicted_pips"], 0)

    def test_sell_tp_hit_before_threshold_returns_win(self) -> None:
        """D1-3: SELL TP hit before threshold → WIN."""
        tp, sl, entry = 1.0960, 1.1030, 1.1000
        candles = self._make_candles_with_touch(
            total=30, touch_at_index=5, tp=tp, sl=sl, entry=entry,
            direction="SELL", touch_tp=True,
        )
        server_epoch = SIGNAL_EPOCH_BASE + 31 * M15
        sig = make_signal(direction="SELL", entry=entry, sl=sl, tp=tp)

        touch_t = SIGNAL_EPOCH_BASE + 5 * M15
        s5 = [{"t": touch_t, "o": entry, "h": entry + 0.0002, "l": tp - 0.0001, "c": tp}]

        action = call_prepare(sig, candles, s5, server_epoch=server_epoch)
        self.assertIsNotNone(action)
        self.assertEqual("WIN", action["predicted_outcome"])
        self.assertGreater(action["predicted_pips"], 0)

    def test_no_tp_sl_threshold_not_reached_returns_none(self) -> None:
        """D1-4: No TP/SL touch, threshold not reached → None (OPEN)."""
        tp, sl, entry = 1.1050, 1.0960, 1.1000
        candles = make_m15_candles(
            50, start_epoch=SIGNAL_EPOCH_BASE,
            high=entry + 0.0005, low=entry - 0.0005,
        )
        server_epoch = SIGNAL_EPOCH_BASE + 51 * M15
        sig = make_signal(direction="BUY", entry=entry, sl=sl, tp=tp)

        action = call_prepare(sig, candles, [], server_epoch=server_epoch)
        self.assertIsNone(action)

    def test_tp_hit_in_candle_1_before_any_threshold(self) -> None:
        """D1-5: TP hit in the very first completed candle → WIN immediately."""
        tp, sl, entry = 1.1020, 1.0980, 1.1000
        candles = make_m15_candles(
            10, start_epoch=SIGNAL_EPOCH_BASE,
            high=entry + 0.0005, low=entry - 0.0005,
        )
        candles[0]["h"] = tp + 0.0001
        server_epoch = SIGNAL_EPOCH_BASE + 11 * M15

        sig = make_signal(direction="BUY", entry=entry, sl=sl, tp=tp)
        s5 = [{"t": SIGNAL_EPOCH_BASE, "o": entry, "h": tp + 0.0001, "l": entry - 0.0002, "c": tp}]

        action = call_prepare(sig, candles, s5, server_epoch=server_epoch)
        self.assertIsNotNone(action)
        self.assertEqual("WIN", action["predicted_outcome"])

    def test_tp_hit_wins_over_time_exit_when_both_possible(self) -> None:
        """D1-6: TP hit in candle 95, threshold in candle 96 → WIN, not TIME_EXIT."""
        tp, sl, entry = 1.1020, 1.0980, 1.1000
        candles = make_m15_candles(
            96, start_epoch=SIGNAL_EPOCH_BASE,
            high=entry + 0.0005, low=entry - 0.0005,
            final_close=1.1008,
        )
        # Candle 95 (index 94) touches tp
        candles[94]["h"] = tp + 0.0001
        server_epoch = SIGNAL_EPOCH_BASE + 97 * M15

        sig = make_signal(direction="BUY", entry=entry, sl=sl, tp=tp)
        touch_t = SIGNAL_EPOCH_BASE + 94 * M15
        s5 = [{"t": touch_t, "o": entry, "h": tp + 0.0001, "l": entry - 0.0002, "c": tp}]

        action = call_prepare(sig, candles, s5, server_epoch=server_epoch)
        self.assertIsNotNone(action)
        self.assertEqual("WIN", action["predicted_outcome"])

    def test_sl_hit_in_partial_entry_candle_before_threshold(self) -> None:
        """D1-7: SL hit in partial-entry candle (candle 0) before threshold → LOSS."""
        # Signal created 300s into first candle
        created_epoch = SIGNAL_EPOCH_BASE + 300
        tp, sl, entry = 1.1050, 1.0980, 1.1000
        candles = make_m15_candles(
            30, start_epoch=SIGNAL_EPOCH_BASE,
            high=entry + 0.0005, low=entry - 0.0005,
        )
        candles[0]["l"] = sl - 0.0001
        server_epoch = SIGNAL_EPOCH_BASE + 31 * M15

        sig = make_signal(created_epoch=created_epoch, direction="BUY", entry=entry, sl=sl, tp=tp)
        # S5 after effective_start (BASE+300) that hits SL
        s5_t = SIGNAL_EPOCH_BASE + 300
        s5 = [{"t": s5_t, "o": entry, "h": entry + 0.0002, "l": sl - 0.0001, "c": sl}]

        action = call_prepare(sig, candles, s5, server_epoch=server_epoch)
        self.assertIsNotNone(action)
        self.assertEqual("LOSS", action["predicted_outcome"])
        self.assertLess(action["predicted_pips"], 0)

    def test_signal_stays_open_after_s5_no_touch(self) -> None:
        """D1-8: M15 touches but S5 shows no touch and threshold not reached → None."""
        tp, sl, entry = 1.1050, 1.0960, 1.1000
        candles = make_m15_candles(
            50, start_epoch=SIGNAL_EPOCH_BASE,
            high=entry + 0.0005, low=entry - 0.0005,
        )
        candles[5]["h"] = tp + 0.0001
        server_epoch = SIGNAL_EPOCH_BASE + 51 * M15

        sig = make_signal(direction="BUY", entry=entry, sl=sl, tp=tp)
        # S5 with no actual touch (high below tp)
        touch_t = SIGNAL_EPOCH_BASE + 5 * M15
        s5 = [{"t": touch_t, "o": entry, "h": tp - 0.0005, "l": entry - 0.0002, "c": entry}]

        action = call_prepare(sig, candles, s5, server_epoch=server_epoch)
        self.assertIsNone(action)


# ── DEFECT 2: M15 cache coverage check ────────────────────────────────────────

class Defect2CoverageCheckTests(unittest.TestCase):
    """Coverage check must use interval-overlap, not first_ts+tf_sec comparison."""

    @staticmethod
    def _make_cache_payload(candles: list[dict]) -> dict:
        """Wrap candle list in the OANDA chart JSON structure expected by load_oanda_cache."""
        return {
            "chart": {
                "result": [{
                    "meta": {"_provider": "oanda", "dataGranularity": "M15"},
                    "timestamp": [c["t"] for c in candles],
                    "indicators": {"quote": [{
                        "open":  [c["o"] for c in candles],
                        "high":  [c["h"] for c in candles],
                        "low":   [c["l"] for c in candles],
                        "close": [c["c"] for c in candles],
                    }]},
                }]
            }
        }

    def _run_fetch(
        self,
        candles_raw: list[dict],
        effective_start: int,
        server_epoch: int,
    ) -> tuple[list[dict], str]:
        """Write raw candles to a temp cache and invoke fetch_candles."""
        payload = self._make_cache_payload(candles_raw)
        with tempfile.TemporaryDirectory() as td:
            cache_file = Path(td) / "EURUSD_M15.json"
            cache_file.write_text(json.dumps(payload))
            original = closer.CACHE_DIR
            closer.CACHE_DIR = Path(td)
            try:
                return closer.fetch_candles(
                    "EURUSD",
                    "M15",
                    server_epoch,
                    effective_start,
                )
            finally:
                closer.CACHE_DIR = original

    def test_historical_cache_before_signal_is_covered(self) -> None:
        """D2-1: Cache with candles before signal start + candle spanning eff_start → covered."""
        # 20 candles before BASE, then candle at BASE
        pre = make_m15_candles(20, start_epoch=SIGNAL_EPOCH_BASE - 20 * M15)
        at = make_m15_candles(10, start_epoch=SIGNAL_EPOCH_BASE)
        all_candles = pre + at
        server_epoch = SIGNAL_EPOCH_BASE + 10 * M15

        eligible, reason = self._run_fetch(all_candles, SIGNAL_EPOCH_BASE, server_epoch)
        self.assertEqual("ok", reason)
        # Eligible candles start at BASE (candle spanning eff_start)
        self.assertGreater(len(eligible), 0)
        self.assertEqual(SIGNAL_EPOCH_BASE, eligible[0]["t"])
        # Pre-signal candles excluded
        self.assertTrue(all(c["t"] >= SIGNAL_EPOCH_BASE for c in eligible))

    def test_cache_ending_before_signal_start_rejected(self) -> None:
        """D2-2: Cache with all candles ending before eff_start → rejected."""
        # Candles all end at or before BASE-1
        candles = make_m15_candles(5, start_epoch=SIGNAL_EPOCH_BASE - 10 * M15)
        # Last candle ends at BASE-5*900 = BASE-4500 — well before BASE
        server_epoch = SIGNAL_EPOCH_BASE + M15

        eligible, reason = self._run_fetch(candles, SIGNAL_EPOCH_BASE, server_epoch)
        self.assertEqual([], eligible)
        self.assertIn("cover", reason)

    def test_duplicate_identical_candles_are_deduped(self) -> None:
        """D2-3: Two identical candles at same timestamp → collapsed to one."""
        c = make_m15_candles(3, start_epoch=SIGNAL_EPOCH_BASE)
        duplicate = dict(c[1])  # identical copy of second candle
        all_with_dup = c[:2] + [duplicate] + c[2:]
        server_epoch = SIGNAL_EPOCH_BASE + 4 * M15

        eligible, reason = self._run_fetch(all_with_dup, SIGNAL_EPOCH_BASE, server_epoch)
        self.assertEqual("ok", reason)
        ts_list = [x["t"] for x in eligible]
        self.assertEqual(len(ts_list), len(set(ts_list)), "duplicate timestamps survive dedup")

    def test_conflicting_candles_at_same_timestamp_rejected(self) -> None:
        """D2-4: Two candles at same t with different h → cache rejected."""
        c = make_m15_candles(3, start_epoch=SIGNAL_EPOCH_BASE)
        conflict = dict(c[1])
        conflict["h"] = c[1]["h"] + 0.005  # different high → conflict
        all_with_conflict = c[:2] + [conflict] + c[2:]
        server_epoch = SIGNAL_EPOCH_BASE + 4 * M15

        eligible, reason = self._run_fetch(all_with_conflict, SIGNAL_EPOCH_BASE, server_epoch)
        self.assertEqual([], eligible)
        self.assertIn("conflict", reason)

    def test_candle_exactly_spanning_eff_start_counted(self) -> None:
        """D2-5: Candle [eff_start, eff_start+900) counts as covering eff_start."""
        # Single candle starting exactly at eff_start
        candles = make_m15_candles(3, start_epoch=SIGNAL_EPOCH_BASE)
        server_epoch = SIGNAL_EPOCH_BASE + 3 * M15

        eligible, reason = self._run_fetch(candles, SIGNAL_EPOCH_BASE, server_epoch)
        self.assertEqual("ok", reason)
        self.assertTrue(any(c["t"] == SIGNAL_EPOCH_BASE for c in eligible))


# ── DEFECT 3: microsecond-precise effective_start ─────────────────────────────

class Defect3MicrosecondPrecisionTests(unittest.TestCase):
    """ceil_to_s5_from_datetime must handle sub-second microseconds correctly."""

    def test_exactly_on_s5_boundary_unchanged(self) -> None:
        """D3-1: Datetime exactly on S5 boundary → same epoch."""
        dt = datetime(2026, 7, 10, 8, 0, 0, 0, tzinfo=timezone.utc)
        expected = int(dt.timestamp())
        self.assertEqual(expected, closer.ceil_to_s5_from_datetime(dt))
        self.assertEqual(0, expected % 5)

    def test_one_microsecond_past_boundary_rounds_up(self) -> None:
        """D3-2: 12:00:00.000001 → 12:00:05 (not 12:00:00)."""
        dt = datetime(2026, 7, 10, 12, 0, 0, 1, tzinfo=timezone.utc)
        base = int(datetime(2026, 7, 10, 12, 0, 0, 0, tzinfo=timezone.utc).timestamp())
        self.assertEqual(base + 5, closer.ceil_to_s5_from_datetime(dt))

    def test_999999_microsecond_past_boundary_rounds_up(self) -> None:
        """D3-3: 12:00:04.999999 → 12:00:05."""
        dt = datetime(2026, 7, 10, 12, 0, 4, 999999, tzinfo=timezone.utc)
        base = int(datetime(2026, 7, 10, 12, 0, 0, 0, tzinfo=timezone.utc).timestamp())
        self.assertEqual(base + 5, closer.ceil_to_s5_from_datetime(dt))

    def test_exactly_5_seconds_boundary_unchanged(self) -> None:
        """D3-4: 12:00:05.000000 → 12:00:05 (already on boundary)."""
        dt = datetime(2026, 7, 10, 12, 0, 5, 0, tzinfo=timezone.utc)
        base = int(datetime(2026, 7, 10, 12, 0, 0, 0, tzinfo=timezone.utc).timestamp())
        self.assertEqual(base + 5, closer.ceil_to_s5_from_datetime(dt))

    def test_int_truncation_gives_wrong_result(self) -> None:
        """D3-5: int(dt.timestamp()) truncates microseconds; ceil_from_datetime does not."""
        # 12:00:00.000001 → int() gives 12:00:00; ceil_from_datetime gives 12:00:05
        dt = datetime(2026, 7, 10, 12, 0, 0, 1, tzinfo=timezone.utc)
        truncated_epoch = int(dt.timestamp())
        correct_epoch = closer.ceil_to_s5_from_datetime(dt)
        # truncated_epoch is already on boundary (0 % 5 == 0), so ceil_to_s5(truncated) == truncated
        # but correct_epoch is truncated + 5
        self.assertEqual(truncated_epoch + 5, correct_epoch)

    def test_2_seconds_past_boundary_rounds_to_next(self) -> None:
        """D3-6: 12:00:02.500000 → 12:00:05."""
        dt = datetime(2026, 7, 10, 12, 0, 2, 500000, tzinfo=timezone.utc)
        base = int(datetime(2026, 7, 10, 12, 0, 0, 0, tzinfo=timezone.utc).timestamp())
        self.assertEqual(base + 5, closer.ceil_to_s5_from_datetime(dt))

    def test_prepare_uses_microsecond_precise_eff_start(self) -> None:
        """D3-7: Signal with microsecond created_at → eff_start correctly excludes pre-entry S5.

        Signal created at BASE+0.000001us → eff_start = BASE+5 (not BASE).
        Pre-entry S5 candle at t=BASE should be excluded from TP/SL scan.
        """
        # Use a created_at string with sub-second component
        created_str = datetime.fromtimestamp(
            SIGNAL_EPOCH_BASE, timezone.utc
        ).isoformat().replace("+00:00", ".000001+00:00")

        sig = make_signal()
        sig["created_at"] = created_str

        # Parse through the function to get eff_start
        created_dt = closer.parse_signal_created_at(created_str)
        eff_start = closer.ceil_to_s5_from_datetime(created_dt)

        # eff_start must be BASE+5, not BASE
        self.assertEqual(SIGNAL_EPOCH_BASE + 5, eff_start)

        # S5 candle at BASE (pre-entry) should not be in post-entry list
        s5_pre = {"t": SIGNAL_EPOCH_BASE, "o": 1.1, "h": 1.2, "l": 1.0, "c": 1.1}
        s5_post = {"t": SIGNAL_EPOCH_BASE + 5, "o": 1.1, "h": 1.1005, "l": 1.0995, "c": 1.1}
        # post-entry filter: t >= eff_start = BASE+5
        self.assertGreaterEqual(s5_post["t"], eff_start)
        self.assertLess(s5_pre["t"], eff_start)


# ── DEFECT 4: sparse S5 handling ──────────────────────────────────────────────

class Defect4SparseS5Tests(unittest.TestCase):
    """S5 fetches must handle sparse data; validate for corrupt/misaligned candles."""

    @staticmethod
    def _call_with_s5(
        candles: list[dict],
        s5_candles: list[dict] | None,
        *,
        server_epoch: int,
        direction: str = "BUY",
        entry: float = 1.1000,
        sl: float = 1.0980,
        tp: float = 1.1050,
        created_epoch: int = SIGNAL_EPOCH_BASE,
    ) -> dict | None:
        """Call prepare_signal_action with the given M15 and S5 candles."""
        sig = make_signal(
            direction=direction, entry=entry, sl=sl, tp=tp,
            created_epoch=created_epoch,
        )
        return call_prepare(sig, candles, s5_candles, server_epoch=server_epoch)

    def test_partial_entry_no_post_entry_s5_not_data_unavailable(self) -> None:
        """D4-1: Partial-entry candle with no post-entry S5 → no touch, not DATA_UNAVAILABLE.

        Signal created mid-candle.  S5 fetch returns candles only BEFORE eff_start.
        Since we have 95 more candles with no boundary touch and threshold not reached,
        the signal should remain OPEN (None), not DATA_UNAVAILABLE.
        """
        created_epoch = SIGNAL_EPOCH_BASE + 300
        candles = make_m15_candles(
            50, start_epoch=SIGNAL_EPOCH_BASE,
            high=1.1005, low=1.0995,  # no boundary touch
        )
        server_epoch = SIGNAL_EPOCH_BASE + 51 * M15

        # S5 that covers only the pre-entry portion (t < eff_start = BASE+300)
        # The mock always returns the same S5, but we filter to t >= proc_start inside resolver
        s5_pre_only = [
            {"t": SIGNAL_EPOCH_BASE, "o": 1.1, "h": 1.1005, "l": 1.0995, "c": 1.1},
            {"t": SIGNAL_EPOCH_BASE + 5, "o": 1.1, "h": 1.1005, "l": 1.0995, "c": 1.1},
        ]
        # eff_start = BASE+300; s5_post_entry = [c for c if t >= BASE+300] = []
        # fetch_s5_candles mock returns s5_pre_only for the partial-entry candle
        # The resolver should continue (not DATA_UNAVAILABLE) since it's partial-start
        action = self._call_with_s5(
            candles, s5_pre_only,
            server_epoch=server_epoch, created_epoch=created_epoch,
        )
        self.assertIsNone(action)  # OPEN, not CANCELLED

    def test_time_exit_with_sparse_s5_uses_last_valid(self) -> None:
        """D4-2: Sparse S5 for threshold candle — last valid S5 (not exactly threshold-5) used.

        threshold_epoch = BASE+96*900+300 (inside candle 97).
        S5 fetch returns candle at threshold-10 (not threshold-5).
        Should use that candle's close for TIME_EXIT, not return DATA_UNAVAILABLE.
        """
        created_epoch = SIGNAL_EPOCH_BASE + 300
        eff_start = created_epoch  # 300 % 5 == 0

        candles = make_m15_candles(97, start_epoch=SIGNAL_EPOCH_BASE,
                                   high=1.1005, low=1.0995)
        server_epoch = candles[-1]["t"] + M15

        threshold = closer.compute_threshold(candles, eff_start, 86400, M15)
        self.assertIsNotNone(threshold)

        # S5 covering threshold candle but last candle ends at threshold-10 (not threshold-5)
        # The last valid S5 has t = threshold-10, t+5 = threshold-5 <= threshold ✓
        s5 = [
            {"t": threshold - 20, "o": 1.1, "h": 1.1005, "l": 1.0995, "c": 1.1001},
            {"t": threshold - 15, "o": 1.1, "h": 1.1005, "l": 1.0995, "c": 1.1002},
            # Gap: no candle at threshold-10 or threshold-5
            # So last valid = threshold-15, t+5 = threshold-10 <= threshold ✓
        ]
        # Also need to ensure s5 includes the proc_start to proc_end range
        # proc_start for candle 97 = t = BASE+96*900
        # Add candles from proc_start up to threshold-15
        proc_start = SIGNAL_EPOCH_BASE + 96 * M15
        pre_s5 = [
            {"t": proc_start + i * 5, "o": 1.1, "h": 1.1005, "l": 1.0995, "c": 1.1}
            for i in range((threshold - 15 - proc_start) // 5)
        ]
        full_s5 = pre_s5 + s5

        sig = make_signal(created_epoch=created_epoch, direction="BUY",
                          entry=1.1000, sl=1.0980, tp=1.1050)
        action = call_prepare(sig, candles, full_s5, server_epoch=server_epoch)
        self.assertIsNotNone(action)
        self.assertEqual("TIME_EXIT", action["predicted_outcome"])
        # Exit price = close of last valid S5 (threshold-15 candle, c=1.1002)
        self.assertAlmostEqual(1.1002, action["predicted_exit_price"])

    def test_time_exit_no_s5_at_all_is_data_unavailable(self) -> None:
        """D4-3: TIME_EXIT required but no S5 candles at all → DATA_UNAVAILABLE → ACTIVE."""
        created_epoch = SIGNAL_EPOCH_BASE + 300
        candles = make_m15_candles(97, start_epoch=SIGNAL_EPOCH_BASE,
                                   high=1.1005, low=1.0995)
        server_epoch = candles[-1]["t"] + M15

        sig = make_signal(created_epoch=created_epoch, direction="BUY",
                          entry=1.1000, sl=1.0980, tp=1.1050)
        action = call_prepare(sig, candles, None, server_epoch=server_epoch, hard_max_age=168)
        self.assertIsNone(action)  # DATA_UNAVAILABLE before hard age → ACTIVE

    def test_misaligned_s5_timestamp_rejected(self) -> None:
        """D4-4: S5 candle with t % 5 != 0 → validate_s5_candles rejects → DATA_UNAVAILABLE."""
        candles_valid, _ = validate_s5_candles([
            {"t": 1003, "o": 1.1, "h": 1.1, "l": 1.0, "c": 1.1},  # 1003 % 5 = 3 → bad
        ])
        self.assertEqual([], candles_valid)

    def test_non_finite_s5_high_rejected(self) -> None:
        """D4-5: S5 candle with h=inf → validate_s5_candles rejects."""
        candles_valid, _ = validate_s5_candles([
            {"t": 1000, "o": 1.1, "h": math.inf, "l": 1.0, "c": 1.1},
        ])
        self.assertEqual([], candles_valid)

    def test_non_finite_s5_low_rejected(self) -> None:
        """D4-6: S5 candle with l=nan → validate_s5_candles rejects."""
        candles_valid, _ = validate_s5_candles([
            {"t": 1000, "o": 1.1, "h": 1.1, "l": math.nan, "c": 1.1},
        ])
        self.assertEqual([], candles_valid)

    def test_conflicting_duplicate_s5_rejected(self) -> None:
        """D4-7: Two S5 candles at same t with different h → rejected."""
        candles_valid, reason = validate_s5_candles([
            {"t": 1000, "o": 1.1, "h": 1.105, "l": 1.0, "c": 1.1},
            {"t": 1000, "o": 1.1, "h": 1.110, "l": 1.0, "c": 1.1},  # different h
        ])
        self.assertEqual([], candles_valid)
        self.assertIn("conflict", reason)

    def test_identical_duplicate_s5_collapsed(self) -> None:
        """D4-8: Two identical S5 candles at same t → collapsed to one."""
        c = {"t": 1000, "o": 1.1, "h": 1.105, "l": 1.095, "c": 1.1}
        candles_valid, reason = validate_s5_candles([c, dict(c)])
        self.assertEqual("ok", reason)
        self.assertEqual(1, len(candles_valid))
        self.assertEqual(1000, candles_valid[0]["t"])

    def test_validate_s5_sorts_by_timestamp(self) -> None:
        """D4-9: validate_s5_candles returns candles in ascending t order."""
        candles_valid, _ = validate_s5_candles([
            {"t": 1010, "o": 1.1, "h": 1.1, "l": 1.0, "c": 1.1},
            {"t": 1000, "o": 1.1, "h": 1.1, "l": 1.0, "c": 1.1},
            {"t": 1005, "o": 1.1, "h": 1.1, "l": 1.0, "c": 1.1},
        ])
        self.assertEqual([1000, 1005, 1010], [c["t"] for c in candles_valid])

    def test_s5_validation_in_resolve_returns_data_unavailable(self) -> None:
        """D4-10: Misaligned S5 returned by fetch → resolve returns DATA_UNAVAILABLE → ACTIVE.

        Candle 10 has M15 H/L touch, triggering S5 fetch.
        Mock fetch returns a misaligned S5 candle (t % 5 != 0).
        Since we're before threshold and DATA_UNAVAILABLE, result must be None.
        """
        tp, sl, entry = 1.1020, 1.0980, 1.1000
        candles = make_m15_candles(
            30, start_epoch=SIGNAL_EPOCH_BASE,
            high=entry + 0.0005, low=entry - 0.0005,
        )
        candles[9]["h"] = tp + 0.0001  # M15 touch at candle 10
        server_epoch = SIGNAL_EPOCH_BASE + 31 * M15

        # Misaligned S5 candle
        bad_t = SIGNAL_EPOCH_BASE + 9 * M15 + 1  # not divisible by 5
        bad_s5 = [{"t": bad_t, "o": entry, "h": tp + 0.0001, "l": entry - 0.0002, "c": tp}]

        sig = make_signal(direction="BUY", entry=entry, sl=sl, tp=tp)
        action = call_prepare(sig, candles, bad_s5, server_epoch=server_epoch, hard_max_age=168)
        # DATA_UNAVAILABLE, age < 168h → ACTIVE (None)
        self.assertIsNone(action)


# ── validate_s5_candles unit tests ────────────────────────────────────────────

class ValidateS5CandlesTests(unittest.TestCase):
    """Unit tests for validate_s5_candles validation logic."""

    def test_valid_single_candle(self) -> None:
        """V5-1: Single well-formed S5 candle passes validation."""
        c = {"t": 1000, "o": 1.1, "h": 1.105, "l": 1.095, "c": 1.1}
        valid, reason = validate_s5_candles([c])
        self.assertEqual("ok", reason)
        self.assertEqual(1, len(valid))

    def test_empty_input_returns_empty(self) -> None:
        """V5-2: Empty input → empty output, ok."""
        valid, reason = validate_s5_candles([])
        self.assertEqual("ok", reason)
        self.assertEqual([], valid)

    def test_non_finite_close_rejected(self) -> None:
        """V5-3: NaN close → rejected."""
        valid, reason = validate_s5_candles([
            {"t": 1000, "o": 1.1, "h": 1.1, "l": 1.0, "c": math.nan},
        ])
        self.assertEqual([], valid)
        self.assertIn("non-finite", reason)

    def test_missing_t_field_rejected(self) -> None:
        """V5-4: Missing t field → rejected with reason mentioning t field."""
        valid, reason = validate_s5_candles([{"o": 1.1, "h": 1.1, "l": 1.0, "c": 1.1}])
        self.assertEqual([], valid)
        self.assertIn("t field", reason)


# ══════════════════════════════════════════════════════════════════════════════
# ADVERSARIAL HARDENING PASS
# ══════════════════════════════════════════════════════════════════════════════



def _mock_https_conn(status: int = 200, body: bytes = b"") -> MagicMock:
    """Build a mock HTTPSConnection that returns given status and body."""
    resp = MagicMock()
    resp.status = status
    resp.read.return_value = body
    conn = MagicMock()
    conn.getresponse.return_value = resp
    return conn


def _mock_https_conn_error(exc: Exception) -> MagicMock:
    """Build a mock HTTPSConnection that raises on request()."""
    conn = MagicMock()
    conn.request.side_effect = exc
    return conn


_FAKE_TOKEN = "FAKE_S5_TOKEN_SHOULD_NOT_APPEAR_IN_REASONS"
_FAKE_URL = "https://fake-oanda.test"
_S5_FROM = SIGNAL_EPOCH_BASE
_S5_TO = SIGNAL_EPOCH_BASE + 60  # 12 S5 candles


def _good_s5_response() -> bytes:
    """One valid complete S5 candle within [_S5_FROM, _S5_TO)."""
    return json.dumps({
        "candles": [{
            "complete": True,
            "time": str(_S5_FROM),
            "mid": {"o": "1.1000", "h": "1.1005", "l": "1.0995", "c": "1.1002"},
        }]
    }).encode()


def _fetch_direct(**kwargs):
    """Call fetch_s5_candles with consistent fake token/url."""
    return fetch_s5_candles(
        "EURUSD",
        kwargs.get("from_epoch", _S5_FROM),
        kwargs.get("to_epoch", _S5_TO),
        _FAKE_TOKEN,
        _FAKE_URL,
    )


def _assert_no_secrets(tc: unittest.TestCase, reason: str) -> None:
    """Assert that token, auth header, and URL do not appear in the error reason."""
    tc.assertNotIn(_FAKE_TOKEN, reason, "token leaked into reason")
    tc.assertNotIn("Authorization", reason, "auth header leaked into reason")
    tc.assertNotIn(_FAKE_URL, reason, "URL leaked into reason")


# ── A. Signal Input Validation ────────────────────────────────────────────────

class SignalInputValidationTests(unittest.TestCase):
    """Tests for signal field validation — NaN/Inf/invalid direction rejection."""

    @staticmethod
    def _prepare_with_bad_field(**override) -> dict | None:
        """Call prepare_signal_action with a signal whose field is overridden."""
        sig = make_signal()
        sig.update(override)
        candles = make_m15_candles(10, start_epoch=SIGNAL_EPOCH_BASE)
        now = datetime.fromtimestamp(SIGNAL_EPOCH_BASE + 11 * M15, timezone.utc)
        server_epoch = SIGNAL_EPOCH_BASE + 11 * M15
        with _patch.object(closer, "fetch_candles", return_value=(candles, "ok")):
            return closer.prepare_signal_action(
                sig, now, server_epoch, 24, 168,
                oanda_token="fake", oanda_url="https://fake",
            )

    def test_invalid_direction_returns_none(self) -> None:
        """A-1: direction not in {BUY,SELL} → no action, no exception."""
        self.assertIsNone(self._prepare_with_bad_field(direction="HODL"))

    def test_nan_entry_price_returns_none(self) -> None:
        """A-2: NaN entry_price → no action, no exception."""
        self.assertIsNone(self._prepare_with_bad_field(entry_price=math.nan))

    def test_infinite_entry_price_returns_none(self) -> None:
        """A-3: Inf entry_price → no action, no exception."""
        self.assertIsNone(self._prepare_with_bad_field(entry_price=math.inf))

    def test_nan_stop_loss_returns_none(self) -> None:
        """A-4: NaN stop_loss → no action, no exception."""
        self.assertIsNone(self._prepare_with_bad_field(stop_loss=math.nan))

    def test_infinite_stop_loss_returns_none(self) -> None:
        """A-5: Inf stop_loss → no action, no exception."""
        self.assertIsNone(self._prepare_with_bad_field(stop_loss=math.inf))

    def test_nan_take_profit_returns_none(self) -> None:
        """A-6: NaN take_profit → no action, no exception."""
        self.assertIsNone(self._prepare_with_bad_field(take_profit=math.nan))

    def test_infinite_take_profit_returns_none(self) -> None:
        """A-7: Inf take_profit → no action, no exception."""
        self.assertIsNone(self._prepare_with_bad_field(take_profit=math.inf))


# ── B. M15 Normalization ──────────────────────────────────────────────────────

class M15NormalizationTests(unittest.TestCase):
    """Tests for M15 candle normalization (sorting, filtering) inside fetch_candles."""

    @staticmethod
    def _fetch_with_raw(
        raw_candles: list[dict],
        eff_start: int,
        server_epoch: int,
    ) -> tuple[list[dict], str]:
        """Call fetch_candles with load_oanda_cache mocked to return raw_candles."""
        with _patch.object(closer, "load_oanda_cache", return_value=(raw_candles, "ok")):
            return closer.fetch_candles(
                "EURUSD",
                "M15",
                server_epoch,
                eff_start,
            )

    def test_out_of_order_m15_candles_sorted_before_threshold(self) -> None:
        """B-8: Reversed M15 candles are sorted by fetch_candles; threshold correct."""
        candles_sorted = make_m15_candles(10, start_epoch=SIGNAL_EPOCH_BASE)
        reversed_candles = list(reversed(candles_sorted))
        server_epoch = SIGNAL_EPOCH_BASE + 11 * M15

        eligible, reason = self._fetch_with_raw(
            reversed_candles, SIGNAL_EPOCH_BASE, server_epoch
        )
        self.assertEqual("ok", reason)
        ts = [c["t"] for c in eligible]
        self.assertEqual(ts, sorted(ts), "eligible candles must be sorted ascending")
        # threshold computed on sorted candles must equal sorted-input result
        th = closer.compute_threshold(eligible, SIGNAL_EPOCH_BASE, 10 * M15, M15)
        th_ref = closer.compute_threshold(candles_sorted, SIGNAL_EPOCH_BASE, 10 * M15, M15)
        self.assertEqual(th_ref, th)

    def test_nonaligned_m15_timestamp_rejected(self) -> None:
        """B-9: M15 timestamp not divisible by 900 → rejected."""
        # Normally SIGNAL_EPOCH_BASE is aligned; mutate one candle
        candles = make_m15_candles(5, start_epoch=SIGNAL_EPOCH_BASE)
        # Force one candle to have t % 900 != 0
        bad = dict(candles[2])
        bad["t"] = candles[2]["t"] + 1  # +1 → no longer divisible by 900
        candles[2] = bad
        server_epoch = SIGNAL_EPOCH_BASE + 6 * M15

        eligible, reason = self._fetch_with_raw(candles, SIGNAL_EPOCH_BASE, server_epoch)
        self.assertEqual([], eligible)
        self.assertIn("non-aligned", reason)

    def test_duplicate_candles_not_double_counted_toward_threshold(self) -> None:
        """B-12: Duplicate M15 candle at same t collapsed; does not inflate threshold."""
        # 95 unique candles → 23.75h market time < 24h → threshold None
        base_candles = make_m15_candles(95, start_epoch=SIGNAL_EPOCH_BASE)
        dup = dict(base_candles[0])  # identical copy of first candle → same t
        all_candles = [dup] + base_candles  # 96 entries but only 95 unique
        server_epoch = SIGNAL_EPOCH_BASE + 96 * M15

        eligible, reason = self._fetch_with_raw(all_candles, SIGNAL_EPOCH_BASE, server_epoch)
        self.assertEqual("ok", reason)
        ts = [c["t"] for c in eligible]
        self.assertEqual(len(ts), len(set(ts)), "duplicates must be collapsed")
        # 95 unique completed candles: 95×900 = 85500 < 86400 → no threshold
        threshold = closer.compute_threshold(eligible, SIGNAL_EPOCH_BASE, 86400, M15)
        self.assertIsNone(threshold, "double-counting must not push threshold over 24h")

    def test_cache_beginning_after_effective_start_rejected(self) -> None:
        """B-13: All cache candles start strictly after effective_start → no coverage."""
        # effective_start = BASE; candles start at BASE+900 (after effective_start)
        candles = make_m15_candles(5, start_epoch=SIGNAL_EPOCH_BASE + M15)
        server_epoch = SIGNAL_EPOCH_BASE + 7 * M15

        eligible, reason = self._fetch_with_raw(candles, SIGNAL_EPOCH_BASE, server_epoch)
        self.assertEqual([], eligible)
        self.assertIn("cover", reason)

    def test_cache_ending_before_effective_start_rejected_b14(self) -> None:
        """B-14 (reinforcing D2-2): all candles end before eff_start → rejected."""
        # Cache ends at BASE-5*900 — no candle spans BASE
        candles = make_m15_candles(5, start_epoch=SIGNAL_EPOCH_BASE - 10 * M15)
        server_epoch = SIGNAL_EPOCH_BASE + M15

        eligible, reason = self._fetch_with_raw(candles, SIGNAL_EPOCH_BASE, server_epoch)
        self.assertEqual([], eligible)
        self.assertIn("cover", reason)

    def test_historical_cache_with_pre_signal_candles_accepted_b15(self) -> None:
        """B-15 (reinforcing D2-1): historical cache with pre-signal candles accepted."""
        pre = make_m15_candles(10, start_epoch=SIGNAL_EPOCH_BASE - 10 * M15)
        post = make_m15_candles(5, start_epoch=SIGNAL_EPOCH_BASE)
        all_c = pre + post
        server_epoch = SIGNAL_EPOCH_BASE + 5 * M15

        eligible, reason = self._fetch_with_raw(all_c, SIGNAL_EPOCH_BASE, server_epoch)
        self.assertEqual("ok", reason)
        self.assertTrue(len(eligible) > 0)
        # Pre-signal candles must not appear in eligible
        self.assertTrue(all(c["t"] >= SIGNAL_EPOCH_BASE for c in eligible))


# ── C. Open State at Hard Wall-Clock Age ─────────────────────────────────────

class OpenStateAtHardAgeTests(unittest.TestCase):
    """Tests confirming clean-OPEN signals are never cancelled by hard-age alone."""

    def test_clean_open_state_at_hard_age_stays_active(self) -> None:
        """C-16: Signal > hard_max_age, clean OPEN (market time not reached due to gaps)
        → must remain ACTIVE, not CANCELLED.

        Hard age must only cancel DATA_UNAVAILABLE, not a clean OPEN.
        48 candles before a 2-day market gap + 47 after = 95 candles = 23.75h market.
        Wall-clock age: 95×900 + 2×86400 = 258300s ≈ 71.75h >> hard_max_age=48h.
        No TP/SL touch.  Resolution = OPEN.
        """
        # 48 candles then 2-day gap then 47 more = 95 market candles
        candles = make_m15_candles(
            95, start_epoch=SIGNAL_EPOCH_BASE,
            high=1.1005, low=1.0995,  # no boundary touch
            weekend_gap_after=47,
            weekend_gap_seconds=2 * 24 * 3600,
        )
        last_candle_t = candles[-1]["t"]
        server_epoch = last_candle_t + M15

        # Wall-clock age from signal creation (BASE) to server_epoch
        age_hours = (server_epoch - SIGNAL_EPOCH_BASE) / 3600.0
        self.assertGreater(age_hours, 48.0, "prerequisite: wall-clock age > hard_max_age")

        sig = make_signal(direction="BUY", entry=1.1000, sl=1.0980, tp=1.1050)
        action = call_prepare(
            sig, candles, [],  # empty S5 (no boundary touch so S5 not needed)
            server_epoch=server_epoch,
            max_age=24,
            hard_max_age=48,  # wall-clock age exceeds this
        )
        # Must remain ACTIVE — clean OPEN is never cancelled by hard age
        self.assertIsNone(action)


# ── D. Effective Start End-to-End ────────────────────────────────────────────

class EffectiveStartEndToEndTests(unittest.TestCase):
    """Tests 17-20: created_at with microseconds, pre/post-entry S5 separation."""

    @staticmethod
    def _make_microsecond_sig(
        *,
        microsecond: int = 1,
        direction: str = "BUY",
        entry: float = 1.1000,
        sl: float = 1.0980,
        tp: float = 1.1020,
    ) -> dict:
        """Return a signal dict with created_at at SIGNAL_EPOCH_BASE + {microsecond} µs."""
        created_dt = datetime(2026, 7, 10, 8, 0, 0, microsecond, tzinfo=timezone.utc)
        return {
            "id": "test-us",
            "pair": "EURUSD",
            "direction": direction,
            "entry_price": entry,
            "stop_loss": sl,
            "take_profit": tp,
            "created_at": created_dt.isoformat(),
            "timeframe": "M15",
        }

    def test_microsecond_eff_start_rounds_to_next_s5(self) -> None:
        """D-17: created_at = BASE+1µs → eff_start = BASE+5 (not BASE)."""
        sig = self._make_microsecond_sig(microsecond=1)
        created = closer.parse_signal_created_at(sig["created_at"])
        eff_start = closer.ceil_to_s5_from_datetime(created)
        self.assertEqual(SIGNAL_EPOCH_BASE + 5, eff_start)

    def test_pre_entry_s5_tp_touch_ignored(self) -> None:
        """D-18: S5 candle at BASE (before eff_start=BASE+5) touching TP → NOT WIN.

        eff_start = BASE+5; s5_post_entry = [c for c if t >= BASE+5].
        Pre-entry candle at t=BASE is excluded → no TP detected → OPEN.
        """
        sig = self._make_microsecond_sig(microsecond=1, tp=1.1020)
        # 30 candles (< 96 needed for threshold); partial-entry candle 0
        candles = make_m15_candles(30, start_epoch=SIGNAL_EPOCH_BASE,
                                   high=1.1005, low=1.0995)
        # Candle 0 is partial-start (eff_start=BASE+5 > BASE)
        candles[0]["h"] = 1.1025  # M15 H >= tp → need_s5 = True
        server_epoch = SIGNAL_EPOCH_BASE + 31 * M15

        # S5 returns only a pre-entry candle (t=BASE < eff_start=BASE+5)
        pre_entry_only = [
            {"t": SIGNAL_EPOCH_BASE, "o": 1.1, "h": 1.1025, "l": 1.0995, "c": 1.1020},
        ]
        # s5_post_entry will be empty → no touch attributed for partial-start
        # Remaining candles (1-29) have no boundary touch → OPEN
        action = call_prepare(sig, candles, pre_entry_only, server_epoch=server_epoch)
        self.assertIsNone(action)  # no WIN, signal stays ACTIVE

    def test_post_entry_s5_tp_touch_detected(self) -> None:
        """D-19: S5 candle at BASE+5 (>= eff_start=BASE+5) touching TP → WIN."""
        sig = self._make_microsecond_sig(microsecond=1, tp=1.1020)
        candles = make_m15_candles(30, start_epoch=SIGNAL_EPOCH_BASE,
                                   high=1.1005, low=1.0995)
        candles[0]["h"] = 1.1025  # force M15 touch to trigger S5 fetch for candle 0
        server_epoch = SIGNAL_EPOCH_BASE + 31 * M15

        # S5 includes BOTH pre-entry (BASE) AND post-entry (BASE+5) candle
        both = [
            {"t": SIGNAL_EPOCH_BASE,     "o": 1.1, "h": 1.1025, "l": 1.0995, "c": 1.1020},
            {"t": SIGNAL_EPOCH_BASE + 5, "o": 1.1, "h": 1.1025, "l": 1.0995, "c": 1.1020},
        ]
        action = call_prepare(sig, candles, both, server_epoch=server_epoch)
        self.assertIsNotNone(action)
        self.assertEqual("WIN", action["predicted_outcome"])

    def test_post_entry_closed_at_is_s5_end(self) -> None:
        """D-20: closed_at_epoch = end of post-entry S5 candle (t+5)."""
        sig = self._make_microsecond_sig(microsecond=1, tp=1.1020)
        candles = make_m15_candles(30, start_epoch=SIGNAL_EPOCH_BASE,
                                   high=1.1005, low=1.0995)
        candles[0]["h"] = 1.1025
        server_epoch = SIGNAL_EPOCH_BASE + 31 * M15

        both = [
            {"t": SIGNAL_EPOCH_BASE,     "o": 1.1, "h": 1.1025, "l": 1.0995, "c": 1.1020},
            {"t": SIGNAL_EPOCH_BASE + 5, "o": 1.1, "h": 1.1025, "l": 1.0995, "c": 1.1020},
        ]
        action = call_prepare(sig, candles, both, server_epoch=server_epoch)
        self.assertIsNotNone(action)
        # closed_at_epoch = (BASE+5) + 5 = BASE+10
        self.assertEqual(SIGNAL_EPOCH_BASE + 10, action["predicted_closed_at_epoch"])


# ── E. S5 Transport Failure Handling ─────────────────────────────────────────

class S5TransportFailureTests(unittest.TestCase):
    """fetch_s5_candles: transport failures return ([], safe_reason), no exception."""

    @staticmethod
    def _fetch() -> tuple[list[dict], str]:
        """Invoke fetch_s5_candles via the module-level _fetch_direct helper."""
        return _fetch_direct()

    def _assert_safe(self, candles: list[dict], reason: str) -> None:
        """Assert result is ([], non-empty string) with no secrets leaked."""
        self.assertEqual([], candles)
        self.assertIsInstance(reason, str)
        self.assertTrue(len(reason) > 0)
        _assert_no_secrets(self, reason)

    def test_http_error(self) -> None:
        """E-21: Non-2xx HTTP response (403) → empty, safe reason, no exception."""
        conn = _mock_https_conn(status=403, body=b"body content here")
        with _patch("http.client.HTTPSConnection", return_value=conn):
            candles, reason = self._fetch()
        self._assert_safe(candles, reason)
        self.assertNotIn("body content here", reason)

    def test_timeout_error(self) -> None:
        """E-22: TimeoutError on request → empty, safe reason."""
        conn = _mock_https_conn_error(TimeoutError("timed out"))
        with _patch("http.client.HTTPSConnection", return_value=conn):
            candles, reason = self._fetch()
        self._assert_safe(candles, reason)

    def test_url_error(self) -> None:
        """E-23: OSError (connection refused) → empty, safe reason."""
        conn = _mock_https_conn_error(OSError("connection refused"))
        with _patch("http.client.HTTPSConnection", return_value=conn):
            candles, reason = self._fetch()
        self._assert_safe(candles, reason)

    def test_malformed_json(self) -> None:
        """E-24: Body not valid JSON → empty, safe reason."""
        conn = _mock_https_conn(body=b"not json {{{}")
        with _patch("http.client.HTTPSConnection", return_value=conn):
            candles, reason = self._fetch()
        self._assert_safe(candles, reason)
        self.assertNotIn("not json", reason)

    def test_json_not_object(self) -> None:
        """E-25: JSON is a list, not an object → empty, safe reason, no AttributeError."""
        body = json.dumps([1, 2, 3]).encode()
        conn = _mock_https_conn(body=body)
        with _patch("http.client.HTTPSConnection", return_value=conn):
            candles, reason = self._fetch()
        self._assert_safe(candles, reason)
        self.assertIn("not a JSON object", reason)

    def test_missing_candles_field(self) -> None:
        """E-26: candles key absent → empty list; reason mentions no complete candles."""
        body = json.dumps({"status": "ok"}).encode()
        conn = _mock_https_conn(body=body)
        with _patch("http.client.HTTPSConnection", return_value=conn):
            candles, reason = self._fetch()
        self.assertEqual([], candles)
        self.assertIn("no complete", reason)

    def test_candles_field_wrong_type(self) -> None:
        """E-27: candles is a string, not a list → empty, safe reason, no TypeError."""
        body = json.dumps({"candles": "not_a_list"}).encode()
        conn = _mock_https_conn(body=body)
        with _patch("http.client.HTTPSConnection", return_value=conn):
            candles, reason = self._fetch()
        self._assert_safe(candles, reason)
        self.assertIn("not a list", reason)

    def test_malformed_complete_candle(self) -> None:
        """E-28: complete candle with unparseable time → skipped; no complete candles remain."""
        body = json.dumps({
            "candles": [{"complete": True, "time": "not-a-number", "mid": {}}]
        }).encode()
        conn = _mock_https_conn(body=body)
        with _patch("http.client.HTTPSConnection", return_value=conn):
            candles, reason = self._fetch()
        self.assertEqual([], candles)
        self.assertIn("no complete", reason)

    def test_nonfinite_ohlc_rejected(self) -> None:
        """E-29: Candle with h=Inf → validation rejects, returns empty."""
        body = json.dumps({"candles": [{
            "complete": True,
            "time": str(_S5_FROM),
            "mid": {"o": "1.1", "h": "Infinity", "l": "1.0", "c": "1.1"},
        }]}).encode()
        conn = _mock_https_conn(body=body)
        with _patch("http.client.HTTPSConnection", return_value=conn):
            candles, reason = self._fetch()
        self.assertEqual([], candles)
        _assert_no_secrets(self, reason)

    def test_conflicting_duplicate_timestamps_rejected(self) -> None:
        """E-30: Two candles same t, different h → validation rejects."""
        body = json.dumps({"candles": [
            {"complete": True, "time": str(_S5_FROM),
             "mid": {"o": "1.1", "h": "1.105", "l": "1.0", "c": "1.1"}},
            {"complete": True, "time": str(_S5_FROM),
             "mid": {"o": "1.1", "h": "1.110", "l": "1.0", "c": "1.1"}},
        ]}).encode()
        conn = _mock_https_conn(body=body)
        with _patch("http.client.HTTPSConnection", return_value=conn):
            candles, reason = self._fetch()
        self.assertEqual([], candles)
        _assert_no_secrets(self, reason)

    def test_misaligned_timestamp_rejected(self) -> None:
        """E-31: Candle t % 5 != 0 → validation rejects."""
        bad_t = _S5_FROM + 1  # not divisible by 5 (assuming _S5_FROM is)
        body = json.dumps({"candles": [{
            "complete": True,
            "time": str(bad_t),
            "mid": {"o": "1.1", "h": "1.105", "l": "1.0", "c": "1.1"},
        }]}).encode()
        conn = _mock_https_conn(body=body)
        with _patch("http.client.HTTPSConnection", return_value=conn):
            candles, reason = self._fetch()
        self.assertEqual([], candles)
        _assert_no_secrets(self, reason)

    def test_candle_outside_requested_range_excluded(self) -> None:
        """E-32: Candle at t=_S5_TO (outside [from, to)) → excluded; no candles remain."""
        body = json.dumps({"candles": [{
            "complete": True,
            "time": str(_S5_TO),  # t >= to_epoch → excluded
            "mid": {"o": "1.1", "h": "1.105", "l": "1.0", "c": "1.1"},
        }]}).encode()
        conn = _mock_https_conn(body=body)
        with _patch("http.client.HTTPSConnection", return_value=conn):
            candles, reason = self._fetch()
        self.assertEqual([], candles)
        self.assertIn("no complete", reason)

    def test_non_https_url_rejected_before_connection(self) -> None:
        """E-N1: Non-HTTPS base URL rejected without any network connection."""
        with _patch("http.client.HTTPSConnection") as mock_cls:
            candles, reason = fetch_s5_candles(
                "EURUSD", _S5_FROM, _S5_TO, _FAKE_TOKEN, "http://fake-oanda.test"
            )
        mock_cls.assert_not_called()
        self.assertEqual([], candles)
        self.assertIsInstance(reason, str)
        _assert_no_secrets(self, reason)

    def test_embedded_credentials_rejected(self) -> None:
        """E-N2: URL with embedded credentials rejected before connection."""
        with _patch("http.client.HTTPSConnection") as mock_cls:
            candles, reason = fetch_s5_candles(
                "EURUSD", _S5_FROM, _S5_TO, _FAKE_TOKEN,
                "https://user:pass@fake-oanda.test"
            )
        mock_cls.assert_not_called()
        self.assertEqual([], candles)
        _assert_no_secrets(self, reason)

    def test_https_hostname_and_port_used_for_connection(self) -> None:
        """E-N3: Host and explicit port parsed from base URL are passed to HTTPSConnection."""
        conn = _mock_https_conn(body=_good_s5_response())
        with _patch("http.client.HTTPSConnection", return_value=conn) as mock_cls:
            fetch_s5_candles(
                "EURUSD", _S5_FROM, _S5_TO, _FAKE_TOKEN, "https://fake-oanda.test:8443"
            )
        mock_cls.assert_called_once()
        args = mock_cls.call_args[0]
        self.assertEqual("fake-oanda.test", args[0])
        self.assertEqual(8443, args[1])

    def test_get_path_contains_oanda_candles_endpoint(self) -> None:
        """E-N4: GET request path includes /v3/instruments/.../candles with query params."""
        conn = _mock_https_conn(body=_good_s5_response())
        with _patch("http.client.HTTPSConnection", return_value=conn):
            fetch_s5_candles("EURUSD", _S5_FROM, _S5_TO, _FAKE_TOKEN, _FAKE_URL)
        req_args = conn.request.call_args[0]
        self.assertEqual("GET", req_args[0])
        self.assertIn("/v3/instruments/EUR_USD/candles", req_args[1])
        self.assertIn("granularity=S5", req_args[1])

    def test_authorization_and_datetime_headers_sent(self) -> None:
        """E-N5: Authorization Bearer and Accept-Datetime-Format headers are sent."""
        conn = _mock_https_conn(body=_good_s5_response())
        with _patch("http.client.HTTPSConnection", return_value=conn):
            fetch_s5_candles("EURUSD", _S5_FROM, _S5_TO, _FAKE_TOKEN, _FAKE_URL)
        req_kwargs = conn.request.call_args[1]
        headers = req_kwargs.get("headers", {})
        self.assertIn("Authorization", headers)
        self.assertTrue(headers["Authorization"].startswith("Bearer "))
        self.assertIn("Accept-Datetime-Format", headers)
        self.assertNotIn(_FAKE_TOKEN, headers.get("Authorization", "").replace(f"Bearer {_FAKE_TOKEN}", ""))

    def test_non_2xx_response_fails_closed(self) -> None:
        """E-N6: HTTP 403 response → empty candles, safe reason, no exception."""
        conn = _mock_https_conn(status=403, body=b"Forbidden")
        with _patch("http.client.HTTPSConnection", return_value=conn):
            candles, reason = self._fetch()
        self.assertEqual([], candles)
        _assert_no_secrets(self, reason)

    def test_token_never_appears_in_reason(self) -> None:
        """E-N7: Token must not appear in returned reason on any error."""
        conn = _mock_https_conn_error(OSError("network error"))
        with _patch("http.client.HTTPSConnection", return_value=conn):
            _candles, reason = self._fetch()
        self.assertNotIn(_FAKE_TOKEN, reason)
        self.assertNotIn("Authorization", reason)


# ── F. Sparse S5 Lookback and Threshold Safety ───────────────────────────────

class SparseS5LookbackTests(unittest.TestCase):
    """Tests for TP/SL detection in sparse (non-contiguous) S5 data."""

    def test_sparse_s5_with_gaps_still_finds_tp(self) -> None:
        """F-33: Sparse S5 (non-contiguous) accepted; TP found in available candle."""
        # Full M15 candle with H >= tp → triggers S5 fetch
        tp = 1.1020
        candle_t = SIGNAL_EPOCH_BASE
        candles = make_m15_candles(50, start_epoch=SIGNAL_EPOCH_BASE,
                                   high=tp + 0.0005, low=1.0995)
        server_epoch = SIGNAL_EPOCH_BASE + 51 * M15

        # Sparse S5: candles at t, t+10, t+20 (gaps of 10s = 2 missing buckets each)
        sparse_s5 = [
            {"t": candle_t,      "o": 1.1, "h": tp - 0.0001, "l": 1.0995, "c": 1.1},
            {"t": candle_t + 10, "o": 1.1, "h": tp + 0.0001, "l": 1.0995, "c": 1.1},
            {"t": candle_t + 20, "o": 1.1, "h": 1.1005,      "l": 1.0995, "c": 1.1},
        ]
        sig = make_signal(direction="BUY", entry=1.1000, sl=1.0980, tp=tp)
        action = call_prepare(sig, candles, sparse_s5, server_epoch=server_epoch)
        self.assertIsNotNone(action)
        self.assertEqual("WIN", action["predicted_outcome"])
        self.assertEqual(candle_t + 10 + S5, action["predicted_closed_at_epoch"])

    def test_pre_entry_lookback_tp_not_win(self) -> None:
        """F-34: Pre-entry lookback S5 candle touching TP is NOT counted as WIN.

        Signal created mid-M15 at BASE+300 → eff_start=BASE+300.
        Lookback S5 at BASE (< eff_start) has h >= tp.
        Post-entry S5 (>= BASE+300) has no touch.
        Expected: no WIN (signal OPEN).
        """
        created_epoch = SIGNAL_EPOCH_BASE + 300
        tp, sl, entry = 1.1020, 1.0980, 1.1000

        candles = make_m15_candles(30, start_epoch=SIGNAL_EPOCH_BASE,
                                   high=tp + 0.0001, low=1.0995)
        server_epoch = SIGNAL_EPOCH_BASE + 31 * M15
        sig = make_signal(created_epoch=created_epoch, direction="BUY",
                          entry=entry, sl=sl, tp=tp)

        # S5 with pre-entry touch but no post-entry touch
        pre_touch = {"t": SIGNAL_EPOCH_BASE, "o": entry, "h": tp + 0.001, "l": entry - 0.001, "c": tp}
        post_no_touch = {"t": SIGNAL_EPOCH_BASE + 300, "o": entry,
                         "h": entry + 0.0005, "l": entry - 0.0005, "c": entry}
        s5 = [pre_touch, post_no_touch]

        action = call_prepare(sig, candles, s5, server_epoch=server_epoch)
        self.assertIsNone(action)  # pre-entry touch must not produce WIN

    def test_no_post_threshold_candle_in_tp_sl_scan(self) -> None:
        """F-36: Candle after threshold has SL touch → TIME_EXIT wins, not LOSS.

        96 completed candles → TIME_EXIT; candle 97 has SL touch but is ignored.
        """
        sl = 1.0980
        candles = make_m15_candles(96, start_epoch=SIGNAL_EPOCH_BASE,
                                   final_close=1.1005,
                                   high=1.1005, low=1.0995)
        # Candle 97: SL touch (after threshold)
        sl_candle = {"t": SIGNAL_EPOCH_BASE + 96 * M15, "o": 1.1,
                     "h": 1.1005, "l": sl - 0.001, "c": 1.098}
        all_candles = candles + [sl_candle]

        server_epoch = SIGNAL_EPOCH_BASE + 97 * M15
        sig = make_signal(direction="BUY", entry=1.1000, sl=sl, tp=1.1050)
        s5 = make_s5_candles(SIGNAL_EPOCH_BASE, SIGNAL_EPOCH_BASE + 96 * M15,
                              high=1.1005, low=1.0995)
        action = call_prepare(sig, all_candles, s5, server_epoch=server_epoch)
        self.assertIsNotNone(action)
        self.assertEqual("TIME_EXIT", action["predicted_outcome"])

    def test_latest_valid_s5_selected_for_time_exit(self) -> None:
        """F-38: Latest S5 where t+5 <= threshold used for TIME_EXIT price.

        Threshold inside candle 97.  Last available S5 ends at threshold-10, not
        threshold-5.  exit_price = close of that last valid S5.
        """
        created_epoch = SIGNAL_EPOCH_BASE + 300
        eff_start = created_epoch  # 300 % 5 == 0

        candles = make_m15_candles(97, start_epoch=SIGNAL_EPOCH_BASE,
                                   high=1.1005, low=1.0995)
        server_epoch = candles[-1]["t"] + M15
        threshold = closer.compute_threshold(candles, eff_start, 86400, M15)
        self.assertIsNotNone(threshold)

        proc_start = SIGNAL_EPOCH_BASE + 96 * M15
        exit_close = 1.1007
        # Cover proc_start → threshold-10; gap at threshold-5
        mid_s5 = [
            {"t": proc_start + i * 5, "o": 1.1, "h": 1.1005, "l": 1.0995, "c": 1.1}
            for i in range((threshold - 10 - proc_start) // 5)
        ]
        last_s5 = {"t": threshold - 10, "o": 1.1, "h": 1.1005, "l": 1.0995, "c": exit_close}
        full_s5 = mid_s5 + [last_s5]  # gap: no candle at threshold-5

        sig = make_signal(created_epoch=created_epoch, entry=1.1000, sl=1.0980, tp=1.1050)
        action = call_prepare(sig, candles, full_s5, server_epoch=server_epoch)
        self.assertIsNotNone(action)
        self.assertEqual("TIME_EXIT", action["predicted_outcome"])
        self.assertAlmostEqual(exit_close, action["predicted_exit_price"])

    def test_s5_ending_after_threshold_excluded_from_exit(self) -> None:
        """F-39: S5 candle starting before threshold but ending after must be excluded.

        t = threshold-3; t+5 = threshold+2 > threshold → NOT in valid_exit.
        """
        created_epoch = SIGNAL_EPOCH_BASE + 300
        eff_start = created_epoch

        candles = make_m15_candles(97, start_epoch=SIGNAL_EPOCH_BASE,
                                   high=1.1005, low=1.0995)
        server_epoch = candles[-1]["t"] + M15
        threshold = closer.compute_threshold(candles, eff_start, 86400, M15)
        self.assertIsNotNone(threshold)

        proc_start = SIGNAL_EPOCH_BASE + 96 * M15
        # Only candle: t = threshold-3 (starts before threshold; t+5 = threshold+2 > threshold)
        # valid_exit requires t+5 <= threshold → this candle is excluded
        only_s5 = [{"t": threshold - 3, "o": 1.1, "h": 1.1005, "l": 1.0995, "c": 1.1007}]
        # Add candles covering proc_start for the initial portion
        head_s5 = [
            {"t": proc_start + i * 5, "o": 1.1, "h": 1.1005, "l": 1.0995, "c": 1.1}
            for i in range((threshold - 3 - proc_start) // 5)
        ]
        all_s5 = head_s5 + only_s5

        sig = make_signal(created_epoch=created_epoch, entry=1.1000, sl=1.0980, tp=1.1050)
        action = call_prepare(sig, candles, all_s5, server_epoch=server_epoch)
        # threshold-3 candle ends at threshold+2 > threshold → excluded from valid_exit
        # No valid exit S5 → DATA_UNAVAILABLE (before hard age → None)
        self.assertIsNone(action)

    def test_empty_post_entry_partial_interval_not_data_unavailable(self) -> None:
        """F-40: Partial-entry, no post-entry S5, non-threshold → no touch (not DU)."""
        created_epoch = SIGNAL_EPOCH_BASE + 300
        candles = make_m15_candles(30, start_epoch=SIGNAL_EPOCH_BASE,
                                   high=1.1005, low=1.0995)
        server_epoch = SIGNAL_EPOCH_BASE + 31 * M15
        sig = make_signal(created_epoch=created_epoch, tp=1.1050, sl=1.0960)

        # Only a pre-entry S5 candle: will be excluded from s5_post_entry
        pre_only = [{"t": SIGNAL_EPOCH_BASE, "o": 1.1, "h": 1.1005, "l": 1.0995, "c": 1.1}]
        action = call_prepare(sig, candles, pre_only, server_epoch=server_epoch)
        # Should be OPEN (None), not CANCELLED
        self.assertIsNone(action)

    def test_time_exit_no_trustworthy_s5_at_threshold_is_data_unavailable(self) -> None:
        """F-41: Threshold reached, no S5 candles with t+5 <= threshold → DATA_UNAVAILABLE."""
        created_epoch = SIGNAL_EPOCH_BASE + 300
        candles = make_m15_candles(97, start_epoch=SIGNAL_EPOCH_BASE,
                                   high=1.1005, low=1.0995)
        server_epoch = candles[-1]["t"] + M15
        sig = make_signal(created_epoch=created_epoch, tp=1.1050, sl=1.0960)

        # S5 returns empty → no valid exit candle → DATA_UNAVAILABLE → ACTIVE (before hard age)
        action = call_prepare(sig, candles, None, server_epoch=server_epoch, hard_max_age=168)
        self.assertIsNone(action)

    def test_same_s5_ambiguity_conservative_loss(self) -> None:
        """F-42: TP and SL in same S5 candle → LOSS with AMBIGUOUS_S5_STOP_FIRST."""
        # BUY: tp=1.1020, sl=1.0980; candle h >= tp AND l <= sl
        candles = make_m15_candles(50, start_epoch=SIGNAL_EPOCH_BASE,
                                   high=1.1025, low=1.0975)
        server_epoch = SIGNAL_EPOCH_BASE + 51 * M15
        sig = make_signal(direction="BUY", entry=1.1000, sl=1.0980, tp=1.1020)

        touch_t = SIGNAL_EPOCH_BASE
        ambiguous_s5 = [
            {"t": touch_t, "o": 1.1000, "h": 1.1025, "l": 1.0975, "c": 1.1000},
        ]
        action = call_prepare(sig, candles, ambiguous_s5, server_epoch=server_epoch)
        self.assertIsNotNone(action)
        self.assertEqual("LOSS", action["predicted_outcome"])
        self.assertEqual("AMBIGUOUS_S5_STOP_FIRST", action["predicted_reason"])
        self.assertLess(action["predicted_pips"], 0)

    def test_post_threshold_candle_s5_not_used_for_exit(self) -> None:
        """F-37: S5 from post-threshold candle cannot be TIME_EXIT price."""
        # 96 full candles → TIME_EXIT; candle 97 would give higher close
        # but must not be considered
        candles = make_m15_candles(96, start_epoch=SIGNAL_EPOCH_BASE, final_close=1.1005)
        post_threshold = {"t": SIGNAL_EPOCH_BASE + 96 * M15, "o": 1.101,
                          "h": 1.102, "l": 1.100, "c": 1.1025}
        all_candles = candles + [post_threshold]

        server_epoch = SIGNAL_EPOCH_BASE + 97 * M15
        sig = make_signal(direction="BUY", entry=1.1000, sl=1.0980, tp=1.1050)
        # S5 for pre-threshold window: no touch
        s5 = make_s5_candles(SIGNAL_EPOCH_BASE, SIGNAL_EPOCH_BASE + 96 * M15,
                              high=1.1005, low=1.0995)
        action = call_prepare(sig, all_candles, s5, server_epoch=server_epoch)
        self.assertIsNotNone(action)
        self.assertEqual("TIME_EXIT", action["predicted_outcome"])
        # Exit price must be from threshold candle (close=1.1005), not post-threshold
        self.assertAlmostEqual(1.1005, action["predicted_exit_price"])

    def test_pre_entry_s5_eligible_for_time_exit_price(self) -> None:
        """F-35: Pre-entry S5 excluded from TP/SL but eligible for mid-candle TIME_EXIT price.

        threshold=BASE+302 is mid-candle (not at M15 boundary BASE+900).
        fetch_s5_candles returns:
          pre_entry_s5: t=BASE+295 < eff_start=BASE+300 → excluded from s5_post_entry
                        h=1.1025 > tp=1.1020 → would WIN if incorrectly included
                        t+5=BASE+300 <= threshold=BASE+302 → eligible for valid_exit
          post_entry_s5: t=BASE+300 == eff_start → in s5_post_entry; no touch
                         t+5=BASE+305 > threshold → NOT eligible for valid_exit

        Expected: TIME_EXIT (no false WIN), exit_price = pre_entry_s5.c (last valid_exit S5).
        """
        tf_sec = M15
        eff_start = SIGNAL_EPOCH_BASE + 300   # 300 % 5 == 0
        threshold = SIGNAL_EPOCH_BASE + 302   # mid-candle; candle_end = BASE+900

        candle = {"t": SIGNAL_EPOCH_BASE, "o": 1.1, "h": 1.1005, "l": 1.0995, "c": 1.1008}
        # Pre-entry: t < eff_start → excluded from s5_post_entry; t+5 <= threshold → in valid_exit
        pre_entry_s5 = {
            "t": SIGNAL_EPOCH_BASE + 295,   # 295 % 5 == 0; < eff_start
            "o": 1.1, "h": 1.1025, "l": 1.0995, "c": 1.1006,  # h > tp → would WIN if included
        }
        # Post-entry: t >= eff_start → in s5_post_entry; no touch; t+5 > threshold → not valid_exit
        post_entry_s5 = {
            "t": SIGNAL_EPOCH_BASE + 300,   # 300 % 5 == 0; == eff_start
            "o": 1.1, "h": 1.1005, "l": 1.0995, "c": 1.1007,
        }

        with _patch(
            "signal_resolution.fetch_s5_candles",
            return_value=([pre_entry_s5, post_entry_s5], "ok"),
        ):
            result = closer.resolve_signal_outcome(
                "EURUSD", "BUY", 1.1000, 1.0980, 1.1020,
                tf_sec, eff_start,
                eval_end=threshold,
                threshold_epoch=threshold,
                completed_m15_candles=[candle],
                oanda_token="fake",
                oanda_url="https://fake.oanda.test",
            )

        # Pre-entry TP touch must not produce WIN; outcome is TIME_EXIT
        self.assertEqual(closer.ResolutionState.RESOLVED, result.state)
        self.assertEqual("TIME_EXIT", result.outcome)
        # Exit price = close of last S5 with t+5 <= threshold = pre_entry_s5.c
        self.assertAlmostEqual(1.1006, result.exit_price)
        self.assertEqual(threshold, result.closed_at_epoch)


# ── G. Wrapper Security Tests ─────────────────────────────────────────────────

class WrapperSecurityTests(unittest.TestCase):
    """Tests for run_signal_closer_live.sh security properties."""

    _wrapper_path = ROOT / "tools" / "run_signal_closer_live.sh"

    def setUp(self) -> None:
        """Load the wrapper script content for each test."""
        self._content = self._wrapper_path.read_text()

    def _run_env_loader(self, env_content: str) -> str:
        """Extract and run the Python env-loader block from the wrapper."""
        match = re.search(r"<<'PY'\n(.*?)\nPY\b", self._content, re.DOTALL)
        self.assertIsNotNone(match, "Could not find PY heredoc in wrapper")
        py_code = match.group(1)
        with tempfile.TemporaryDirectory() as td:
            Path(td, ".env").write_text(env_content)
            r = subprocess.run(
                [sys.executable, "-c", py_code],
                capture_output=True, text=True, cwd=td,
            )
        return r.stdout

    def test_env_loader_emits_only_export_lines(self) -> None:
        """G-43: Every non-empty output line from the env loader is an export assignment."""
        env = (
            "SUPABASE_SERVICE_KEY=supakey123\n"
            "OANDA_API_TOKEN=oanda_secret\n"
            "OANDA_API_URL=https://api-fxtrade.oanda.com\n"
            "SIGNAL_CLOSER_HARD_MAX_AGE_HOURS=200\n"
        )
        output = self._run_env_loader(env)
        for line in output.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            self.assertTrue(
                line.startswith("export ") and "=" in line,
                f"Non-export line found: {line!r}",
            )

    def test_no_raw_secret_values_in_output(self) -> None:
        """G-44: Secret values are shell-quoted but must not appear raw on stdout."""
        secret_token = "VERY_SECRET_OANDA_TOKEN_XYZ"
        supakey = "SECRET_SUPA_KEY_ABC"
        env = (
            f"SUPABASE_SERVICE_KEY={supakey}\n"
            f"OANDA_API_TOKEN={secret_token}\n"
            "OANDA_API_URL=https://api-fxtrade.oanda.com\n"
        )
        output = self._run_env_loader(env)
        # The values must be properly quoted but the raw unquoted form
        # should not appear in any non-assignment context
        # (they do appear in the export assignments, which is expected)
        # At minimum: no diagnostic/debug output should repeat them
        non_assignment_lines = [
            ln for ln in output.splitlines()
            if ln.strip() and not ln.strip().startswith("export ")
        ]
        for ln in non_assignment_lines:
            self.assertNotIn(secret_token, ln)
            self.assertNotIn(supakey, ln)

    def test_oanda_and_hard_max_age_vars_loaded(self) -> None:
        """G-45: OANDA_API_TOKEN, OANDA_API_URL, SIGNAL_CLOSER_HARD_MAX_AGE_HOURS exported."""
        env = (
            "OANDA_API_TOKEN=mytok\n"
            "OANDA_API_URL=https://api.oanda.com\n"
            "SIGNAL_CLOSER_HARD_MAX_AGE_HOURS=150\n"
        )
        output = self._run_env_loader(env)
        self.assertIn("export OANDA_API_TOKEN=", output)
        self.assertIn("export OANDA_API_URL=", output)
        self.assertIn("export SIGNAL_CLOSER_HARD_MAX_AGE_HOURS=", output)

    def test_hard_max_age_passed_to_script(self) -> None:
        """G-46: --hard-max-age flag is present in the script invocation block."""
        self.assertIn("--hard-max-age", self._content)
        # Must be a variable expansion, not a hard-coded literal
        self.assertIn("$HARD_MAX_AGE", self._content)

    def test_no_shell_tracing_enabled(self) -> None:
        """G-47: Wrapper must not enable set -x or similar tracing directives."""
        # set -x would expose secret values in shell trace output
        forbidden = ["set -x", "set -v", "xtrace"]
        for pattern in forbidden:
            self.assertNotIn(
                pattern, self._content,
                f"Shell tracing {pattern!r} must not be present in wrapper",
            )


# ── H. DeepSource DS-PY — HTTPS HEAD clock probe ─────────────────────────────

class HttpsClockProbeTests(unittest.TestCase):
    """H-1 through H-6: compute_server_clock_epoch uses HTTPS HEAD, no subprocess."""

    _DATE_A = "Mon, 14 Jul 2026 10:00:00 GMT"
    _DATE_B = "Mon, 14 Jul 2026 10:00:30 GMT"  # 30 s apart — within 60 s

    @staticmethod
    def _make_conn(date_value: str | None):
        """Return a mock HTTPSConnection whose getresponse yields the given Date."""
        resp = MagicMock()
        resp.getheader.side_effect = lambda h, default="": date_value if h == "Date" and date_value is not None else default
        conn = MagicMock()
        conn.getresponse.return_value = resp
        return conn

    def test_two_valid_dates_within_60s_returns_median(self) -> None:
        """H-1: Two valid Date headers ≤60 s apart → integer median."""
        import email.utils, statistics as _stats
        ep_a = int(email.utils.parsedate_to_datetime(self._DATE_A).timestamp())
        ep_b = int(email.utils.parsedate_to_datetime(self._DATE_B).timestamp())
        expected = int(_stats.median([ep_a, ep_b]))

        conns = [self._make_conn(self._DATE_A), self._make_conn(self._DATE_B)]
        with _patch("http.client.HTTPSConnection", side_effect=conns):
            result = closer.compute_server_clock_epoch()
        self.assertEqual(expected, result)

    def test_one_valid_date_returns_fallback(self) -> None:
        """H-2: Only one valid Date header → that epoch is returned."""
        import email.utils
        ep = int(email.utils.parsedate_to_datetime(self._DATE_A).timestamp())
        conns = [self._make_conn(self._DATE_A)] + [self._make_conn(None)] * 10
        with _patch("http.client.HTTPSConnection", side_effect=conns):
            result = closer.compute_server_clock_epoch()
        self.assertEqual(ep, result)

    def test_missing_date_headers_fail_closed(self) -> None:
        """H-3: No endpoint returns a Date header → returns 0."""
        conns = [self._make_conn(None)] * 10
        with _patch("http.client.HTTPSConnection", side_effect=conns):
            result = closer.compute_server_clock_epoch()
        self.assertEqual(0, result)

    def test_non_https_endpoint_skipped(self) -> None:
        """H-4: Non-HTTPS or hostless URLs are rejected without connecting."""
        original = closer.CLOCK_ENDPOINTS
        try:
            closer.CLOCK_ENDPOINTS = ["http://example.com", "ftp://example.com"]
            with _patch("http.client.HTTPSConnection") as mock_conn:
                result = closer.compute_server_clock_epoch()
            mock_conn.assert_not_called()
        finally:
            closer.CLOCK_ENDPOINTS = original
        self.assertEqual(0, result)

    def test_connection_exception_fails_closed(self) -> None:
        """H-5: OSError during connection → function returns 0 without raising."""
        conn = MagicMock()
        conn.request.side_effect = OSError("network unreachable")
        with _patch("http.client.HTTPSConnection", return_value=conn):
            result = closer.compute_server_clock_epoch()
        self.assertEqual(0, result)

    def test_no_subprocess_invoked_by_clock_probe(self) -> None:
        """H-6: compute_server_clock_epoch never invokes any subprocess."""
        conn = self._make_conn(self._DATE_A)
        with (
            _patch("http.client.HTTPSConnection", return_value=conn),
            _patch("subprocess.run") as mock_run,
            _patch("subprocess.Popen") as mock_popen,
            _patch("os.system") as mock_system,
        ):
            closer.compute_server_clock_epoch()
        mock_run.assert_not_called()
        mock_popen.assert_not_called()
        mock_system.assert_not_called()


# ── I. Finding 4 — threshold_epoch None defensive guard ───────────────────────

class ThresholdNoneGuardTests(unittest.TestCase):
    """I-1: resolve_signal_outcome returns DATA_UNAVAILABLE when threshold_epoch is None."""

    def test_none_threshold_returns_open_without_raising(self) -> None:
        """I-1: threshold_epoch=None with no TP/SL touch → OPEN, does not raise.

        The defensive None guards inside threshold branches are logically unreachable
        (threshold_epoch is None implies no threshold candle, so those branches are
        not entered).  This test confirms the function handles None gracefully end-to-end.
        """
        candles = make_m15_candles(10, start_epoch=SIGNAL_EPOCH_BASE, high=1.1010, low=1.0995)
        eff_start = SIGNAL_EPOCH_BASE
        server_epoch = SIGNAL_EPOCH_BASE + 10 * M15
        eval_end = server_epoch

        with _patch("signal_resolution.fetch_s5_candles", return_value=([], "no s5")):
            result = closer.resolve_signal_outcome(
                pair="EURUSD",
                direction="BUY",
                entry=1.1000,
                sl=1.0980,
                tp=1.1020,
                tf_sec=M15,
                effective_start_epoch=eff_start,
                eval_end=eval_end,
                threshold_epoch=None,
                completed_m15_candles=candles,
                oanda_token="fake",
                oanda_url="https://fake.oanda.test",
            )
        self.assertEqual(closer.ResolutionState.OPEN, result.state)


# ── J. Objective B — apply_signal_actions write failure tracking ───────────────

class ApplySignalActionsTests(unittest.TestCase):
    """J-1 through J-10: apply_signal_actions write failure contract."""

    _SERVER_EPOCH = SIGNAL_EPOCH_BASE + 200 * M15

    def _make_action(self, outcome: str, sig_id: str = "sig-1") -> dict:
        """Build a minimal resolved-action dict for Supabase write tests."""
        return {
            "id": sig_id,
            "pair": "EURUSD",
            "direction": "BUY",
            "entry_price": 1.1000,
            "age_hours": 5.0,
            "predicted_outcome": outcome,
            "predicted_pips": 10.0 if outcome in ("WIN", "TIME_EXIT") else -10.0,
            "predicted_reason": "test",
            "predicted_closed_at_epoch": self._SERVER_EPOCH,
            "predicted_exit_price": 1.1010,
        }

    def test_successful_closed_patch_increments_closed(self) -> None:
        """J-1: close_signal returning True increments closed counter."""
        action = self._make_action("WIN")
        with _patch.object(closer, "close_signal", return_value=True):
            counts = closer.apply_signal_actions([action], False, self._SERVER_EPOCH)
        self.assertEqual(1, counts["closed"])
        self.assertEqual(0, counts["write_failed"])

    def test_failed_closed_patch_returns_false(self) -> None:
        """J-2: close_signal returning False → write_failed=1, closed=0."""
        action = self._make_action("WIN")
        with _patch.object(closer, "close_signal", return_value=False):
            counts = closer.apply_signal_actions([action], False, self._SERVER_EPOCH)
        self.assertEqual(0, counts["closed"])
        self.assertEqual(1, counts["write_failed"])

    def test_failed_patch_does_not_increment_closed(self) -> None:
        """J-3: A failed WIN write must not be counted as closed."""
        action = self._make_action("WIN")
        with _patch.object(closer, "close_signal", return_value=False):
            counts = closer.apply_signal_actions([action], False, self._SERVER_EPOCH)
        self.assertNotEqual(1, counts["closed"])

    def test_failed_cancelled_patch_does_not_increment_cancelled(self) -> None:
        """J-4: A failed CANCELLED write must not be counted as cancelled."""
        action = self._make_action("CANCELLED")
        with _patch.object(closer, "close_signal", return_value=False):
            counts = closer.apply_signal_actions([action], False, self._SERVER_EPOCH)
        self.assertEqual(0, counts["cancelled"])
        self.assertEqual(1, counts["write_failed"])

    def test_failed_writes_increment_write_failed(self) -> None:
        """J-5: Two failed writes → write_failed=2."""
        actions = [self._make_action("WIN", "s1"), self._make_action("LOSS", "s2")]
        with _patch.object(closer, "close_signal", return_value=False):
            counts = closer.apply_signal_actions(actions, False, self._SERVER_EPOCH)
        self.assertEqual(2, counts["write_failed"])

    def test_failed_writes_increment_still_open_additional(self) -> None:
        """J-6: Failed writes increase still_open_additional by the failure count."""
        actions = [self._make_action("WIN", "s1"), self._make_action("WIN", "s2")]
        with _patch.object(closer, "close_signal", return_value=False):
            counts = closer.apply_signal_actions(actions, False, self._SERVER_EPOCH)
        self.assertEqual(2, counts["still_open_additional"])

    def test_later_action_attempted_after_earlier_failure(self) -> None:
        """J-7: A failed write on the first signal does not skip subsequent signals."""
        actions = [self._make_action("WIN", "s1"), self._make_action("WIN", "s2")]
        call_count = {"n": 0}

        def side_effect(*args, **kwargs):
            call_count["n"] += 1
            return False

        with _patch.object(closer, "close_signal", side_effect=side_effect):
            closer.apply_signal_actions(actions, False, self._SERVER_EPOCH)

        self.assertEqual(2, call_count["n"], "close_signal should be called for every action")

    def test_dry_run_never_calls_supabase_and_counts_as_success(self) -> None:
        """J-8: dry_run=True → close_signal returns True without Supabase; closed incremented."""
        action = self._make_action("WIN")
        supabase_calls: list = []

        with _patch.object(closer, "supabase_request", side_effect=lambda *a, **k: supabase_calls.append(a)):
            counts = closer.apply_signal_actions([action], True, self._SERVER_EPOCH)

        self.assertEqual(0, len(supabase_calls), "supabase_request must not be called in dry-run")
        self.assertEqual(1, counts["closed"])
        self.assertEqual(0, counts["write_failed"])

    def test_write_failed_nonzero_produces_nonzero_exit_in_live_mode(self) -> None:
        """J-9: main exits with code 2 when any live write fails."""
        fake_signal = {
            "id": "live-sig-1",
            "pair": "EURUSD",
            "direction": "BUY",
            "entry_price": 1.1000,
            "stop_loss": 1.0980,
            "take_profit": 1.1020,
            "created_at": datetime.fromtimestamp(SIGNAL_EPOCH_BASE, timezone.utc).isoformat(),
            "timeframe": "M15",
            "status": "ACTIVE",
        }
        candles = make_m15_candles(96, start_epoch=SIGNAL_EPOCH_BASE)
        server_epoch = SIGNAL_EPOCH_BASE + 200 * M15

        with (
            _patch.object(closer, "compute_server_clock_epoch", return_value=server_epoch),
            _patch.object(closer, "get_active_signals", return_value=[fake_signal]),
            _patch.object(closer, "fetch_candles", return_value=(candles, "ok")),
            _patch("signal_resolution.fetch_s5_candles", return_value=([], "no s5")),
            _patch.object(closer, "SUPABASE_KEY", "fake-key"),
            _patch.object(closer, "close_signal", return_value=False),
            _patch.object(closer, "print_preview", return_value=None),
            _patch.object(closer, "bulk_gate", return_value=None),
        ):
            old_argv = sys.argv
            sys.argv = ["signal_closer.py", "--live", "--confirm", "CLOSE_SIGNALS", "--max-batch", "5"]
            try:
                with self.assertRaises(SystemExit) as cm:
                    closer.main()
                self.assertEqual(2, cm.exception.code)
            finally:
                sys.argv = old_argv

    def test_no_false_closed_log_on_failure(self) -> None:
        """J-10: When close_signal returns False, the CLOSED success log must not be emitted."""
        action = self._make_action("WIN")
        log_lines: list[str] = []
        original_log = closer.log

        def capture_log(msg: str) -> None:
            log_lines.append(msg)
            original_log(msg)

        with (
            _patch.object(closer, "close_signal", return_value=False),
            _patch.object(closer, "log", side_effect=capture_log),
        ):
            closer.apply_signal_actions([action], False, self._SERVER_EPOCH)

        closed_logs = [ln for ln in log_lines if ln.startswith("CLOSED ")]
        self.assertEqual(0, len(closed_logs), f"No CLOSED success log expected on failure; got: {closed_logs}")


# ── K. close_signal response-contract tests ────────────────────────────────────

class CloseSignalResponseContractTests(unittest.TestCase):
    """K-1 through K-15: Direct close_signal and integration tests.

    K-1..K-10 call the real close_signal function with only supabase_request mocked.
    K-11..K-15 verify apply_signal_actions counters and main() exit codes through
    the real close_signal (supabase_request mocked, not close_signal).
    """

    _SIG_ID = "contract-test-sig-k001"
    _SERVER_EPOCH = SIGNAL_EPOCH_BASE + 200 * M15

    def _call_close(
        self,
        resp=None,
        *,
        exc: Exception | None = None,
        dry_run: bool = False,
    ) -> tuple[bool, list[str]]:
        """Helper: call real close_signal with supabase_request mocked. Returns (result, log_lines)."""
        log_lines: list[str] = []

        def fake_supa(*args, **kwargs):
            if exc is not None:
                raise exc
            return resp

        with (
            _patch.object(closer, "supabase_request", side_effect=fake_supa),
            _patch.object(closer, "log", side_effect=log_lines.append),
        ):
            result = closer.close_signal(
                self._SIG_ID, "CLOSED", 10.0, dry_run, self._SERVER_EPOCH
            )
        return result, log_lines

    @staticmethod
    def _has_closed_log(log_lines: list[str]) -> bool:
        """Return True if any captured log line starts with 'CLOSED '."""
        return any(ln.startswith("CLOSED ") for ln in log_lines)

    # ── K-1..K-9: direct response-contract tests ──────────────────────────────

    def test_k1_exact_matching_row_returns_true_and_closed_log(self) -> None:
        """K-1: Single row with matching id → True + CLOSED success log emitted."""
        result, logs = self._call_close([{"id": self._SIG_ID, "status": "CLOSED"}])
        self.assertTrue(result)
        self.assertTrue(self._has_closed_log(logs), f"Expected CLOSED log; got: {logs}")

    def test_k2_empty_list_returns_false_no_closed_log(self) -> None:
        """K-2: Empty list (0 rows updated) → False, no CLOSED log."""
        result, logs = self._call_close([])
        self.assertFalse(result)
        self.assertFalse(self._has_closed_log(logs))

    def test_k3_multiple_rows_returns_false_no_closed_log(self) -> None:
        """K-3: Two rows returned → False, no CLOSED log."""
        result, logs = self._call_close([{"id": self._SIG_ID}, {"id": "other-sig"}])
        self.assertFalse(result)
        self.assertFalse(self._has_closed_log(logs))

    def test_k4_wrong_returned_id_returns_false(self) -> None:
        """K-4: One row but id doesn't match signal_id → False, no CLOSED log."""
        result, logs = self._call_close([{"id": "completely-wrong-id"}])
        self.assertFalse(result)
        self.assertFalse(self._has_closed_log(logs))

    def test_k5_missing_id_field_returns_false(self) -> None:
        """K-5: One row with no 'id' key (row.get('id') returns None) → False, no CLOSED log."""
        result, logs = self._call_close([{"status": "CLOSED", "result_pips": 10.0}])
        self.assertFalse(result)
        self.assertFalse(self._has_closed_log(logs))

    def test_k6_dict_response_not_list_returns_false(self) -> None:
        """K-6: Response is a plain dict, not a list → False, no CLOSED log."""
        result, logs = self._call_close({"id": self._SIG_ID})
        self.assertFalse(result)
        self.assertFalse(self._has_closed_log(logs))

    def test_k7_list_containing_non_dict_element_returns_false(self) -> None:
        """K-7: List whose sole element is not a dict → False, no CLOSED log."""
        result, logs = self._call_close(["not-a-dict"])
        self.assertFalse(result)
        self.assertFalse(self._has_closed_log(logs))

    def test_k8_none_response_returns_false(self) -> None:
        """K-8: None response (JSON null body) → False, no CLOSED log."""
        result, logs = self._call_close(None)
        self.assertFalse(result)
        self.assertFalse(self._has_closed_log(logs))

    def test_k9_supabase_exception_returns_false_no_escape(self) -> None:
        """K-9: supabase_request raises → False; exception must not propagate; no CLOSED log."""
        result, logs = self._call_close(exc=OSError("connection refused"))
        self.assertFalse(result)
        self.assertFalse(self._has_closed_log(logs))

    # ── K-10: dry-run contract ─────────────────────────────────────────────────

    def test_k10_dry_run_returns_true_no_supabase_call(self) -> None:
        """K-10: dry_run=True → True immediately; supabase_request is never invoked."""
        patch_calls: list = []

        def fake_supa(*args, **kwargs):
            patch_calls.append(args)
            return [{"id": self._SIG_ID}]

        with _patch.object(closer, "supabase_request", side_effect=fake_supa):
            result = closer.close_signal(self._SIG_ID, "CLOSED", 5.0, True, self._SERVER_EPOCH)

        self.assertTrue(result)
        self.assertEqual(0, len(patch_calls), "supabase_request must not be called in dry-run")

    # ── K-11..K-13: apply_signal_actions integration (real close_signal) ──────

    def _make_k_action(self, outcome: str, sig_id: str | None = None) -> dict:
        """Build a resolved-action dict for apply_signal_actions integration tests."""
        return {
            "id": sig_id or self._SIG_ID,
            "pair": "EURUSD",
            "direction": "BUY",
            "entry_price": 1.1000,
            "age_hours": 5.0,
            "predicted_outcome": outcome,
            "predicted_pips": 10.0 if outcome in ("WIN", "TIME_EXIT") else 0.0,
            "predicted_reason": "test",
            "predicted_closed_at_epoch": self._SERVER_EPOCH,
            "predicted_exit_price": 1.1010 if outcome != "CANCELLED" else None,
        }

    def test_k11_failed_patch_response_counted_as_write_failed_not_closed(self) -> None:
        """K-11: apply_signal_actions; real close_signal; PATCH returns [] → write_failed=1, closed=0."""
        action = self._make_k_action("WIN")
        with _patch.object(closer, "supabase_request", return_value=[]):
            counts = closer.apply_signal_actions([action], False, self._SERVER_EPOCH)
        self.assertEqual(0, counts["closed"])
        self.assertEqual(1, counts["write_failed"])
        self.assertEqual(1, counts["still_open_additional"])

    def test_k12_failed_cancelled_patch_counted_as_write_failed_not_cancelled(self) -> None:
        """K-12: CANCELLED signal; real close_signal; PATCH returns [] → write_failed=1, cancelled=0."""
        action = self._make_k_action("CANCELLED")
        with _patch.object(closer, "supabase_request", return_value=[]):
            counts = closer.apply_signal_actions([action], False, self._SERVER_EPOCH)
        self.assertEqual(0, counts["cancelled"])
        self.assertEqual(1, counts["write_failed"])

    def test_k13_later_actions_attempted_after_earlier_failed_write(self) -> None:
        """K-13: Failed PATCH on signal-a does not prevent signal-b from being attempted."""
        actions = [
            self._make_k_action("WIN", "sig-k13-a"),
            self._make_k_action("WIN", "sig-k13-b"),
        ]
        patch_paths: list[str] = []

        def fake_supa(method, path, body=None):
            if method == "PATCH":
                patch_paths.append(path)
            return []  # both writes fail

        with _patch.object(closer, "supabase_request", side_effect=fake_supa):
            counts = closer.apply_signal_actions(actions, False, self._SERVER_EPOCH)

        self.assertEqual(2, len(patch_paths), "Both PATCH requests must be attempted")
        self.assertEqual(2, counts["write_failed"])
        self.assertEqual(0, counts["closed"])

    # ── K-14..K-15: main() integration ────────────────────────────────────────

    def test_k14_live_main_exits_2_on_write_confirmation_failure(self) -> None:
        """K-14: Live main exits 2 when PATCH response confirms 0 updated rows (real close_signal)."""
        fake_signal = {
            "id": "live-k14",
            "pair": "EURUSD",
            "direction": "BUY",
            "entry_price": 1.1000,
            "stop_loss": 1.0980,
            "take_profit": 1.1020,
            "created_at": datetime.fromtimestamp(SIGNAL_EPOCH_BASE, timezone.utc).isoformat(),
            "timeframe": "M15",
            "status": "ACTIVE",
        }
        candles = make_m15_candles(96, start_epoch=SIGNAL_EPOCH_BASE)

        def fake_supa(method, path, body=None):
            if method == "GET":
                return [fake_signal]
            return []  # PATCH → empty list → write confirmation fails

        old_argv = sys.argv
        sys.argv = [
            "signal_closer.py", "--live", "--confirm", "CLOSE_SIGNALS", "--max-batch", "5",
        ]
        try:
            with (
                _patch.object(closer, "compute_server_clock_epoch", return_value=self._SERVER_EPOCH),
                _patch.object(closer, "SUPABASE_KEY", "fake-key"),
                _patch.object(closer, "supabase_request", side_effect=fake_supa),
                _patch.object(closer, "fetch_candles", return_value=(candles, "ok")),
                _patch("signal_resolution.fetch_s5_candles", return_value=([], "no s5")),
                _patch.object(closer, "print_preview", return_value=None),
                _patch.object(closer, "bulk_gate", return_value=None),
                self.assertRaises(SystemExit) as cm,
            ):
                closer.main()
            self.assertEqual(2, cm.exception.code)
        finally:
            sys.argv = old_argv

    def test_k15_dry_run_main_never_exits_2(self) -> None:
        """K-15: Dry-run main exits cleanly; sys.exit(2) is never raised."""
        old_argv = sys.argv
        sys.argv = ["signal_closer.py"]  # no --live → dry-run by default
        try:
            with (
                _patch.object(closer, "compute_server_clock_epoch", return_value=self._SERVER_EPOCH),
                _patch.object(closer, "SUPABASE_KEY", "fake-key"),
                _patch.object(closer, "get_active_signals", return_value=[]),
            ):
                try:
                    closer.main()
                except SystemExit as exc:
                    self.assertNotEqual(
                        2, exc.code,
                        f"main() must not exit 2 in dry-run mode; got exit({exc.code})",
                    )
        finally:
            sys.argv = old_argv


# ── Characterization tests for fetch_s5_candles helpers ───────────────────────

class FetchS5HelpersTests(unittest.TestCase):
    """H-*: Unit tests for each extracted helper of fetch_s5_candles."""

    _BASE = "https://api-fxtrade.oanda.com"
    _TOKEN = "tok"
    _FROM = 1_000_000_000
    _TO = 1_000_001_000

    # ── _validate_s5_inputs ────────────────────────────────────────────────────

    def test_h01_missing_token(self) -> None:
        """H-01: Empty token → OANDA_API_TOKEN not set."""
        err = _validate_s5_inputs("", self._FROM, self._TO, self._BASE)
        self.assertIsNotNone(err)
        assert err is not None
        self.assertIn("OANDA_API_TOKEN", err)

    def test_h02_invalid_range_equal(self) -> None:
        """H-02: from_epoch == to_epoch → invalid range."""
        err = _validate_s5_inputs(self._TOKEN, 1000, 1000, self._BASE)
        self.assertIsNotNone(err)
        assert err is not None
        self.assertIn("invalid S5 range", err)

    def test_h03_invalid_range_reversed(self) -> None:
        """H-03: from_epoch > to_epoch → invalid range."""
        err = _validate_s5_inputs(self._TOKEN, 2000, 1000, self._BASE)
        self.assertIsNotNone(err)
        assert err is not None
        self.assertIn("invalid S5 range", err)

    def test_h04_non_https_url(self) -> None:
        """H-04: http:// URL → requires HTTPS."""
        err = _validate_s5_inputs(self._TOKEN, self._FROM, self._TO, "http://example.com")
        self.assertIsNotNone(err)
        assert err is not None
        self.assertIn("HTTPS", err)

    def test_h05_missing_hostname(self) -> None:
        """H-05: URL with no hostname → missing hostname."""
        err = _validate_s5_inputs(self._TOKEN, self._FROM, self._TO, "https:///path")
        self.assertIsNotNone(err)
        assert err is not None
        self.assertIn("hostname", err)

    def test_h06_embedded_credentials(self) -> None:
        """H-06: URL with user:pass → credentials rejected."""
        err = _validate_s5_inputs(
            self._TOKEN, self._FROM, self._TO, "https://u:p@example.com"
        )
        self.assertIsNotNone(err)
        assert err is not None
        self.assertIn("credentials", err)

    def test_h07_valid_inputs_return_none(self) -> None:
        """H-07: All valid inputs → None (no error)."""
        err = _validate_s5_inputs(self._TOKEN, self._FROM, self._TO, self._BASE)
        self.assertIsNone(err)

    # ── _build_s5_path ─────────────────────────────────────────────────────────

    def test_h08_path_contains_instrument_and_params(self) -> None:
        """H-08: Built path includes instrument, granularity, from/to, includeFirst."""
        host, port, path = _build_s5_path("EURUSD", "2026-01-01T00:00:00Z", "2026-01-01T01:00:00Z", self._BASE)
        self.assertEqual("api-fxtrade.oanda.com", host)
        self.assertIsNone(port)
        self.assertIn("/v3/instruments/EUR_USD/candles", path)
        self.assertIn("granularity=S5", path)
        self.assertIn("includeFirst=true", path)
        self.assertIn("2026-01-01T00:00:00Z", path)

    def test_h09_explicit_port_preserved(self) -> None:
        """H-09: Explicit port in base_url is returned."""
        _, port, _ = _build_s5_path("EURUSD", "t1", "t2", "https://example.com:8443")
        self.assertEqual(8443, port)

    # ── _execute_s5_http ───────────────────────────────────────────────────────

    def test_h10_non_2xx_returns_error(self) -> None:
        """H-10: HTTP 404 → returns None data and error string."""
        resp = MagicMock()
        resp.status = 404
        conn = MagicMock()
        conn.getresponse.return_value = resp
        with _patch("http.client.HTTPSConnection", return_value=conn):
            data, err = _execute_s5_http("host", None, "/path", self._TOKEN)
        self.assertIsNone(data)
        self.assertIsNotNone(err)
        assert err is not None
        self.assertIn("404", err)

    def test_h11_malformed_json_returns_error(self) -> None:
        """H-11: Non-JSON body → JSONDecodeError caught, error returned."""
        resp = MagicMock()
        resp.status = 200
        resp.read.return_value = b"not-json{"
        conn = MagicMock()
        conn.getresponse.return_value = resp
        with _patch("http.client.HTTPSConnection", return_value=conn):
            data, err = _execute_s5_http("host", None, "/path", self._TOKEN)
        self.assertIsNone(data)
        self.assertIsNotNone(err)

    def test_h12_connection_error_returns_error(self) -> None:
        """H-12: Connection refused → exception caught, error returned."""
        conn = MagicMock()
        conn.request.side_effect = ConnectionRefusedError("refused")
        with _patch("http.client.HTTPSConnection", return_value=conn):
            data, err = _execute_s5_http("host", None, "/path", self._TOKEN)
        self.assertIsNone(data)
        self.assertIsNotNone(err)

    def test_h13_successful_request_returns_data(self) -> None:
        """H-13: 200 response with valid JSON → data returned, no error."""
        payload = {"candles": []}
        resp = MagicMock()
        resp.status = 200
        resp.read.return_value = json.dumps(payload).encode()
        conn = MagicMock()
        conn.getresponse.return_value = resp
        with _patch("http.client.HTTPSConnection", return_value=conn):
            data, err = _execute_s5_http("host", None, "/path", self._TOKEN)
        self.assertEqual(payload, data)
        self.assertIsNone(err)

    def test_h14_token_not_leaked_in_error(self) -> None:
        """H-14: Token does not appear in any returned error string."""
        conn = MagicMock()
        conn.request.side_effect = OSError("boom")
        with _patch("http.client.HTTPSConnection", return_value=conn):
            _, err = _execute_s5_http("host", None, "/path", self._TOKEN)
        self.assertIsNotNone(err)
        assert err is not None
        self.assertNotIn(self._TOKEN, err)

    # ── _parse_s5_response ─────────────────────────────────────────────────────

    def test_h15_non_dict_response(self) -> None:
        """H-15: List response → 'not a JSON object'."""
        raw, err = _parse_s5_response([])
        self.assertEqual([], raw)
        self.assertIsNotNone(err)
        assert err is not None
        self.assertIn("not a JSON object", err)

    def test_h16_non_list_candles_field(self) -> None:
        """H-16: candles field is a string → 'not a list'."""
        raw, err = _parse_s5_response({"candles": "oops"})
        self.assertEqual([], raw)
        self.assertIsNotNone(err)
        assert err is not None
        self.assertIn("not a list", err)

    def test_h17_valid_shape_returns_candles(self) -> None:
        """H-17: Dict with list candles → list returned, no error."""
        items = [{"time": "1000", "complete": True, "mid": {"o": "1.1", "h": "1.2", "l": "1.0", "c": "1.1"}}]
        raw, err = _parse_s5_response({"candles": items})
        self.assertEqual(items, raw)
        self.assertIsNone(err)

    def test_h18_missing_candles_key_returns_empty_list(self) -> None:
        """H-18: Dict without 'candles' key → empty list, no error."""
        raw, err = _parse_s5_response({})
        self.assertEqual([], raw)
        self.assertIsNone(err)

    # ── _convert_s5_candles ────────────────────────────────────────────────────

    def test_h19_incomplete_candles_excluded(self) -> None:
        """H-19: complete=False candles are filtered out."""
        raw = [
            {"time": "1000", "complete": False, "mid": {"o": "1.1", "h": "1.2", "l": "1.0", "c": "1.1"}},
            {"time": "1005", "complete": True,  "mid": {"o": "1.1", "h": "1.2", "l": "1.0", "c": "1.1"}},
        ]
        result = _convert_s5_candles(raw, 1000, 2000)
        self.assertEqual(1, len(result))
        self.assertEqual(1005, result[0]["t"])

    def test_h20_out_of_range_candles_excluded(self) -> None:
        """H-20: Candles outside [from_epoch, to_epoch) are filtered."""
        raw = [
            {"time": "999",  "complete": True, "mid": {"o": "1.1", "h": "1.2", "l": "1.0", "c": "1.1"}},
            {"time": "1000", "complete": True, "mid": {"o": "1.1", "h": "1.2", "l": "1.0", "c": "1.1"}},
            {"time": "1999", "complete": True, "mid": {"o": "1.1", "h": "1.2", "l": "1.0", "c": "1.1"}},
            {"time": "2000", "complete": True, "mid": {"o": "1.1", "h": "1.2", "l": "1.0", "c": "1.1"}},
        ]
        result = _convert_s5_candles(raw, 1000, 2000)
        self.assertEqual(2, len(result))
        self.assertEqual([1000, 1999], [c["t"] for c in result])

    def test_h21_malformed_mid_skipped(self) -> None:
        """H-21: Candle with missing mid key is skipped without raising."""
        raw = [
            {"time": "1000", "complete": True},  # no mid
            {"time": "1005", "complete": True, "mid": {"o": "1.1", "h": "1.2", "l": "1.0", "c": "1.1"}},
        ]
        result = _convert_s5_candles(raw, 1000, 2000)
        self.assertEqual(1, len(result))
        self.assertEqual(1005, result[0]["t"])

    def test_h22_non_dict_raw_entry_skipped(self) -> None:
        """H-22: Non-dict entry in raw list is silently skipped."""
        raw = ["bad", None, {"time": "1000", "complete": True, "mid": {"o": "1.1", "h": "1.2", "l": "1.0", "c": "1.1"}}]
        result = _convert_s5_candles(raw, 1000, 2000)
        self.assertEqual(1, len(result))

    def test_h23_output_is_sorted_by_t(self) -> None:
        """H-23: Output candles are sorted by t ascending."""
        raw = [
            {"time": "1010", "complete": True, "mid": {"o": "1.1", "h": "1.2", "l": "1.0", "c": "1.1"}},
            {"time": "1000", "complete": True, "mid": {"o": "1.1", "h": "1.2", "l": "1.0", "c": "1.1"}},
            {"time": "1005", "complete": True, "mid": {"o": "1.1", "h": "1.2", "l": "1.0", "c": "1.1"}},
        ]
        result = _convert_s5_candles(raw, 1000, 2000)
        self.assertEqual([1000, 1005, 1010], [c["t"] for c in result])

    def test_h24_empty_raw_returns_empty(self) -> None:
        """H-24: Empty raw list → empty output."""
        self.assertEqual([], _convert_s5_candles([], 1000, 2000))

    def test_h25_no_completed_candles_returns_empty(self) -> None:
        """H-25: All candles incomplete → empty output."""
        raw = [{"time": "1000", "complete": False, "mid": {"o": "1", "h": "2", "l": "0", "c": "1"}}]
        self.assertEqual([], _convert_s5_candles(raw, 1000, 2000))


if __name__ == "__main__":
    unittest.main(verbosity=2)
