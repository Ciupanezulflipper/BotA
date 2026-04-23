#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import os
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

ROOT = Path.home() / "BotA"
LOG_DIR = ROOT / "logs"
DEFAULT_IN = LOG_DIR / "shadow_adx_scoring.jsonl"
DEFAULT_OUT = LOG_DIR / "shadow_outcome_sim.jsonl"

OANDA_API_URL = os.environ.get("OANDA_API_URL", "https://api-fxpractice.oanda.com").rstrip("/")
OANDA_API_TOKEN = os.environ.get("OANDA_API_TOKEN", "").strip()

# Realism controls
SPREAD_PIPS_DEFAULT = float(os.environ.get("SIM_SPREAD_PIPS_DEFAULT", "1.0"))
MIN_TP_PIPS = float(os.environ.get("SIM_MIN_TP_PIPS", "1.5"))


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def parse_iso8601(ts: str) -> Optional[datetime]:
    try:
        dt = datetime.fromisoformat(ts)
    except Exception:
        return None
    if dt.tzinfo is None:
        return None
    return dt.astimezone(timezone.utc)


def floor_to_m15(dt: datetime) -> datetime:
    dt_utc = dt.astimezone(timezone.utc)
    floored_minute = (dt_utc.minute // 15) * 15
    return dt_utc.replace(minute=floored_minute, second=0, microsecond=0)


def next_m15_candle_start(dt: datetime) -> datetime:
    return floor_to_m15(dt) + timedelta(minutes=15)


def pip_size(pair: str) -> float:
    p = pair.upper().strip()
    if p.endswith("JPY"):
        return 0.01
    if p in ("XAUUSD", "XAU/USD"):
        return 0.1
    if p in ("XAGUSD", "XAG/USD"):
        return 0.01
    return 0.0001


def pips(diff: float, pair: str) -> float:
    pip = pip_size(pair)
    return round(diff / pip, 1) if pip > 0 else 0.0


def pair_to_instrument(pair: str) -> str:
    pair_u = pair.upper().strip()
    if len(pair_u) != 6:
        raise ValueError(f"unsupported pair format: {pair}")
    return f"{pair_u[:3]}_{pair_u[3:]}"


def validate_https_url(url: str) -> str:
    raw = str(url or "").strip()
    parsed = urllib.parse.urlparse(raw)
    if parsed.scheme != "https" or not parsed.netloc:
        raise RuntimeError(f"unsupported url scheme/netloc: {raw!r}")
    return raw


@dataclass
class Candle:
    time: datetime
    high: float
    low: float


def safe_float(v: Any, default: float = 0.0) -> float:
    try:
        f = float(v)
        if math.isnan(f) or math.isinf(f):
            return default
        return f
    except Exception:
        return default


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            s = line.strip()
            if not s:
                continue
            try:
                obj = json.loads(s)
                if isinstance(obj, dict):
                    obj["_line_no"] = line_no
                    rows.append(obj)
            except Exception:
                rows.append({"_line_no": line_no, "_malformed_json": True, "_raw": s})
    return rows


def write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("a", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, separators=(",", ":"), ensure_ascii=False) + "\n")
            count += 1
    return count


def make_row_key(row: Dict[str, Any]) -> str:
    ts = str(row.get("timestamp", ""))
    pair = str(row.get("pair", ""))
    tf = str(row.get("timeframe", row.get("tf", "")))
    direction = str(row.get("direction_pre_gate", row.get("direction", "")))
    entry = str(row.get("entry", ""))
    return "|".join([ts, pair, tf, direction, entry])


def load_existing_keys(path: Path) -> set[str]:
    keys: set[str] = set()
    if not path.exists():
        return keys
    for row in load_jsonl(path):
        if row.get("source_key"):
            keys.add(str(row["source_key"]))
    return keys


def spread_pips_for_pair(_pair: str) -> float:
    # Conservative default unless user later wants pair-specific overrides.
    return SPREAD_PIPS_DEFAULT


def apply_spread_to_entry(entry: float, direction: str, pair: str) -> float:
    spread_price = spread_pips_for_pair(pair) * pip_size(pair)
    if direction.upper() == "BUY":
        return entry + spread_price
    if direction.upper() == "SELL":
        return entry - spread_price
    return entry


