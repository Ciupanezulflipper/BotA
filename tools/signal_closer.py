#!/usr/bin/env python3
"""
BotA Signal Closer v2.3
=======================

Reads ACTIVE signals from Supabase, resolves TP/SL outcomes from the same
OANDA-backed local candle cache used by BotA's indicator pipeline, and updates
signal status accordingly.

Rules:
- If price hit TP -> status=CLOSED, result_pips=positive.
- If price hit SL -> status=CLOSED, result_pips=negative.
- Candle outcome detection is attempted BEFORE age cancellation.
- If OANDA-backed candles are available and no TP/SL was hit, then signals older
  than MAX_AGE_HOURS may be cancelled with result_pips=0.
- If OANDA-backed candles are unavailable, stale, non-covering, or replaced by a
  non-OANDA fallback, the signal is left ACTIVE until HARD_MAX_AGE_HOURS.
- HARD_MAX_AGE_HOURS is an escape hatch to prevent permanent ACTIVE lockout when
  a signal can no longer be resolved from trustworthy candles.

CLOCK SAFETY:
- Trading lifecycle decisions use trusted HTTPS Date headers, not Android local
  phone time.
- If trusted server UTC cannot be obtained, the closer fails closed and does not
  update Supabase.

SAFETY MODEL:
- Dry-run is the DEFAULT. Live execution requires explicit flags.
- Live run requires ALL THREE: --live --confirm CLOSE_SIGNALS --max-batch N
- Closing more than 1 signal requires --allow-bulk
- A preview summary is always printed before any live action
- A 3-second abort window is given before live writes begin
"""

from __future__ import annotations

import argparse
import email.utils
import json
import os
import pathlib
import statistics
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone


ROOT = pathlib.Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / "cache"

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://ozgkeslgjqbqfewojnmr.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

MAX_AGE_HOURS = int(os.environ.get("SIGNAL_MAX_AGE_HOURS", "24"))
HARD_MAX_AGE_HOURS = int(os.environ.get("SIGNAL_CLOSER_HARD_MAX_AGE_HOURS", "168"))
MAX_LOCAL_CANDLE_AGE_SECONDS = int(
    os.environ.get("SIGNAL_CLOSER_MAX_LOCAL_CANDLE_AGE_SECONDS", "7200")
)

DEFAULT_TIMEFRAME = "M15"
FUTURE_CANDLE_TOLERANCE_SECONDS = 300
LOG_FILE = ROOT / "logs" / "signal_closer.log"

CLOCK_ENDPOINTS = [
    "https://www.google.com",
    "https://www.cloudflare.com",
    "https://api-fxpractice.oanda.com",
    "https://query1.finance.yahoo.com",
]


