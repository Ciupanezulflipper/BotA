#!/usr/bin/env python3
"""
BotA Signal Closer v3.1
=======================

Resolves ACTIVE signals from Supabase using OANDA-backed local M15 candle
caches plus on-demand OANDA S5 range fetches for precision.

Lifecycle:
- TP hit (S5 confirmed)  → CLOSED, positive pips, event timestamp
- SL hit (S5 confirmed)  → CLOSED, negative pips, event timestamp
- 24 market-open hours   → CLOSED, signed real-price pips, threshold timestamp
- Hard-age data failure  → CANCELLED, zero pips, current server time

CLOCK SAFETY:
- All lifecycle decisions use trusted HTTPS Date headers, not local phone time.

SAFETY MODEL:
- Dry-run is the DEFAULT. Live requires: --live --confirm CLOSE_SIGNALS --max-batch N
- Bulk close requires --allow-bulk
- Preview always printed; 3-second abort window before live writes

CREDENTIALS:
- Telegram: loaded via scoped loader from .env.runtime
- OANDA: loaded by the live wrapper into env before this script runs
- Secret values are never written to logs or stdout
"""

from __future__ import annotations

import argparse
import email.utils
import json
import math
import os
import pathlib
import statistics
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from enum import Enum, auto

ROOT = pathlib.Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / "cache"

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://ozgkeslgjqbqfewojnmr.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

OANDA_API_TOKEN = os.environ.get("OANDA_API_TOKEN", "")
OANDA_API_URL = os.environ.get("OANDA_API_URL", "https://api-fxtrade.oanda.com")

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

S5_SECONDS = 5


# ── Logging ────────────────────────────────────────────────────────────────────

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


# ── Pip maths ─────────────────────────────────────────────────────────────────

def pip_size(pair: str) -> float:
    return 0.01 if "JPY" in pair.upper() else 0.0001


def pips(diff: float, pair: str) -> float:
    return round(diff / pip_size(pair), 1)


# ── Timeframe helpers ─────────────────────────────────────────────────────────