def oanda_fetch_candles(pair: str, tf: str, start_dt: datetime, end_dt: datetime) -> List[Candle]:
    if not OANDA_API_TOKEN:
        raise RuntimeError("OANDA_API_TOKEN missing")

    tf_u = tf.upper().strip()
    if tf_u != "M15":
        raise RuntimeError(f"unsupported timeframe for simulator: {tf}")

    if end_dt <= start_dt:
        raise RuntimeError(
            f"invalid candle window: end_dt<=start_dt ({start_dt.isoformat()} .. {end_dt.isoformat()})"
        )

    instrument = pair_to_instrument(pair)
    params = {
        "price": "M",
        "granularity": "M15",
        "from": start_dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "to": end_dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
    }

    base_url = validate_https_url(OANDA_API_URL)
    url = f"{base_url}/v3/instruments/{instrument}/candles?{urllib.parse.urlencode(params)}"
    validate_https_url(url)

    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {OANDA_API_TOKEN}",
            "Accept": "application/json",
            "User-Agent": "BotA-shadow-outcome-simulator/2.0",
        },
    )

    with urllib.request.urlopen(req, timeout=20) as resp:  # nosec B310
        payload = json.loads(resp.read().decode("utf-8"))

    raw = payload.get("candles", [])
    candles: List[Candle] = []
    for c in raw:
        try:
            t_raw = str(c.get("time", ""))
            dt = parse_iso8601(t_raw.replace("Z", "+00:00"))
            if dt is None:
                continue
            mid = c.get("mid", {}) or {}
            high = float(mid.get("h", 0.0))
            low = float(mid.get("l", 0.0))
            if high <= 0 or low <= 0:
                continue
            candles.append(Candle(time=dt, high=high, low=low))
        except Exception:
            continue

    candles.sort(key=lambda x: x.time)
    return candles


def simulate_tp_sl(
    direction: str,
    entry_real: float,
    sl: float,
    tp: float,
    candles: Iterable[Candle],
    pair: str,
) -> Tuple[str, float, Optional[str]]:
    direction_u = direction.upper()

    for candle in candles:
        h = candle.high
        l = candle.low

        if direction_u == "BUY":
            # Option B + pessimistic same-candle ordering
            if l <= sl:
                return "LOSS", -abs(pips(entry_real - sl, pair)), candle.time.isoformat()
            if h >= tp:
                return "WIN", abs(pips(tp - entry_real, pair)), candle.time.isoformat()

        elif direction_u == "SELL":
            if h >= sl:
                return "LOSS", -abs(pips(sl - entry_real, pair)), candle.time.isoformat()
            if l <= tp:
                return "WIN", abs(pips(entry_real - tp, pair)), candle.time.isoformat()

        else:
            return "SKIP_INVALID_DIRECTION", 0.0, None

    return "OPEN_EXPIRED", 0.0, None


def build_skip_result(
    row: Dict[str, Any],
    reason: str,
    started_at: datetime,
    notes: str = "",
) -> Dict[str, Any]:
    return {
        "sim_timestamp_utc": now_utc().isoformat(),
        "source_key": make_row_key(row),
        "source_line_no": row.get("_line_no"),
        "source_timestamp": row.get("timestamp"),
        "pair": row.get("pair"),
        "timeframe": row.get("timeframe", row.get("tf")),
        "direction": row.get("direction_pre_gate", row.get("direction")),
        "entry_raw": row.get("entry"),
        "entry_real": row.get("entry"),
        "sl": row.get("sl"),
        "tp": row.get("tp"),
        "status": reason,
        "result_pips": 0.0,
        "window_hours": None,
        "window_start_utc": started_at.isoformat(),
        "window_end_utc": None,
        "resolved_at_utc": None,
        "notes": notes or reason,
    }