def log(msg: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    line = f"[CLOSER {ts}] {msg}"
    print(line)
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def pip_size(pair: str) -> float:
    return 0.01 if "JPY" in pair.upper() else 0.0001


def pips(diff: float, pair: str) -> float:
    return round(diff / pip_size(pair), 1)


def timeframe_seconds(tf: str) -> int:
    tf = str(tf or DEFAULT_TIMEFRAME).upper()
    mapping = {
        "M1": 60,
        "M5": 300,
        "M15": 900,
        "M30": 1800,
        "H1": 3600,
        "H4": 14400,
        "D1": 86400,
        "D": 86400,
    }
    return mapping.get(tf, 900)


def cache_tf_name(tf: str) -> str:
    tf = str(tf or DEFAULT_TIMEFRAME).upper()
    return "D1" if tf == "D" else tf


def granularity_matches(actual: str, expected_tf: str) -> bool:
    actual = str(actual or "").upper()
    expected_tf = cache_tf_name(expected_tf)
    if not actual:
        return True
    if expected_tf == "D1" and actual == "D":
        return True
    return actual == expected_tf


def compute_server_clock_epoch() -> int:
    """
    Query HTTPS Date headers from multiple endpoints.
    Returns trusted UTC epoch int, or 0 if unavailable/disagreement.
    Mirrors the watcher ship-mode clock strategy without using local phone time.
    """
    epochs: list[int] = []

    for url in CLOCK_ENDPOINTS:
        if len(epochs) >= 2:
            break
        try:
            proc = subprocess.run(
                ["curl", "-sI", "--max-time", "6", url],
                text=True,
                capture_output=True,
                timeout=10,
                check=False,
            )
            date_line = next(
                (line for line in proc.stdout.splitlines() if line.lower().startswith("date:")),
                "",
            )
            if not date_line:
                continue

            dt = email.utils.parsedate_to_datetime(date_line.split(":", 1)[1].strip())
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            epochs.append(int(dt.timestamp()))
        except Exception:
            continue

    if len(epochs) >= 2:
        if max(epochs) - min(epochs) <= 60:
            return int(statistics.median(epochs))
        return 0

    if len(epochs) == 1:
        return epochs[0]

    return 0


def iso_from_epoch(epoch: int) -> str:
    return datetime.fromtimestamp(epoch, timezone.utc).isoformat().replace("+00:00", "Z")


def supabase_request(method: str, path: str, body: dict | None = None) -> dict | list:
    url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/{path}"
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


def load_oanda_cache(pair: str, tf: str, server_epoch: int) -> tuple[list[dict], str]:
    """
    Load local OANDA-backed candle cache.

    Returns:
      (candles, reason)

    Candle format:
      {"t": epoch_seconds, "h": high, "l": low}

    The closer intentionally refuses Yahoo/non-OANDA cache files because signal
    levels are generated from the OANDA-backed pipeline.
    """
    tf = cache_tf_name(tf)
    path = CACHE_DIR / f"{pair.upper()}_{tf}.json"

    if not path.exists():
        return [], f"missing local cache {path}"

    try:
        data = json.loads(path.read_text(errors="replace"))
        result = data.get("chart", {}).get("result", [])
        if not result:
            return [], f"empty chart result in {path}"

        block = result[0]
        meta = block.get("meta", {})
        provider = str(meta.get("_provider") or meta.get("provider") or "").lower()
        granularity = str(meta.get("dataGranularity") or "").upper()

        if provider != "oanda":
            return [], f"non-OANDA cache provider={provider or 'UNKNOWN'} path={path}"

        if not granularity_matches(granularity, tf):
            return [], f"cache granularity mismatch expected={tf} actual={granularity} path={path}"

        timestamps = block.get("timestamp", [])
        quote = block.get("indicators", {}).get("quote", [{}])[0]
        highs = quote.get("high", [])
        lows = quote.get("low", [])

        candles: list[dict] = []
        for i, ts in enumerate(timestamps):
            try:
                high = highs[i]
                low = lows[i]
                if ts is not None and high is not None and low is not None:
                    candles.append({"t": int(ts), "h": float(high), "l": float(low)})
            except Exception:
                continue

        candles.sort(key=lambda c: c["t"])

        if not candles:
            return [], f"no valid OANDA candles in {path}"

        newest_age = int(server_epoch - float(candles[-1]["t"]))

        if newest_age < -FUTURE_CANDLE_TOLERANCE_SECONDS:
            return [], (
                f"local OANDA cache future candle age_sec={newest_age} "
                f"tolerance={FUTURE_CANDLE_TOLERANCE_SECONDS} path={path}"
            )

        if newest_age > MAX_LOCAL_CANDLE_AGE_SECONDS:
            return [], (
                f"local OANDA cache stale age_sec={newest_age} "
                f"limit={MAX_LOCAL_CANDLE_AGE_SECONDS} path={path}"
            )

        return candles, "ok"

    except Exception as exc:
        return [], f"parse error {type(exc).__name__}: {str(exc)[:120]}"


def fetch_candles(
    pair: str,
    signal_time: datetime,
    tf: str,
    server_epoch: int,
) -> tuple[list[dict], str]:
    """
    Fetch candles from local OANDA-backed cache only.

    The cache must cover the signal start. If the first candle is after the
    signal time, the closer refuses to infer outcome because TP/SL may have been
    hit before the available cache window.
    """
    candles, reason = load_oanda_cache(pair, tf, server_epoch)
    if not candles:
        return [], reason

    signal_epoch = int(signal_time.timestamp())
    tf_sec = timeframe_seconds(tf)

    first_ts = int(candles[0]["t"])
    last_ts = int(candles[-1]["t"])

    if first_ts > signal_epoch + tf_sec:
        return [], (
            f"OANDA cache does not cover signal start for {pair} {cache_tf_name(tf)}: "
            f"signal_epoch={signal_epoch} first_ts={first_ts} last_ts={last_ts}"
        )

    return [c for c in candles if int(c["t"]) >= signal_epoch - tf_sec], "ok"


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


def close_signal(
    signal_id: str,
    status: str,
    result_pips: float,
    dry_run: bool,
    closed_at_iso: str,
) -> None:
    body = {
        "status": status,
        "result_pips": round(result_pips, 1),
        "closed_at": closed_at_iso,
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
        reason = sig.get("predicted_reason", "")
        pips_val = float(sig.get("predicted_pips", 0.0))
        entry_val = float(sig.get("entry_price", 0.0))
        reason_suffix = f"  reason={reason}" if reason else ""
        print(
            f"  {sig.get('pair', '?'):<8} {sig.get('direction', '?'):<5} "
            f"entry={entry_val:.5f}  "
            f"age={age_h:.1f}h  "
            f"outcome={outcome}  pips={pips_val:+.1f}"
            f"{reason_suffix}"
        )

    print(f"{'=' * 64}\n")

    if not dry_run:
        print("  Live writes begin in 3 seconds. CTRL+C to abort.")
        time.sleep(3)


def parse_signal_created_at(raw_value: object) -> datetime:
    text = str(raw_value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    created = datetime.fromisoformat(text)
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    return created.astimezone(timezone.utc)


def mark_cancelled(sig: dict, reason: str) -> dict:
    sig["predicted_outcome"] = "CANCELLED"
    sig["predicted_pips"] = 0.0
    sig["predicted_reason"] = reason
    return sig


def prepare_signal_action(
    sig: dict,
    now_utc: datetime,
    now_epoch: int,
    max_age: int,
    hard_max_age: int,
) -> dict | None:
    """
    Decide whether a signal should be acted on.

    Critical ordering:
    1. Parse and age the signal using trusted server UTC.
    2. Fetch OANDA-backed local candles.
    3. If candles prove WIN/LOSS, close with real pips.
    4. If candles exist and no TP/SL was hit, then age-cancel if expired.
    5. If OANDA candles cannot be fetched or do not cover the signal, leave ACTIVE
       until HARD_MAX_AGE_HOURS, then cancel unresolved to prevent dedup lockout.
    """
    try:
        pair = str(sig["pair"]).upper()
        direction = str(sig["direction"]).upper()
        entry = float(sig["entry_price"])
        sl = float(sig["stop_loss"])
        tp = float(sig["take_profit"])
        tf = cache_tf_name(str(sig.get("timeframe") or DEFAULT_TIMEFRAME).upper())
        created = parse_signal_created_at(sig["created_at"])
    except Exception as exc:
        log(f"ERROR malformed signal payload: {exc}")
        return None

    age_hours = (now_utc - created).total_seconds() / 3600.0
    sig["age_hours"] = age_hours

    candles, candle_reason = fetch_candles(pair, created, tf, now_epoch)
    if not candles:
        if age_hours >= hard_max_age:
            log(
                f"HARD_AGE_ESCAPE {pair} {tf} {direction} entry={entry} "
                f"age={age_hours:.1f}h hard_max={hard_max_age}h "
                f"reason={candle_reason} -> CANCELLED unresolved"
            )
            return mark_cancelled(sig, "HARD_AGE_UNRESOLVED_NO_OANDA_CANDLES")

        log(
            f"WARN: no usable OANDA candles for {pair} {tf} {direction} "
            f"entry={entry} age={age_hours:.1f}h reason={candle_reason} — leaving ACTIVE"
        )
        sig["predicted_outcome"] = "SKIP_NO_OANDA_CANDLES"
        sig["predicted_pips"] = 0.0
        sig["predicted_reason"] = candle_reason
        return None

    outcome, result_pips = check_outcome(direction, entry, sl, tp, candles, pair)
    sig["predicted_outcome"] = outcome
    sig["predicted_pips"] = result_pips
    sig["predicted_reason"] = "OANDA_CACHE_RESOLVED"

    if outcome in ("WIN", "LOSS"):
        return sig

    if age_hours >= max_age:
        return mark_cancelled(sig, "MAX_AGE_NO_TP_SL_HIT")

    log(f"OPEN {pair} {tf} {direction} entry={entry} age={age_hours:.1f}h — still active")
    return None


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "BotA Signal Closer v2.3 — dry-run by default.\n"
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
    parser.add_argument(
        "--hard-max-age",
        type=int,
        default=None,
        dest="hard_max_age",
        help="Override SIGNAL_CLOSER_HARD_MAX_AGE_HOURS for this run.",
    )

    args = parser.parse_args()

    max_age = args.max_age if args.max_age is not None else MAX_AGE_HOURS
    hard_max_age = (
        args.hard_max_age if args.hard_max_age is not None else HARD_MAX_AGE_HOURS
    )
    dry_run = safety_gate(args)

    if not SUPABASE_KEY:
        log("ERROR: SUPABASE_SERVICE_KEY not set")
        sys.exit(1)

    server_epoch = compute_server_clock_epoch()
    if server_epoch <= 1000000000:
        log("CLOCK server_clock_unavailable -> FAIL_CLOSED no Supabase writes")
        sys.exit(1)

    now_utc = datetime.fromtimestamp(server_epoch, timezone.utc)
    closed_at_iso = iso_from_epoch(server_epoch)

    log(
        f"CLOCK server_clock_ok epoch={server_epoch} "
        f"utc={closed_at_iso}"
    )
    log(
        f"Starting signal closer "
        f"(max_age={max_age}h, hard_max_age={hard_max_age}h, "
        f"dry_run={dry_run}, pair_filter={args.pair or 'ALL'})"
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

    signals_to_act: list[dict] = []

    for sig in signals:
        action = prepare_signal_action(sig, now_utc, server_epoch, max_age, hard_max_age)
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
        reason = str(sig.get("predicted_reason", ""))

        if outcome == "CANCELLED":
            log(
                f"EXPIRED {pair} {direction} entry={entry} "
                f"age={age_hours:.1f}h reason={reason} -> CANCELLED"
            )
            close_signal(sig_id, "CANCELLED", 0.0, dry_run, closed_at_iso)
            cancelled += 1
        elif outcome in ("WIN", "LOSS"):
            log(
                f"{outcome} {pair} {direction} entry={entry} "
                f"reason={reason} -> {result_pips:+.1f} pips"
            )
            close_signal(sig_id, "CLOSED", result_pips, dry_run, closed_at_iso)
            closed += 1

    log(
        f"Done — closed={closed} cancelled={cancelled} "
        f"still_open={still_open} dry_run={dry_run}"
    )


if __name__ == "__main__":
    main()
