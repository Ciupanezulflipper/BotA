#!/usr/bin/env python3
"""
BotA Signal Resolution Engine
==============================

Self-contained resolution pipeline extracted from signal_closer.py.
Provides the full TP/SL/TIME_EXIT determination logic, OANDA S5 fetching,
S5 candle validation, and typed outcome classes.

Public API consumed by signal_closer.py:
  resolve_signal_outcome, fetch_s5_candles, validate_s5_candles,
  ResolutionState, ResolutionResult, check_s5_outcome,
  m15_touches_any_boundary, log, pip_size, pips, oanda_instrument,
  S5_SECONDS
"""

from __future__ import annotations

import http.client
import json
import math
import pathlib
import urllib.parse
from datetime import datetime, timezone
from enum import Enum, auto

ROOT = pathlib.Path(__file__).resolve().parent.parent
LOG_FILE = ROOT / "logs" / "signal_closer.log"

S5_SECONDS = 5


# ── Logging ────────────────────────────────────────────────────────────────────

def log(msg: str) -> None:
    """Print a timestamped log line and append it to LOG_FILE."""
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
    """Return 0.01 for JPY pairs, 0.0001 for all others."""
    return 0.01 if "JPY" in pair.upper() else 0.0001


def pips(diff: float, pair: str) -> float:
    """Convert a price difference to pips, rounded to one decimal place."""
    return round(diff / pip_size(pair), 1)


# ── OANDA instrument name ─────────────────────────────────────────────────────

def oanda_instrument(pair: str) -> str:
    """Convert 'EURUSD' → 'EUR_USD' for the OANDA v3 API."""
    pair = pair.upper().replace("_", "")
    if len(pair) == 6:
        return pair[:3] + "_" + pair[3:]
    return pair


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


# ── OANDA S5 fetcher helpers ───────────────────────────────────────────────────

def _validate_s5_inputs(
    token: str,
    from_epoch: int,
    to_epoch: int,
    base_url: str,
) -> str | None:
    """Return an error string if inputs are invalid, else None."""
    if not token:
        return "OANDA_API_TOKEN not set"
    if from_epoch >= to_epoch:
        return f"invalid S5 range from={from_epoch} >= to={to_epoch}"
    parsed = urllib.parse.urlsplit(base_url)
    if parsed.scheme != "https":
        return "S5 fetch requires HTTPS base URL"
    if not parsed.hostname:
        return "S5 fetch: missing hostname in base URL"
    if parsed.username or parsed.password:
        return "S5 fetch: embedded credentials in base URL rejected"
    return None


def _build_s5_path(pair: str, from_iso: str, to_iso: str, base_url: str) -> tuple[str, int | None, str]:
    """Return (host, port, request_path) for the OANDA S5 candles endpoint."""
    parsed = urllib.parse.urlsplit(base_url)
    host = parsed.hostname or ""
    port = parsed.port
    base_path = parsed.path.rstrip("/") if parsed.path else ""
    instrument = oanda_instrument(pair)
    params = f"granularity=S5&price=M&from={from_iso}&to={to_iso}&includeFirst=true"
    return host, port, f"{base_path}/v3/instruments/{instrument}/candles?{params}"


def _execute_s5_http(
    host: str, port: int | None, path: str, token: str
) -> tuple[object, str | None]:
    """Execute the HTTPS GET and decode JSON. Returns (data, None) or (None, error)."""
    conn = http.client.HTTPSConnection(host, port, timeout=20)
    try:
        conn.request("GET", path, headers={
            "Authorization": f"Bearer {token}",
            "Accept-Datetime-Format": "UNIX",
        })
        resp = conn.getresponse()
        if resp.status < 200 or resp.status >= 300:
            return None, f"S5 fetch HTTP {resp.status}"
        return json.loads(resp.read().decode("utf-8")), None
    except Exception as exc:
        return None, f"S5 fetch {type(exc).__name__}: {str(exc)[:80]}"
    finally:
        conn.close()


def _parse_s5_response(data: object) -> tuple[list, str | None]:
    """Validate response shape. Returns (candles_raw, None) or ([], error)."""
    if not isinstance(data, dict):
        return [], "S5 response is not a JSON object"
    candles_raw = data.get("candles", [])
    if not isinstance(candles_raw, list):
        return [], "S5 candles field is not a list"
    return candles_raw, None