def timeframe_seconds(tf: str) -> int:
    tf = str(tf or DEFAULT_TIMEFRAME).upper()
    mapping = {
        "M1": 60, "M5": 300, "M15": 900, "M30": 1800,
        "H1": 3600, "H4": 14400, "D1": 86400, "D": 86400,
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


# ── Effective-start boundary ───────────────────────────────────────────────────

def ceil_to_s5(epoch: int) -> int:
    """Round integer epoch up to next S5 boundary (ignores sub-second precision)."""
    rem = epoch % S5_SECONDS
    return epoch if rem == 0 else epoch + (S5_SECONDS - rem)


def ceil_to_s5_from_datetime(dt: datetime) -> int:
    """Round datetime (with microsecond precision) up to next S5 boundary.

    Uses integer microsecond arithmetic to avoid float truncation of sub-second
    fields present in Supabase created_at timestamps.
    """
    epoch_td = dt - datetime(1970, 1, 1, tzinfo=timezone.utc)
    total_us = (
        epoch_td.days * 86400 + epoch_td.seconds
    ) * 1_000_000 + epoch_td.microseconds
    s5_us = 5_000_000
    rem = total_us % s5_us
    return total_us // 1_000_000 if rem == 0 else (total_us + s5_us - rem) // 1_000_000


# ── OANDA instrument name ─────────────────────────────────────────────────────

def oanda_instrument(pair: str) -> str:
    """Convert 'EURUSD' → 'EUR_USD' for the OANDA v3 API."""
    pair = pair.upper().replace("_", "")
    if len(pair) == 6:
        return pair[:3] + "_" + pair[3:]
    return pair


# ── Trusted server clock ──────────────────────────────────────────────────────

def compute_server_clock_epoch() -> int:
    epochs: list[int] = []
    for url in CLOCK_ENDPOINTS:
        if len(epochs) >= 2:
            break
        try:
            proc = subprocess.run(
                ["curl", "-sI", "--max-time", "6", url],
                text=True, capture_output=True, timeout=10, check=False,
            )
            date_line = next(
                (l for l in proc.stdout.splitlines() if l.lower().startswith("date:")),
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


# ── Supabase ───────────────────────────────────────────────────────────────────

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


# ── Local M15 cache ────────────────────────────────────────────────────────────

def load_oanda_cache(pair: str, tf: str, server_epoch: int) -> tuple[list[dict], str]:
    """
    Load local OANDA-backed M15 candle cache.

    Returns (candles, reason).  Each candle: {t, o, h, l, c} where o/c may be
    None if missing from the source file.  Only h and l are required for TP/SL
    detection; t is required for all uses.

    Refuses non-OANDA providers, granularity mismatches, future candles, and
    stale caches.
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
        opens = quote.get("open", [])
        closes = quote.get("close", [])

        candles: list[dict] = []
        for i, ts in enumerate(timestamps):
            try:
                high = highs[i] if i < len(highs) else None
                low = lows[i] if i < len(lows) else None
                open_ = opens[i] if i < len(opens) else None
                close = closes[i] if i < len(closes) else None

                # t, h, l must be non-None for a usable candle
                if ts is None or high is None or low is None:
                    continue

                candles.append({
                    "t": int(ts),
                    "o": float(open_) if open_ is not None else None,
                    "h": float(high),
                    "l": float(low),
                    "c": float(close) if close is not None else None,
                })
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
    effective_start_epoch: int,
) -> tuple[list[dict], str]:
    """
    Return completed M15 candles that overlap with the signal's exposure window.

    A candle is eligible if:
    - t + tf_sec > effective_start_epoch  (was open at or after effective start)
    - t + tf_sec <= server_epoch           (is fully completed by now)

    Coverage check (DEFECT 2 fix): at least one candle must contain
    effective_start_epoch in its interval [t, t+tf_sec).  The old check
    ``first_ts + tf_sec <= effective_start_epoch`` incorrectly rejected
    historical caches that had many candles prior to the signal.

    Dedup: identical timestamps are collapsed; conflicting timestamps reject
    the whole cache.
    """
    candles, reason = load_oanda_cache(pair, tf, server_epoch)
    if not candles:
        return [], reason

    tf_sec = timeframe_seconds(tf)

    # Sort and dedup: identical t+h+l → keep one; conflicting h or l → reject
    seen: dict[int, dict] = {}
    for c in candles:  # already sorted by load_oanda_cache
        key = int(c["t"])
        if key in seen:
            ex = seen[key]
            if ex["h"] != c["h"] or ex["l"] != c["l"]:
                return [], f"conflicting duplicate M15 candles for {pair} at t={key}"
        else:
            seen[key] = c
    candles = sorted(seen.values(), key=lambda x: int(x["t"]))

    # Reject non-aligned timestamps (OANDA M15 candles must be divisible by tf_sec)
    for c in candles:
        if int(c["t"]) % tf_sec != 0:
            return [], (
                f"non-aligned M15 timestamp t={c['t']} for {pair} "
                f"(not divisible by {tf_sec})"
            )

    # Coverage check: at least one candle must span effective_start_epoch
    if not any(
        int(c["t"]) <= effective_start_epoch < int(c["t"]) + tf_sec
        for c in candles
    ):
        return [], (
            f"OANDA cache does not cover signal start for {pair} {cache_tf_name(tf)}: "
            f"effective_start_epoch={effective_start_epoch}"
        )

    eligible = [
        c for c in candles
        if int(c["t"]) + tf_sec > effective_start_epoch  # overlaps exposure window
        and int(c["t"]) + tf_sec <= server_epoch           # completed
    ]
    return eligible, "ok"


# ── Market-hours threshold ─────────────────────────────────────────────────────

def compute_threshold(
    candles: list[dict],
    effective_start_epoch: int,
    hold_seconds: int,
    tf_sec: int,
) -> int | None:
    """
    Accumulate market-open seconds from completed M15 candles.

    Each candle contributes:  max(0, candle_end - max(candle_t, effective_start_epoch))

    Returns the exact epoch at which cumulative exposure first reaches
    hold_seconds, or None if not yet reached.

    Because effective_start_epoch is S5-aligned and hold_seconds is a multiple
    of 5, the returned threshold is also S5-aligned.
    """
    cumulative = 0
    for candle in candles:
        t = int(candle["t"])
        candle_end = t + tf_sec
        interval_start = max(t, effective_start_epoch)
        if interval_start >= candle_end:
            continue
        overlap = candle_end - interval_start
        if cumulative + overlap >= hold_seconds:
            remaining = hold_seconds - cumulative
            return interval_start + remaining
        cumulative += overlap
    return None


# ── OANDA S5 fetcher ───────────────────────────────────────────────────────────

def fetch_s5_candles(
    pair: str,
    from_epoch: int,
    to_epoch: int,
    token: str,
    base_url: str,
) -> tuple[list[dict], str]:
    """
    Fetch complete S5 midpoint candles from OANDA for [from_epoch, to_epoch).

    Returns (sorted_candles, reason).  Each candle: {t, o, h, l, c}.
    Token, authorization headers, and API URL are never logged.
    Returns ([], reason) on any failure.
    """
    if not token:
        return [], "OANDA_API_TOKEN not set"
    if from_epoch >= to_epoch:
        return [], f"invalid S5 range from={from_epoch} >= to={to_epoch}"

    instrument = oanda_instrument(pair)
    from_iso = datetime.fromtimestamp(from_epoch, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    to_iso = datetime.fromtimestamp(to_epoch, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    params = f"granularity=S5&price=M&from={from_iso}&to={to_iso}&includeFirst=true"
    path = f"/v3/instruments/{instrument}/candles?{params}"

    try:
        req = urllib.request.Request(
            f"{base_url.rstrip('/')}{path}",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept-Datetime-Format": "UNIX",
            },
        )
        with urllib.request.urlopen(req, timeout=20) as resp:  # nosec B310
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        return [], f"S5 fetch {type(exc).__name__}: {str(exc)[:80]}"

    if not isinstance(data, dict):
        return [], "S5 response is not a JSON object"

    candles_raw = data.get("candles", [])
    if not isinstance(candles_raw, list):
        return [], "S5 candles field is not a list"

    candles: list[dict] = []

    for raw in candles_raw:
        if not isinstance(raw, dict) or not raw.get("complete", False):
            continue
        try:
            t = int(float(raw["time"]))
            if t < from_epoch or t >= to_epoch:
                continue
            mid = raw.get("mid", {})
            candles.append({
                "t": t,
                "o": float(mid["o"]),
                "h": float(mid["h"]),
                "l": float(mid["l"]),
                "c": float(mid["c"]),
            })
        except Exception:
            continue

    candles.sort(key=lambda c: c["t"])

    if not candles:
        return [], f"no complete S5 candles for {pair} [{from_iso}, {to_iso})"

    validated, val_reason = validate_s5_candles(candles)
    if not validated:
        return [], f"S5 validation: {val_reason}"
    return validated, "ok"


# ── S5 validation ──────────────────────────────────────────────────────────────

def validate_s5_candles(candles: list[dict]) -> tuple[list[dict], str]:
    """
    Sort, dedup, and validate S5 candles.

    Rejects: misaligned timestamps (t % 5 != 0), non-finite h/l/c values,
    conflicting duplicate timestamps.  Identical duplicates are collapsed.

    Returns (valid_candles, reason).  On any validation failure returns ([], reason).
    """
    seen: dict[int, dict] = {}
    for c in candles:
        try:
            t = int(c["t"])
        except (KeyError, TypeError, ValueError):
            return [], "malformed S5 candle: bad t field"
        if t % S5_SECONDS != 0:
            return [], f"misaligned S5 candle t={t} (not divisible by {S5_SECONDS})"
        for field in ("h", "l", "c"):
            val = c.get(field)
            if val is None or not math.isfinite(float(val)):
                return [], f"non-finite S5 {field} at t={t}"
        if t in seen:
            ex = seen[t]
            if ex["h"] != c["h"] or ex["l"] != c["l"]:
                return [], f"conflicting duplicate S5 at t={t}"
            continue  # identical duplicate — collapse
        seen[t] = c
    return sorted(seen.values(), key=lambda x: int(x["t"])), "ok"


# ── Resolution state ───────────────────────────────────────────────────────────

class ResolutionState(Enum):
    RESOLVED = auto()
    OPEN = auto()
    DATA_UNAVAILABLE = auto()


class ResolutionResult:
    __slots__ = ("state", "outcome", "result_pips", "exit_price", "closed_at_epoch", "reason")

    def __init__(
        self,
        state: ResolutionState,
        outcome: str = "",
        result_pips: float = 0.0,
        exit_price: float | None = None,
        closed_at_epoch: int | None = None,
        reason: str = "",
    ) -> None:
        self.state = state
        self.outcome = outcome
        self.result_pips = result_pips
        self.exit_price = exit_price
        self.closed_at_epoch = closed_at_epoch
        self.reason = reason


# ── Outcome resolution ─────────────────────────────────────────────────────────

def m15_touches_any_boundary(
    direction: str,
    entry: float,  # noqa: ARG001 — kept for symmetry; not used in touch detection
    sl: float,
    tp: float,
    candle: dict,
) -> bool:
    """True if the M15 candle's H/L contacts any boundary (TP or SL)."""
    h = candle.get("h")
    l = candle.get("l")
    if h is None or l is None:
        return False
    if direction == "BUY":
        return float(h) >= tp or float(l) <= sl
    return float(l) <= tp or float(h) >= sl


def check_s5_outcome(
    direction: str,
    entry: float,
    sl: float,
    tp: float,
    s5_candles: list[dict],
    pair: str,
) -> tuple[str, float, float, int, str] | None:
    """
    Scan S5 candles in order for the first TP or SL touch.

    Returns (outcome, result_pips, exit_price, closed_at_epoch, reason) or None.

    closed_at_epoch is the end of the first S5 candle proving the result (t + 5).

    Same-S5 TP+SL ambiguity → conservative LOSS with AMBIGUOUS_S5_STOP_FIRST.
    """
    for bar in s5_candles:
        h = float(bar["h"])
        l = float(bar["l"])
        candle_end = int(bar["t"]) + S5_SECONDS

        if direction == "BUY":
            tp_hit = h >= tp
            sl_hit = l <= sl
        else:
            tp_hit = l <= tp
            sl_hit = h >= sl

        if tp_hit and sl_hit:
            exit_price = sl
            result = pips(sl - entry if direction == "BUY" else entry - sl, pair)
            return "LOSS", result, exit_price, candle_end, "AMBIGUOUS_S5_STOP_FIRST"

        if tp_hit:
            exit_price = tp
            result = pips(tp - entry if direction == "BUY" else entry - tp, pair)
            return "WIN", result, exit_price, candle_end, "OANDA_S5_TP"

        if sl_hit:
            exit_price = sl
            result = pips(sl - entry if direction == "BUY" else entry - sl, pair)
            return "LOSS", result, exit_price, candle_end, "OANDA_S5_SL"

    return None


def resolve_signal_outcome(
    pair: str,
    direction: str,
    entry: float,
    sl: float,
    tp: float,
    tf_sec: int,
    effective_start_epoch: int,
    eval_end: int,
    threshold_epoch: int | None,
    completed_m15_candles: list[dict],
    oanda_token: str,
    oanda_url: str,
) -> ResolutionResult:
    """
    Resolve outcome by scanning completed M15 candles up to eval_end.

    eval_end = threshold_epoch when threshold reached; else latest completed M15 end.
    threshold_epoch = None when the 24 market-hour threshold has not been reached.

    DEFECT 1 fix: TP/SL is evaluated on every run, not deferred until threshold.
    DEFECT 4 fix: S5 range includes lookback for partial-entry candles; TIME_EXIT
      uses latest valid S5 (t+5 <= threshold) rather than requiring exact t==threshold-5;
      partial-entry with no post-entry S5 → no touch (not DATA_UNAVAILABLE).

    Returns ResolutionResult with state RESOLVED, OPEN, or DATA_UNAVAILABLE.
    """
    for candle in completed_m15_candles:
        t = int(candle["t"])
        candle_end = t + tf_sec

        proc_start = max(t, effective_start_epoch)
        proc_end = min(candle_end, eval_end)

        if proc_start >= proc_end:
            continue

        is_partial_start = proc_start > t
        is_threshold_candle = (
            threshold_epoch is not None and proc_end == threshold_epoch
        )
        is_threshold_at_m15_boundary = is_threshold_candle and (proc_end == candle_end)
        is_partial_end = is_threshold_candle and (proc_end < candle_end)

        need_s5 = is_partial_start or is_partial_end

        # When threshold == M15 candle boundary and whole-candle H/L shows no
        # TP/SL touch, S5 precision is not needed even for a partial-start
        # candle: the full-candle OHLC subsumes any sub-period H/L.
        if need_s5 and is_threshold_at_m15_boundary and not m15_touches_any_boundary(
            direction, entry, sl, tp, candle
        ):
            close_val = candle.get("c")
            if close_val is None:
                log(
                    f"M15 close unavailable for threshold boundary "
                    f"{pair} t={t} — DATA_UNAVAILABLE"
                )
                return ResolutionResult(state=ResolutionState.DATA_UNAVAILABLE)
            exit_price = float(close_val)
            result_pips_val = pips(
                (exit_price - entry) if direction == "BUY"
                else (entry - exit_price),
                pair,
            )
            log(
                f"TIME_EXIT {pair} {direction} entry={entry} "
                f"exit={exit_price} pips={result_pips_val:+.1f} "
                f"threshold={threshold_epoch} (M15 boundary, no touch)"
            )
            return ResolutionResult(
                state=ResolutionState.RESOLVED,
                outcome="TIME_EXIT",
                result_pips=result_pips_val,
                exit_price=exit_price,
                closed_at_epoch=threshold_epoch,
                reason="MAX_MARKET_SECONDS_TIME_EXIT",
            )

        if not need_s5:
            if not m15_touches_any_boundary(direction, entry, sl, tp, candle):
                if is_threshold_candle:
                    # Threshold exactly at M15 boundary; no touch → use M15 close
                    close_val = candle.get("c")
                    if close_val is None:
                        log(
                            f"M15 close unavailable for threshold boundary "
                            f"{pair} t={t} — DATA_UNAVAILABLE"
                        )
                        return ResolutionResult(state=ResolutionState.DATA_UNAVAILABLE)
                    exit_price = float(close_val)
                    result_pips_val = pips(
                        (exit_price - entry) if direction == "BUY"
                        else (entry - exit_price),
                        pair,
                    )
                    log(
                        f"TIME_EXIT {pair} {direction} entry={entry} "
                        f"exit={exit_price} pips={result_pips_val:+.1f} "
                        f"threshold={threshold_epoch} (M15 boundary, no touch)"
                    )
                    return ResolutionResult(
                        state=ResolutionState.RESOLVED,
                        outcome="TIME_EXIT",
                        result_pips=result_pips_val,
                        exit_price=exit_price,
                        closed_at_epoch=threshold_epoch,
                        reason="MAX_MARKET_SECONDS_TIME_EXIT",
                    )
                continue  # no touch, not threshold — scan next candle
            need_s5 = True  # M15 H/L touched a boundary → need S5 precision

        if need_s5:
            # DEFECT 4 fix: extend request back one M15 for partial-start candles
            # to maximise chance of finding S5 data near the entry boundary.
            s5_from = (
                max(0, proc_start - tf_sec) if is_partial_start else proc_start
            )
            s5_to = proc_end

            s5_raw, s5_reason = fetch_s5_candles(
                pair, s5_from, s5_to, oanda_token, oanda_url,
            )

            # Validate S5: misaligned / non-finite / conflicting → DATA_UNAVAILABLE
            if s5_raw:
                s5_validated, val_reason = validate_s5_candles(s5_raw)
                if not s5_validated:
                    log(
                        f"S5 validation failed for {pair} [{s5_from}, {s5_to}): "
                        f"{val_reason} — DATA_UNAVAILABLE"
                    )
                    return ResolutionResult(state=ResolutionState.DATA_UNAVAILABLE)
                s5_all = s5_validated
            else:
                s5_all = []

            # For TP/SL scan, only consider candles from proc_start onward
            s5_post_entry = [c for c in s5_all if int(c["t"]) >= proc_start]

            if not s5_post_entry:
                if is_partial_start and not is_threshold_candle:
                    # DEFECT 4 fix: sparse S5 in partial-entry candle → no touch
                    # attributed; do not treat as DATA_UNAVAILABLE
                    log(
                        f"S5 sparse for partial-entry {pair} "
                        f"[{proc_start}, {proc_end}): no post-entry S5 — "
                        f"no touch attributed, continuing"
                    )
                    continue
                # No S5 at all when needed → DATA_UNAVAILABLE
                log(
                    f"S5 unavailable for {pair} [{s5_from}, {s5_to}): "
                    f"{s5_reason} — DATA_UNAVAILABLE"
                )
                return ResolutionResult(state=ResolutionState.DATA_UNAVAILABLE)

            # TP/SL scan on post-entry S5 candles
            result = check_s5_outcome(direction, entry, sl, tp, s5_post_entry, pair)
            if result is not None:
                outcome, rp, ep, cat, reason = result
                log(
                    f"{outcome} {pair} {direction} entry={entry} "
                    f"exit={ep} pips={rp:+.1f} reason={reason} "
                    f"closed_at_epoch={cat}"
                )
                return ResolutionResult(
                    state=ResolutionState.RESOLVED,
                    outcome=outcome,
                    result_pips=rp,
                    exit_price=ep,
                    closed_at_epoch=cat,
                    reason=reason,
                )

            # No TP/SL in S5 — handle threshold TIME_EXIT if applicable
            if is_threshold_candle:
                if is_threshold_at_m15_boundary:
                    close_val = candle.get("c")
                    if close_val is None:
                        log(
                            f"M15 close unavailable for threshold boundary "
                            f"{pair} t={t} — DATA_UNAVAILABLE"
                        )
                        return ResolutionResult(state=ResolutionState.DATA_UNAVAILABLE)
                    exit_price = float(close_val)
                else:
                    # DEFECT 4 fix: use latest S5 where t+5 <= threshold_epoch
                    # rather than requiring exactly t == threshold_epoch - 5.
                    valid_exit = [
                        c for c in s5_all
                        if int(c["t"]) + S5_SECONDS <= threshold_epoch
                    ]
                    if not valid_exit:
                        log(
                            f"S5 coverage insufficient for threshold exit {pair}: "
                            f"no S5 candle ending at or before {threshold_epoch} "
                            f"in [{s5_from}, {s5_to}) — DATA_UNAVAILABLE"
                        )
                        return ResolutionResult(state=ResolutionState.DATA_UNAVAILABLE)
                    last_s5 = valid_exit[-1]
                    close_val = last_s5.get("c")
                    if close_val is None:
                        log(
                            f"S5 close None for threshold exit {pair} "
                            f"t={last_s5['t']} — DATA_UNAVAILABLE"
                        )
                        return ResolutionResult(state=ResolutionState.DATA_UNAVAILABLE)
                    exit_price = float(close_val)

                result_pips_val = pips(
                    (exit_price - entry) if direction == "BUY"
                    else (entry - exit_price),
                    pair,
                )
                log(
                    f"TIME_EXIT {pair} {direction} entry={entry} "
                    f"exit={exit_price} pips={result_pips_val:+.1f} "
                    f"threshold={threshold_epoch}"
                )
                return ResolutionResult(
                    state=ResolutionState.RESOLVED,
                    outcome="TIME_EXIT",
                    result_pips=result_pips_val,
                    exit_price=exit_price,
                    closed_at_epoch=threshold_epoch,
                    reason="MAX_MARKET_SECONDS_TIME_EXIT",
                )

    # Exhausted all candles without resolution
    if threshold_epoch is not None:
        # Threshold was reached but no candle returned a result — defensive guard
        return ResolutionResult(state=ResolutionState.DATA_UNAVAILABLE)
    return ResolutionResult(state=ResolutionState.OPEN)


# ── Signal action builder ──────────────────────────────────────────────────────

def parse_signal_created_at(raw_value: object) -> datetime:
    text = str(raw_value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    created = datetime.fromisoformat(text)
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    return created.astimezone(timezone.utc)


def mark_cancelled(sig: dict, reason: str, closed_at_epoch: int) -> dict:
    sig["predicted_outcome"] = "CANCELLED"
    sig["predicted_pips"] = 0.0
    sig["predicted_reason"] = reason
    sig["predicted_exit_price"] = None
    sig["predicted_closed_at_epoch"] = closed_at_epoch
    return sig


def prepare_signal_action(
    sig: dict,
    now_utc: datetime,
    now_epoch: int,
    max_age: int,
    hard_max_age: int,
    oanda_token: str = "",
    oanda_url: str = "",
) -> dict | None:
    """
    Decide outcome for a single ACTIVE signal.

    Ordering:
    1. Parse signal fields.
    2. Compute effective_start_epoch with microsecond precision (DEFECT 3 fix).
    3. Load completed eligible M15 candles.
    4. Compute market-time threshold.
    5. Set eval_end = threshold if reached, else latest completed M15 end.
    6. Resolve: scan ALL candles up to eval_end for TP/SL (DEFECT 1 fix).
    7. Handle RESOLVED / OPEN / DATA_UNAVAILABLE.
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

    if direction not in ("BUY", "SELL"):
        log(f"ERROR invalid direction={direction!r} for signal id={sig.get('id')}")
        return None
    for _name, _val in (("entry_price", entry), ("stop_loss", sl), ("take_profit", tp)):
        if not math.isfinite(_val):
            log(f"ERROR non-finite {_name}={_val!r} for signal id={sig.get('id')}")
            return None

    # DEFECT 3 fix: microsecond-exact ceil to S5 (avoids int() truncation)
    effective_start_epoch = ceil_to_s5_from_datetime(created)
    tf_sec = timeframe_seconds(tf)
    hold_seconds = max_age * 3600
    age_hours = (now_utc - created).total_seconds() / 3600.0
    sig["age_hours"] = age_hours

    candles, candle_reason = fetch_candles(
        pair, created, tf, now_epoch, effective_start_epoch,
    )

    if not candles:
        if age_hours >= hard_max_age:
            log(
                f"HARD_AGE_ESCAPE {pair} {tf} {direction} entry={entry} "
                f"age={age_hours:.1f}h hard_max={hard_max_age}h "
                f"reason={candle_reason} -> CANCELLED unresolved"
            )
            return mark_cancelled(sig, "HARD_AGE_UNRESOLVED_NO_OANDA_CANDLES", now_epoch)

        log(
            f"WARN: no usable OANDA candles for {pair} {tf} {direction} "
            f"entry={entry} age={age_hours:.1f}h reason={candle_reason} — leaving ACTIVE"
        )
        sig["predicted_outcome"] = "SKIP_NO_OANDA_CANDLES"
        sig["predicted_pips"] = 0.0
        sig["predicted_reason"] = candle_reason
        sig["predicted_exit_price"] = None
        sig["predicted_closed_at_epoch"] = None
        return None

    threshold_epoch = compute_threshold(candles, effective_start_epoch, hold_seconds, tf_sec)

    if threshold_epoch is None:
        # Threshold not yet reached; evaluate TP/SL up to the latest completed M15 end
        last_candle = candles[-1]
        eval_end = int(last_candle["t"]) + tf_sec
    else:
        eval_end = threshold_epoch

    resolution = resolve_signal_outcome(
        pair, direction, entry, sl, tp, tf_sec,
        effective_start_epoch, eval_end, threshold_epoch,
        candles, oanda_token, oanda_url,
    )

    if resolution.state == ResolutionState.OPEN:
        log(
            f"OPEN {pair} {tf} {direction} entry={entry} "
            f"age={age_hours:.1f}h — no TP/SL, market exposure < {max_age}h"
        )
        return None

    if resolution.state == ResolutionState.DATA_UNAVAILABLE:
        if age_hours >= hard_max_age:
            log(
                f"HARD_AGE_ESCAPE {pair} {tf} {direction} entry={entry} "
                f"age={age_hours:.1f}h — precision data unavailable -> CANCELLED"
            )
            return mark_cancelled(sig, "HARD_AGE_UNRESOLVED_NO_S5_DATA", now_epoch)
        log(
            f"WARN: precision data unavailable for {pair} {tf} {direction} "
            f"entry={entry} age={age_hours:.1f}h — leaving ACTIVE"
        )
        return None

    # ResolutionState.RESOLVED
    sig["predicted_outcome"] = resolution.outcome
    sig["predicted_pips"] = resolution.result_pips
    sig["predicted_reason"] = resolution.reason
    sig["predicted_exit_price"] = resolution.exit_price
    sig["predicted_closed_at_epoch"] = resolution.closed_at_epoch
    return sig


# ── Supabase write ─────────────────────────────────────────────────────────────

def close_signal(
    signal_id: str,
    status: str,
    result_pips: float,
    dry_run: bool,
    closed_at_epoch: int,
) -> None:
    closed_at_iso = iso_from_epoch(closed_at_epoch)
    body = {
        "status": status,
        "result_pips": round(result_pips, 1),
        "closed_at": closed_at_iso,
    }

    if dry_run:
        log(f"DRY-RUN: would update {signal_id} -> {status} {result_pips:+.1f} pips")
        return

    try:
        supabase_request("PATCH", f"signals?id=eq.{signal_id}", body)
        log(f"CLOSED {signal_id} -> {status} {result_pips:+.1f} pips")
    except Exception as exc:
        log(f"ERROR closing {signal_id}: {exc}")


# ── Safety gates ───────────────────────────────────────────────────────────────

def safety_gate(args: argparse.Namespace) -> bool:
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
        exit_price = sig.get("predicted_exit_price")
        exit_str = f"  exit={exit_price:.5f}" if exit_price is not None else ""
        reason_suffix = f"  reason={reason}" if reason else ""
        print(
            f"  {sig.get('pair', '?'):<8} {sig.get('direction', '?'):<5} "
            f"entry={entry_val:.5f}{exit_str}  "
            f"age={age_h:.1f}h  "
            f"outcome={outcome}  pips={pips_val:+.1f}"
            f"{reason_suffix}"
        )
    print(f"{'=' * 64}\n")
    if not dry_run:
        print("  Live writes begin in 3 seconds. CTRL+C to abort.")
        time.sleep(3)


# ── Entry point ────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "BotA Signal Closer v3.1 — dry-run by default.\n"
            "Live execution requires: --live --confirm CLOSE_SIGNALS --max-batch N"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--confirm", type=str, default="", metavar="CLOSE_SIGNALS")
    parser.add_argument("--max-batch", type=int, default=0, dest="max_batch", metavar="N")
    parser.add_argument("--allow-bulk", action="store_true", dest="allow_bulk")
    parser.add_argument("--pair", type=str, default=None)
    parser.add_argument("--max-age", type=int, default=None, dest="max_age")
    parser.add_argument("--hard-max-age", type=int, default=None, dest="hard_max_age")

    args = parser.parse_args()

    max_age = args.max_age if args.max_age is not None else MAX_AGE_HOURS
    hard_max_age = args.hard_max_age if args.hard_max_age is not None else HARD_MAX_AGE_HOURS
    dry_run = safety_gate(args)

    if not SUPABASE_KEY:
        log("ERROR: SUPABASE_SERVICE_KEY not set")
        sys.exit(1)

    server_epoch = compute_server_clock_epoch()
    if server_epoch <= 1_000_000_000:
        log("CLOCK server_clock_unavailable -> FAIL_CLOSED no Supabase writes")
        sys.exit(1)

    now_utc = datetime.fromtimestamp(server_epoch, timezone.utc)
    closed_at_iso = iso_from_epoch(server_epoch)

    log(f"CLOCK server_clock_ok epoch={server_epoch} utc={closed_at_iso}")
    log(
        f"Starting signal closer "
        f"(max_age={max_age}h, hard_max_age={hard_max_age}h, "
        f"dry_run={dry_run}, pair_filter={args.pair or 'ALL'})"
    )

    oanda_token = OANDA_API_TOKEN
    oanda_url = OANDA_API_URL

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
        action = prepare_signal_action(
            sig, now_utc, server_epoch, max_age, hard_max_age,
            oanda_token=oanda_token, oanda_url=oanda_url,
        )
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
        result_pips_val = float(sig["predicted_pips"])
        reason = str(sig.get("predicted_reason", ""))
        closed_at_epoch_val = int(sig.get("predicted_closed_at_epoch") or server_epoch)
        exit_price = sig.get("predicted_exit_price")

        log(
            f"{outcome} {pair} {direction} entry={entry} "
            f"exit={'none' if exit_price is None else f'{exit_price:.5f}'} "
            f"age={age_hours:.1f}h reason={reason} pips={result_pips_val:+.1f}"
        )

        if outcome == "CANCELLED":
            close_signal(sig_id, "CANCELLED", 0.0, dry_run, closed_at_epoch_val)
            cancelled += 1
        elif outcome in ("WIN", "LOSS", "TIME_EXIT"):
            close_signal(sig_id, "CLOSED", result_pips_val, dry_run, closed_at_epoch_val)
            closed += 1

    log(
        f"Done — closed={closed} cancelled={cancelled} "
        f"still_open={still_open} dry_run={dry_run}"
    )


if __name__ == "__main__":
    main()