# skipcq: PY-R1000
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default=str(DEFAULT_IN))
    ap.add_argument("--out", dest="outp", default=str(DEFAULT_OUT))
    ap.add_argument("--hours", type=int, default=24)
    ap.add_argument("--pair", default="")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--allow-duplicates", action="store_true")
    args = ap.parse_args()

    in_path = Path(args.inp)
    out_path = Path(args.outp)

    rows = load_jsonl(in_path)
    if not rows:
        print("NO_INPUT_ROWS")
        return 0

    existing_keys = set() if args.allow_duplicates else load_existing_keys(out_path)
    results: List[Dict[str, Any]] = []
    processed = 0
    duplicates_skipped = 0

    for row in rows:
        if args.limit and processed >= args.limit:
            break

        if row.get("_malformed_json"):
            results.append({
                "sim_timestamp_utc": now_utc().isoformat(),
                "source_key": f"MALFORMED|{row.get('_line_no')}",
                "source_line_no": row.get("_line_no"),
                "status": "SKIP_MALFORMED_JSON",
                "result_pips": 0.0,
                "notes": "malformed input JSONL line",
            })
            processed += 1
            continue

        pair = str(row.get("pair", "")).upper()
        tf = str(row.get("timeframe", row.get("tf", ""))).upper()
        direction = str(row.get("direction_pre_gate", row.get("direction", ""))).upper()
        ts = parse_iso8601(str(row.get("timestamp", "")))
        entry_raw = safe_float(row.get("entry", 0.0), 0.0)
        sl = safe_float(row.get("sl", 0.0), 0.0)
        tp = safe_float(row.get("tp", 0.0), 0.0)

        if args.pair and pair != args.pair.upper():
            continue

        source_key = make_row_key(row)
        if source_key in existing_keys:
            duplicates_skipped += 1
            continue

        if ts is None:
            results.append(build_skip_result(row, "SKIP_BAD_TIMESTAMP", now_utc()))
            processed += 1
            continue

        if pair not in {"EURUSD", "GBPUSD", "USDJPY", "EURJPY"}:
            results.append(build_skip_result(row, "SKIP_UNSUPPORTED_PAIR", ts))
            processed += 1
            continue

        if tf != "M15":
            results.append(build_skip_result(row, "SKIP_UNSUPPORTED_TIMEFRAME", ts))
            processed += 1
            continue

        if direction not in {"BUY", "SELL"}:
            results.append(build_skip_result(row, "SKIP_INVALID_DIRECTION", ts))
            processed += 1
            continue

        if entry_raw <= 0.0:
            results.append(build_skip_result(row, "SKIP_MISSING_ENTRY", ts))
            processed += 1
            continue

        if sl <= 0.0 or tp <= 0.0:
            results.append(build_skip_result(row, "SKIP_MISSING_SL_TP", ts))
            processed += 1
            continue

        entry_real = apply_spread_to_entry(entry_raw, direction, pair)
        tp_pips = abs(pips(tp - entry_real, pair))
        if tp_pips < MIN_TP_PIPS:
            results.append(build_skip_result(
                row,
                "SKIP_TP_TOO_SMALL",
                ts,
                notes=f"tp_pips={tp_pips} < min_tp_pips={MIN_TP_PIPS}",
            ))
            processed += 1
            continue

        replay_start_dt = next_m15_candle_start(ts)
        requested_end_dt = ts + timedelta(hours=args.hours)
        effective_end_dt = min(requested_end_dt, now_utc())

        if effective_end_dt <= replay_start_dt:
            results.append({
                "sim_timestamp_utc": now_utc().isoformat(),
                "source_key": source_key,
                "source_line_no": row.get("_line_no"),
                "source_timestamp": row.get("timestamp"),
                "pair": pair,
                "timeframe": tf,
                "direction": direction,
                "entry_raw": round(entry_raw, 5),
                "entry_real": round(entry_real, 5),
                "sl": round(sl, 5),
                "tp": round(tp, 5),
                "status": "SKIP_FUTURE_WINDOW",
                "result_pips": 0.0,
                "window_hours": args.hours,
                "window_start_utc": replay_start_dt.isoformat(),
                "window_end_utc": effective_end_dt.isoformat(),
                "resolved_at_utc": None,
                "notes": "effective_end_dt<=replay_start_dt after next-candle clamp",
            })
            processed += 1
            continue

        try:
            candles = oanda_fetch_candles(pair, tf, replay_start_dt, effective_end_dt)
        except Exception as ex:
            results.append({
                "sim_timestamp_utc": now_utc().isoformat(),
                "source_key": source_key,
                "source_line_no": row.get("_line_no"),
                "source_timestamp": row.get("timestamp"),
                "pair": pair,
                "timeframe": tf,
                "direction": direction,
                "entry_raw": round(entry_raw, 5),
                "entry_real": round(entry_real, 5),
                "sl": round(sl, 5),
                "tp": round(tp, 5),
                "status": "ERROR_FETCH_CANDLES",
                "result_pips": 0.0,
                "window_hours": args.hours,
                "window_start_utc": replay_start_dt.isoformat(),
                "window_end_utc": effective_end_dt.isoformat(),
                "resolved_at_utc": None,
                "notes": str(ex),
            })
            processed += 1
            continue

        outcome, result_pips, resolved_at = simulate_tp_sl(direction, entry_real, sl, tp, candles, pair)
        results.append({
            "sim_timestamp_utc": now_utc().isoformat(),
            "source_key": source_key,
            "source_line_no": row.get("_line_no"),
            "source_timestamp": row.get("timestamp"),
            "pair": pair,
            "timeframe": tf,
            "direction": direction,
            "entry_raw": round(entry_raw, 5),
            "entry_real": round(entry_real, 5),
            "sl": round(sl, 5),
            "tp": round(tp, 5),
            "status": outcome,
            "result_pips": result_pips,
            "window_hours": args.hours,
            "window_start_utc": replay_start_dt.isoformat(),
            "window_end_utc": effective_end_dt.isoformat(),
            "resolved_at_utc": resolved_at,
            "notes": "",
        })
        processed += 1

    written = write_jsonl(out_path, results)
    summary = {
        "input_file": str(in_path),
        "output_file": str(out_path),
        "processed_rows": processed,
        "written_rows": written,
        "duplicates_skipped": duplicates_skipped,
    }
    print(json.dumps(summary, separators=(",", ":"), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