def _convert_s5_candles(candles_raw: list, from_epoch: int, to_epoch: int) -> list[dict]:
    """Filter complete in-range candles and build {t,o,h,l,c} dicts."""
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
    return candles


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
    err = _validate_s5_inputs(token, from_epoch, to_epoch, base_url)
    if err:
        return [], err

    from_iso = datetime.fromtimestamp(from_epoch, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    to_iso = datetime.fromtimestamp(to_epoch, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    host, port, path = _build_s5_path(pair, from_iso, to_iso, base_url)

    data, req_err = _execute_s5_http(host, port, path, token)
    if req_err:
        return [], req_err

    candles_raw, shape_err = _parse_s5_response(data)
    if shape_err:
        return [], shape_err

    candles = _convert_s5_candles(candles_raw, from_epoch, to_epoch)
    if not candles:
        return [], f"no complete S5 candles for {pair} [{from_iso}, {to_iso})"

    validated, val_reason = validate_s5_candles(candles)
    if not validated:
        return [], f"S5 validation: {val_reason}"
    return validated, "ok"


# ── Resolution state ───────────────────────────────────────────────────────────

class ResolutionState(Enum):
    """Outcome category returned by the signal resolution engine."""

    RESOLVED = auto()
    OPEN = auto()
    DATA_UNAVAILABLE = auto()


class ResolutionResult:
    """Immutable result produced by resolve_signal_outcome."""

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
        """Initialise all result fields."""
        self.state = state
        self.outcome = outcome
        self.result_pips = result_pips
        self.exit_price = exit_price
        self.closed_at_epoch = closed_at_epoch
        self.reason = reason


# ── Outcome resolution helpers ─────────────────────────────────────────────────

def m15_touches_any_boundary(
    direction: str,
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


def _make_m15_time_exit(
    direction: str,
    entry: float,
    pair: str,
    candle: dict,
    threshold_int: int,
) -> ResolutionResult:
    """Build a TIME_EXIT ResolutionResult from the M15 candle close price."""
    close_val = candle.get("c")
    if close_val is None:
        log(
            f"M15 close unavailable for threshold boundary "
            f"{pair} t={candle.get('t')} — DATA_UNAVAILABLE"
        )
        return ResolutionResult(state=ResolutionState.DATA_UNAVAILABLE)
    exit_price = float(close_val)
    result_pips_val = pips(
        (exit_price - entry) if direction == "BUY" else (entry - exit_price), pair
    )
    log(
        f"TIME_EXIT {pair} {direction} entry={entry} "
        f"exit={exit_price} pips={result_pips_val:+.1f} "
        f"threshold={threshold_int} (M15 boundary, no touch)"
    )
    return ResolutionResult(
        state=ResolutionState.RESOLVED,
        outcome="TIME_EXIT",
        result_pips=result_pips_val,
        exit_price=exit_price,
        closed_at_epoch=threshold_int,
        reason="MAX_MARKET_SECONDS_TIME_EXIT",
    )


def _select_s5_exit_price(
    candle: dict,
    is_threshold_at_m15_boundary: bool,
    s5_all: list[dict],
    threshold_int: int,
    pair: str,
    s5_from: int,
    s5_to: int,
) -> tuple[float | None, ResolutionResult | None]:
    """
    Select the TIME_EXIT price for a threshold candle.

    Returns (exit_price, None) on success or (None, error_result) on failure.

    For M15-boundary thresholds: use the M15 candle close.
    For mid-candle thresholds: use the latest S5 close where t+5 <= threshold_int.
    """
    if is_threshold_at_m15_boundary:
        close_val = candle.get("c")
        if close_val is None:
            log(
                f"M15 close unavailable for threshold boundary "
                f"{pair} t={candle.get('t')} — DATA_UNAVAILABLE"
            )
            return None, ResolutionResult(state=ResolutionState.DATA_UNAVAILABLE)
        return float(close_val), None

    # DEFECT 4 fix: use latest S5 where t+5 <= threshold_int
    valid_exit = [c for c in s5_all if int(c["t"]) + S5_SECONDS <= threshold_int]
    if not valid_exit:
        log(
            f"S5 coverage insufficient for threshold exit {pair}: "
            f"no S5 candle ending at or before {threshold_int} "
            f"in [{s5_from}, {s5_to}) — DATA_UNAVAILABLE"
        )
        return None, ResolutionResult(state=ResolutionState.DATA_UNAVAILABLE)
    last_s5 = valid_exit[-1]
    close_val = last_s5.get("c")
    if close_val is None:
        log(
            f"S5 close None for threshold exit {pair} "
            f"t={last_s5['t']} — DATA_UNAVAILABLE"
        )
        return None, ResolutionResult(state=ResolutionState.DATA_UNAVAILABLE)
    return float(close_val), None


# ── Candle-level resolution helpers ────────────────────────────────────────────

def _resolve_with_s5(
    candle: dict,
    pair: str,
    direction: str,
    entry: float,
    sl: float,
    tp: float,
    proc_start: int,
    proc_end: int,
    is_partial_start: bool,
    is_threshold_candle: bool,
    is_threshold_at_m15_boundary: bool,
    tf_sec: int,
    threshold_epoch: int | None,
    oanda_token: str,
    oanda_url: str,
) -> ResolutionResult | None:
    """
    Fetch S5 data for one candle window, scan for TP/SL, handle threshold TIME_EXIT.

    Returns ResolutionResult when outcome is determined (including DATA_UNAVAILABLE).
    Returns None to signal "continue scanning the next M15 candle."
    """
    # DEFECT 4 fix: extend request back one M15 for partial-start candles.
    s5_from = max(0, proc_start - tf_sec) if is_partial_start else proc_start
    s5_to = proc_end

    s5_raw, s5_reason = fetch_s5_candles(pair, s5_from, s5_to, oanda_token, oanda_url)

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

    s5_post_entry = [c for c in s5_all if int(c["t"]) >= proc_start]

    if not s5_post_entry:
        if is_partial_start and not is_threshold_candle:
            # DEFECT 4 fix: sparse S5 for partial-entry → no touch attributed.
            log(
                f"S5 sparse for partial-entry {pair} "
                f"[{proc_start}, {proc_end}): no post-entry S5 — "
                f"no touch attributed, continuing"
            )
            return None
        log(
            f"S5 unavailable for {pair} [{s5_from}, {s5_to}): "
            f"{s5_reason} — DATA_UNAVAILABLE"
        )
        return ResolutionResult(state=ResolutionState.DATA_UNAVAILABLE)

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

    if not is_threshold_candle:
        return None

    # Threshold candle with no TP/SL hit → TIME_EXIT pricing.
    # is_threshold_candle=True guarantees threshold_epoch is not None;
    # the guard below is defensive for the logically unreachable None case.
    if threshold_epoch is None:
        return ResolutionResult(state=ResolutionState.DATA_UNAVAILABLE)
    threshold_int: int = threshold_epoch

    exit_price, err = _select_s5_exit_price(
        candle, is_threshold_at_m15_boundary,
        s5_all, threshold_int, pair, s5_from, s5_to,
    )
    if err is not None:
        return err

    assert exit_price is not None
    result_pips_val = pips(
        (exit_price - entry) if direction == "BUY" else (entry - exit_price),
        pair,
    )
    log(
        f"TIME_EXIT {pair} {direction} entry={entry} "
        f"exit={exit_price} pips={result_pips_val:+.1f} "
        f"threshold={threshold_int}"
    )
    return ResolutionResult(
        state=ResolutionState.RESOLVED,
        outcome="TIME_EXIT",
        result_pips=result_pips_val,
        exit_price=exit_price,
        closed_at_epoch=threshold_int,
        reason="MAX_MARKET_SECONDS_TIME_EXIT",
    )


def _resolve_single_candle(
    candle: dict,
    pair: str,
    direction: str,
    entry: float,
    sl: float,
    tp: float,
    tf_sec: int,
    effective_start_epoch: int,
    eval_end: int,
    threshold_epoch: int | None,
    oanda_token: str,
    oanda_url: str,
) -> ResolutionResult | None:
    """
    Evaluate one M15 candle against the lifecycle contract.

    Returns ResolutionResult when a conclusive outcome is determined.
    Returns None to continue scanning the next candle.
    """
    t = int(candle["t"])
    candle_end = t + tf_sec
    proc_start = max(t, effective_start_epoch)
    proc_end = min(candle_end, eval_end)

    if proc_start >= proc_end:
        return None

    is_partial_start = proc_start > t
    is_threshold_candle = threshold_epoch is not None and proc_end == threshold_epoch
    is_threshold_at_m15_boundary = is_threshold_candle and proc_end == candle_end
    is_partial_end = is_threshold_candle and proc_end < candle_end
    need_s5 = is_partial_start or is_partial_end

    # When threshold == M15 boundary and whole-candle H/L shows no touch,
    # the full-candle OHLC subsumes any sub-period H/L; S5 is unnecessary.
    if need_s5 and is_threshold_at_m15_boundary and not m15_touches_any_boundary(
        direction, sl, tp, candle
    ):
        if threshold_epoch is None:  # defensive guard; logically unreachable
            return ResolutionResult(state=ResolutionState.DATA_UNAVAILABLE)
        return _make_m15_time_exit(direction, entry, pair, candle, threshold_epoch)

    if not need_s5 and not m15_touches_any_boundary(direction, sl, tp, candle):
        if is_threshold_candle:
            if threshold_epoch is None:  # defensive guard; logically unreachable
                return ResolutionResult(state=ResolutionState.DATA_UNAVAILABLE)
            return _make_m15_time_exit(direction, entry, pair, candle, threshold_epoch)
        return None  # no touch, not threshold → scan next candle
    # M15 H/L touched a boundary → need S5 precision (fall through)

    return _resolve_with_s5(
        candle, pair, direction, entry, sl, tp,
        proc_start, proc_end, is_partial_start, is_threshold_candle,
        is_threshold_at_m15_boundary, tf_sec, threshold_epoch,
        oanda_token, oanda_url,
    )


# ── Outcome resolution ─────────────────────────────────────────────────────────

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
        result = _resolve_single_candle(
            candle, pair, direction, entry, sl, tp, tf_sec,
            effective_start_epoch, eval_end, threshold_epoch,
            oanda_token, oanda_url,
        )
        if result is not None:
            return result

    if threshold_epoch is not None:
        return ResolutionResult(state=ResolutionState.DATA_UNAVAILABLE)
    return ResolutionResult(state=ResolutionState.OPEN)
