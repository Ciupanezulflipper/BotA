#!/usr/bin/env python3
"""
BotA Signal Closer v2.1
=======================

Reads ACTIVE signals from Supabase, fetches current candle data,
checks if TP or SL was hit, and updates signal status accordingly.

Rules:
- If price hit TP -> status=CLOSED, result_pips=positive.
- If price hit SL -> status=CLOSED, result_pips=negative.
- Candle outcome detection is attempted BEFORE age cancellation.
- If candles are available and no TP/SL was hit, then signals older than MAX_AGE_HOURS
  may be cancelled with result_pips=0.
- If candles cannot be fetched, the signal is left ACTIVE rather than being cancelled
  blindly. This protects the performance ledger during ship-network outages.

SAFETY MODEL:
- Dry-run is the DEFAULT. Live execution requires explicit flags.
- Live run requires ALL THREE: --live --confirm CLOSE_SIGNALS --max-batch N
- Closing more than 1 signal requires --allow-bulk
- A preview summary is always printed before any live action
- A 3-second abort window is given before live writes begin
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parent.parent

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://ozgkeslgjqbqfewojnmr.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
MAX_AGE_HOURS = int(os.environ.get("SIGNAL_MAX_AGE_HOURS", "24"))
LOG_FILE = ROOT / "logs" / "signal_closer.log"


def log(msg: str) -> None:
    ts = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    line = f"[CLOSER {ts}] {msg}"
    print(line)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def pip_size(pair: str) -> float:
    return 0.01 if "JPY" in pair.upper() else 0.0001


def pips(diff: float, pair: str) -> float:
    return round(diff / pip_size(pair), 1)


def supabase_request(method: str, path: str, body: dict | None = None) -> dict | list:
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    data = json.dumps(body).encode("utf-8") if body else None
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=15) as resp:  # nosec B310
        return json.loads(resp.read().decode("utf-8"))


def get_active_signals() -> list[dict]:
    path = (
        "signals?status=eq.ACTIVE"
        "&select=id,pair,direction,entry_price,stop_loss,take_profit,created_at,timeframe"
    )
    result = supabase_request("GET", path)
    return result if isinstance(result, list) else []


def fetch_candles(pair: str, signal_time: datetime) -> list[dict]:
    try:
        symbol = pair.upper() + "=X"
        period1 = int(signal_time.timestamp())
        period2 = int(datetime.now(timezone.utc).timestamp())
        url = (
            f"https://query1.finance.yahoo.com/v8/finance/chart/"
            f"{urllib.parse.quote(symbol)}"
            f"?interval=15m&period1={period1}&period2={period2}"
        )
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:  # nosec B310
            data = json.loads(resp.read().decode("utf-8"))

        result = data.get("chart", {}).get("result", [])
        if not result:
            return []

        quote_block = result[0]
        timestamps = quote_block.get("timestamp", [])
        quotes = quote_block.get("indicators", {}).get("quote", [{}])[0]
        highs = quotes.get("high", [])
        lows = quotes.get("low", [])

        candles: list[dict] = []
        for i, ts in enumerate(timestamps):
            try:
                high = highs[i]
                low = lows[i]
                if high is not None and low is not None:
                    candles.append({"t": ts, "h": float(high), "l": float(low)})
            except Exception:
                continue

        return candles
    except Exception as exc:
        log(f"ERROR fetching candles for {pair}: {exc}")
        return []


def check_outcome(
    direction: str,
    entry: float,
    sl: float,
    tp: float,
    candles: list[dict],
    pair: str,
) -> tuple[str, float]:
    direction = direction.upper()

    for bar in candles:
        high = bar["h"]
        low = bar["l"]

        if direction == "BUY":
            if high >= tp:
                return "WIN", pips(tp - entry, pair)
            if low <= sl:
                return "LOSS", pips(sl - entry, pair)

        elif direction == "SELL":
            if low <= tp:
                return "WIN", pips(entry - tp, pair)
            if high >= sl:
                return "LOSS", pips(entry - sl, pair)

    return "OPEN", 0.0


def close_signal(signal_id: str, status: str, result_pips: float, dry_run: bool) -> None:
    now = datetime.now(timezone.utc).isoformat()
    body = {
        "status": status,
        "result_pips": round(result_pips, 1),
        "closed_at": now,
    }

    if dry_run:
        log(f"DRY-RUN: would update {signal_id} -> {status} {result_pips:+.1f} pips")
        return

    try:
        path = f"signals?id=eq.{signal_id}"
        supabase_request("PATCH", path, body)
        log(f"CLOSED {signal_id} -> {status} {result_pips:+.1f} pips")
    except Exception as exc:
        log(f"ERROR closing {signal_id}: {exc}")


def safety_gate(args: argparse.Namespace) -> bool:
    """
    Returns True if execution should be dry-run, False if live is approved.
    Exits with error if --live is requested but safety conditions are not met.
    """
    if not args.live:
        return True

    errors: list[str] = []

    if args.confirm != "CLOSE_SIGNALS":
        errors.append(f"--confirm must be exactly 'CLOSE_SIGNALS' (got '{args.confirm}')")

    if args.max_batch <= 0:
        errors.append("--max-batch N is required for live execution (N must be > 0)")

    if errors:
        print("\n[GUARDRAIL] Live execution blocked:")
        for error in errors:
            print(f"  - {error}")
        print(
            "\nExample safe live command:\n"
            "  python3 tools/signal_closer.py --live --confirm CLOSE_SIGNALS --max-batch 5\n"
            "\nTo close more than 1 signal also add: --allow-bulk\n"
        )
        sys.exit(1)

    return False


def bulk_gate(signals_to_act: list[dict], args: argparse.Namespace) -> None:
    """
    Enforces max-batch and allow-bulk rules.
    Exits with error if rules are violated.
    """
    count = len(signals_to_act)

    if count > args.max_batch:
        print(
            f"\n[GUARDRAIL] BLOCKED: {count} signals would be closed "
            f"but --max-batch={args.max_batch}\n"
            f"  Increase --max-batch or narrow scope with --pair / --max-age\n"
        )
        sys.exit(1)

    if count > 1 and not args.allow_bulk:
        print(
            f"\n[GUARDRAIL] BLOCKED: closing {count} signals requires --allow-bulk\n"
            f"  Re-run with --allow-bulk if you intend to close multiple signals\n"
        )
        sys.exit(1)


def print_preview(signals_to_act: list[dict], dry_run: bool) -> None:
    mode = "DRY-RUN" if dry_run else "*** LIVE ***"
    print(f"\n{'=' * 64}")
    print(f"  SIGNAL CLOSER PREVIEW — {mode}")
    print(f"  Signals to act on: {len(signals_to_act)}")
    print(f"{'=' * 64}")

    for sig in signals_to_act:
        age_h = float(sig.get("age_hours", 0.0))
        outcome = sig.get("predicted_outcome", "?")
        pips_val = float(sig.get("predicted_pips", 0.0))
        entry_val = float(sig.get("entry_price", 0.0))
        print(
            f"  {sig.get('pair', '?'):<8} {sig.get('direction', '?'):<5} "
            f"entry={entry_val:.5f}  "
            f"age={age_h:.1f}h  "
            f"outcome={outcome}  pips={pips_val:+.1f}"
        )

    print(f"{'=' * 64}\n")

    if not dry_run:
        print("  Live writes begin in 3 seconds. CTRL+C to abort.")
        time.sleep(3)


def prepare_signal_action(sig: dict, now: datetime, max_age: int) -> dict | None:
    """
    Decide whether a signal should be acted on.

    Critical ordering:
    1. Parse and age the signal.
    2. Fetch candles.
    3. If candles prove WIN/LOSS, close with real pips.
    4. If candles exist and no TP/SL was hit, then age-cancel if expired.
    5. If candles cannot be fetched, skip and leave ACTIVE.

    This prevents stale signals from being cancelled as 0-pip outcomes during
    data outages when TP/SL could have been hit while the closer was offline.
    """
    try:
        pair = sig["pair"]
        direction = sig["direction"]
        entry = float(sig["entry_price"])
        sl = float(sig["stop_loss"])
        tp = float(sig["take_profit"])
        created = datetime.fromisoformat(sig["created_at"].replace("Z", "+00:00"))
    except Exception as exc:
        log(f"ERROR malformed signal payload: {exc}")
        return None

    age_hours = (now - created).total_seconds() / 3600.0
    sig["age_hours"] = age_hours

    candles = fetch_candles(pair, created)
    if not candles:
        log(
            f"WARN: no candles for {pair} {direction} entry={entry} "
            f"age={age_hours:.1f}h — leaving ACTIVE"
        )
        sig["predicted_outcome"] = "SKIP_NO_CANDLES"
        sig["predicted_pips"] = 0.0
        return None

    outcome, result_pips = check_outcome(direction, entry, sl, tp, candles, pair)
    sig["predicted_outcome"] = outcome
    sig["predicted_pips"] = result_pips

    if outcome in ("WIN", "LOSS"):
        return sig

    if age_hours >= max_age:
        sig["predicted_outcome"] = "CANCELLED"
        sig["predicted_pips"] = 0.0
        return sig

    log(f"OPEN {pair} {direction} entry={entry} age={age_hours:.1f}h — still active")
    return None


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "BotA Signal Closer v2.1 — dry-run by default.\n"
            "Live execution requires: --live --confirm CLOSE_SIGNALS --max-batch N"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--live",
        action="store_true",
        help="Enable live writes. Without this flag the script always dry-runs.",
    )
    parser.add_argument(
        "--confirm",
        type=str,
        default="",
        metavar="CLOSE_SIGNALS",
        help="Must be exactly 'CLOSE_SIGNALS' to allow live execution.",
    )
    parser.add_argument(
        "--max-batch",
        type=int,
        default=0,
        dest="max_batch",
        metavar="N",
        help="Maximum number of signals that may be closed. Required for live runs.",
    )
    parser.add_argument(
        "--allow-bulk",
        action="store_true",
        dest="allow_bulk",
        help="Required when closing more than 1 signal in a live run.",
    )
    parser.add_argument(
        "--pair",
        type=str,
        default=None,
        help="Limit to a specific pair (e.g. EURUSD).",
    )
    parser.add_argument(
        "--max-age",
        type=int,
        default=None,
        dest="max_age",
        help="Override SIGNAL_MAX_AGE_HOURS for this run.",
    )

    args = parser.parse_args()

    max_age = args.max_age if args.max_age is not None else MAX_AGE_HOURS
    dry_run = safety_gate(args)

    if not SUPABASE_KEY:
        log("ERROR: SUPABASE_SERVICE_KEY not set")
        sys.exit(1)

    log(
        f"Starting signal closer "
        f"(max_age={max_age}h, dry_run={dry_run}, pair_filter={args.pair or 'ALL'})"
    )

    try:
        signals = get_active_signals()
    except Exception as exc:
        log(f"ERROR fetching active signals: {exc}")
        sys.exit(1)

    if args.pair:
        signals = [
            sig for sig in signals
            if str(sig.get("pair", "")).upper() == args.pair.upper()
        ]

    log(f"Found {len(signals)} ACTIVE signals to evaluate")

    now = datetime.now(timezone.utc)
    signals_to_act: list[dict] = []

    for sig in signals:
        action = prepare_signal_action(sig, now, max_age)
        if action is not None:
            signals_to_act.append(action)

    print_preview(signals_to_act, dry_run)

    if not dry_run:
        bulk_gate(signals_to_act, args)

    closed = 0
    cancelled = 0
    still_open = len(signals) - len(signals_to_act)

    for sig in signals_to_act:
        sig_id = sig["id"]
        pair = sig["pair"]
        direction = sig["direction"]
        entry = float(sig["entry_price"])
        age_hours = float(sig.get("age_hours", 0.0))
        outcome = sig["predicted_outcome"]
        result_pips = float(sig["predicted_pips"])

        if outcome == "CANCELLED":
            log(f"EXPIRED {pair} {direction} entry={entry} age={age_hours:.1f}h -> CANCELLED")
            close_signal(sig_id, "CANCELLED", 0.0, dry_run)
            cancelled += 1
        elif outcome in ("WIN", "LOSS"):
            log(f"{outcome} {pair} {direction} entry={entry} -> {result_pips:+.1f} pips")
            close_signal(sig_id, "CLOSED", result_pips, dry_run)
            closed += 1

    log(f"Done — closed={closed} cancelled={cancelled} still_open={still_open} dry_run={dry_run}")


if __name__ == "__main__":
    main()
