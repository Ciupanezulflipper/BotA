#!/usr/bin/env python3
"""
tools/rejected_shadow_tracker.py
BotA v1.1 — Rejected Candidate Shadow Tracker

Purpose:
- Reads logs/alerts.csv for rejected BUY/SELL candidates.
- Tracks score-gated / H1-neutral / H1-vetoed candidates.
- Fetches OANDA M15 candles after the candidate timestamp.
- Simulates TP/SL outcome without touching live signals, Telegram, or Supabase.

Safety:
- No Telegram sends.
- No signals table writes.
- No strategy/scoring/threshold changes.
- Output only: logs/rejected_shadow_outcomes.jsonl

Important corrections vs draft:
- OPEN_PENDING rows are NOT treated as final; they can be rechecked later.
- Final dedup only applies to TP_HIT / SL_HIT / EXPIRED_NO_HIT.
- Same-candle policy is TP_FIRST_LIVE_MATCH to match BotA closer audit.
- Candidate key includes pair, timeframe, direction, timestamp, entry, SL, TP.
- Parses/stores both filter_reason and reasons columns.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
import email.utils
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


ROOT = Path(__file__).resolve().parents[1]
ALERTS_CSV = ROOT / "logs" / "alerts.csv"
OUTPUT_JSONL = ROOT / "logs" / "rejected_shadow_outcomes.jsonl"

FINAL_STATUSES = {"TP_HIT", "SL_HIT", "EXPIRED_NO_HIT"}
SAME_CANDLE_POLICY = "TP_FIRST_LIVE_MATCH"


def device_device_now_utc() -> datetime:
    return datetime.now(timezone.utc)


def server_device_now_utc() -> Tuple[Optional[datetime], str]:
    """
    Return trusted server UTC from HTTP Date headers.
    This avoids Android/ship clock drift.
    """
    urls = [
        "https://www.google.com",
        "https://api-fxpractice.oanda.com",
        "https://www.cloudflare.com",
        "https://query1.finance.yahoo.com",
    ]

    values: List[datetime] = []
    errors: List[str] = []

    for url in urls:
        try:
            req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "BotA-clock/1.0"})
            with urllib.request.urlopen(req, timeout=8) as response:  # nosec B310
                date_header = response.headers.get("Date", "")
        except Exception as exc:
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "BotA-clock/1.0"})
                with urllib.request.urlopen(req, timeout=8) as response:  # nosec B310
                    date_header = response.headers.get("Date", "")
            except Exception as exc2:
                errors.append(f"{url}:{type(exc2).__name__}")
                continue

        if not date_header:
            errors.append(f"{url}:no_date")
            continue

        try:
            dt = email.utils.parsedate_to_datetime(date_header)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            values.append(dt.astimezone(timezone.utc))
        except Exception:
            errors.append(f"{url}:bad_date")

    if not values:
        return None, "server_clock_unavailable:" + ",".join(errors[:4])

    values.sort()
    spread = (values[-1] - values[0]).total_seconds()
    if len(values) >= 2 and spread > 120:
        return None, f"server_clock_spread_too_wide:{spread:.0f}s"

    return values[len(values) // 2], f"server_clock_ok:count={len(values)} spread={spread:.0f}s"


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        f = float(str(value).strip())
        if math.isnan(f) or math.isinf(f):
            return default
        return f
    except Exception:
        return default


def parse_bool_rejected(value: Any) -> bool:
    s = str(value or "").strip().lower()
    if s in {"false", "0", "no", "none", ""}:
        return False
    return True


def parse_dt(value: str) -> Optional[datetime]:
    raw = str(value or "").strip()
    if not raw:
        return None

    # Handles:
    # 2026-05-08T23:45:29+1000
    # 2026-05-08T23:45:29+10:00
    # 2026-05-08T13:45:29Z
    try:
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def floor_to_m15(dt: datetime) -> datetime:
    d = dt.astimezone(timezone.utc)
    minute = (d.minute // 15) * 15
    return d.replace(minute=minute, second=0, microsecond=0)


def next_m15_after(dt: datetime) -> datetime:
    return floor_to_m15(dt) + timedelta(minutes=15)


def pip_size(pair: str) -> float:
    p = pair.upper().strip()
    if p.endswith("JPY"):
        return 0.01
    if p in {"XAUUSD", "XAU/USD"}:
        return 0.1
    if p in {"XAGUSD", "XAG/USD"}:
        return 0.01
    return 0.0001


def pair_to_instrument(pair: str) -> str:
    p = pair.upper().replace("/", "").strip()
    if len(p) != 6:
        raise ValueError(f"unsupported pair format: {pair}")
    return f"{p[:3]}_{p[3:]}"


def load_env_files() -> None:
    """
    Minimal .env parser. Does not source shell files.
    Keeps existing OS env values if already set.
    """
    for env_file in [
        ROOT / ".env.runtime",
        ROOT / ".env",
        ROOT / "config" / "strategy.env",
    ]:
        if not env_file.exists():
            continue

        for line in env_file.read_text(errors="ignore").splitlines():
            s = line.strip()
            if not s or s.startswith("#") or "=" not in s:
                continue
            if s.startswith("export "):
                s = s[7:].strip()
            key, value = s.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


def fetch_oanda_m15(
    pair: str,
    start_dt: datetime,
    end_dt: datetime,
    token: str,
    base_url: str,
) -> Tuple[List[Tuple[datetime, float, float, float]], Optional[str]]:
    if end_dt <= start_dt:
        return [], "invalid_window_end_before_start"

    instrument = pair_to_instrument(pair)
    params = {
        "price": "M",
        "granularity": "M15",
        "from": start_dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "to": end_dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
    }

    url = f"{base_url.rstrip('/')}/v3/instruments/{instrument}/candles?{urllib.parse.urlencode(params)}"

    try:
        req = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
                "User-Agent": "BotA-rejected-shadow-tracker/1.1",
            },
        )
        with urllib.request.urlopen(req, timeout=20) as response:  # nosec B310
            payload = json.loads(response.read().decode("utf-8"))

        candles: List[Tuple[datetime, float, float, float]] = []
        for c in payload.get("candles", []):
            if not c.get("complete", True):
                continue
            mid = c.get("mid", {}) or {}
            dt = parse_dt(str(c.get("time", "")))
            high = safe_float(mid.get("h"), 0.0)
            low = safe_float(mid.get("l"), 0.0)
            close = safe_float(mid.get("c"), 0.0)
            if dt is None or high <= 0 or low <= 0:
                continue
            candles.append((dt, high, low, close))

        candles.sort(key=lambda x: x[0])
        return candles, None

    except Exception as exc:
        return [], f"{type(exc).__name__}: {exc}"


def simulate_tp_first(
    direction: str,
    entry: float,
    sl: float,
    tp: float,
    candles: Iterable[Tuple[datetime, float, float, float]],
    pair: str,
) -> Tuple[str, float, Optional[str]]:
    """
    TP-first same-candle policy to match prior BotA closer audit.
    """
    ps = pip_size(pair)
    d = direction.upper()

    for dt, high, low, _close in candles:
        if d == "BUY":
            if high >= tp:
                return "TP_HIT", round((tp - entry) / ps, 1), dt.isoformat()
            if low <= sl:
                return "SL_HIT", round((sl - entry) / ps, 1), dt.isoformat()

        elif d == "SELL":
            if low <= tp:
                return "TP_HIT", round((entry - tp) / ps, 1), dt.isoformat()
            if high >= sl:
                return "SL_HIT", round((entry - sl) / ps, 1), dt.isoformat()

    return "NO_HIT", 0.0, None


def read_existing_final_keys(path: Path) -> set[str]:
    """
    Only final outcomes dedup.
    OPEN_PENDING / fetch errors are intentionally re-checkable.
    """
    keys: set[str] = set()
    if not path.exists():
        return keys

    for line in path.read_text(errors="ignore").splitlines():
        s = line.strip()
        if not s:
            continue
        try:
            obj = json.loads(s)
        except Exception:
            continue
        if obj.get("outcome") in FINAL_STATUSES and obj.get("key"):
            keys.add(str(obj["key"]))
    return keys


def row_get(row: Dict[str, str], keys: List[str], fallback_index: Optional[int] = None, raw_row: Optional[List[str]] = None) -> str:
    for key in keys:
        if key in row and row[key] is not None:
            return str(row[key])
    if fallback_index is not None and raw_row is not None and fallback_index < len(raw_row):
        return str(raw_row[fallback_index])
    return ""


def load_alert_rows() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []

    with ALERTS_CSV.open(newline="", encoding="utf-8", errors="ignore") as f:
        sample = f.readline()
        f.seek(0)

        has_header = any(x in sample.lower() for x in ["timestamp", "pair", "direction", "score"])

        if has_header:
            reader = csv.DictReader(f)
            for raw in reader:
                rows.append({"dict": dict(raw), "raw": []})
        else:
            reader2 = csv.reader(f)
            for raw_row in reader2:
                rows.append({"dict": {}, "raw": raw_row})

    return rows


def make_key(pair: str, tf: str, direction: str, ts: datetime, entry: float, sl: float, tp: float) -> str:
    return "|".join([
        pair.upper(),
        tf.upper(),
        direction.upper(),
        ts.isoformat(),
        f"{entry:.6f}",
        f"{sl:.6f}",
        f"{tp:.6f}",
    ])


def build_candidates(score_min: float, lookback_hours: int) -> List[Dict[str, Any]]:
    server_now, clock_status = server_device_now_utc()
    if server_now is None:
        raise RuntimeError(clock_status)

    cutoff = server_now - timedelta(hours=lookback_hours)
    future_grace = server_now + timedelta(minutes=5)
    candidates: List[Dict[str, Any]] = []

    for wrapped in load_alert_rows():
        drow: Dict[str, str] = wrapped["dict"]
        rrow: List[str] = wrapped["raw"]

        ts_raw = row_get(drow, ["timestamp", "ts", "time"], 0, rrow)
        pair = row_get(drow, ["pair", "symbol"], 1, rrow).upper().replace("/", "")
        tf = row_get(drow, ["tf", "timeframe"], 2, rrow).upper()
        direction = row_get(drow, ["direction", "dir"], 3, rrow).upper()

        if tf != "M15" or direction not in {"BUY", "SELL"}:
            continue

        score = safe_float(row_get(drow, ["score"], 4, rrow), -1.0)
        entry = safe_float(row_get(drow, ["entry"], 6, rrow), 0.0)
        sl = safe_float(row_get(drow, ["sl"], 7, rrow), 0.0)
        tp = safe_float(row_get(drow, ["tp"], 8, rrow), 0.0)
        rejected_raw = row_get(drow, ["filter_rejected", "rejected"], 10, rrow)
        filter_reason = row_get(drow, ["filter_reason", "filter_reasons", "filters", "filter_str"], 11, rrow)
        reasons = row_get(drow, ["reasons", "reason"], 12, rrow)

        if score < score_min or entry <= 0 or sl <= 0 or tp <= 0:
            continue

        if not parse_bool_rejected(rejected_raw):
            continue

        ts = parse_dt(ts_raw)
        if ts is None or ts < cutoff:
            continue

        # If alert timestamp is ahead of trusted server UTC, do not ask OANDA
        # for future candles. This can happen during ship/Android clock drift.
        if ts > future_grace:
            continue

        combined = f"{filter_reason} | {reasons}"
        key = make_key(pair, tf, direction, ts, entry, sl, tp)

        candidates.append({
            "key": key,
            "timestamp": ts,
            "pair": pair,
            "tf": tf,
            "direction": direction,
            "score": score,
            "entry": entry,
            "sl": sl,
            "tp": tp,
            "filter_reason": filter_reason,
            "reasons": reasons,
            "combined_reason": combined,
            "h1_neutral": "H1_trend_neutral" in combined and "vetoed" not in combined,
            "h1_veto": "H1_trend_neutral" in combined and "vetoed" in combined,
            "score_gate": "score<" in combined,
            "rr_gate": "rr<" in combined or "rr<=0" in combined,
        })

    candidates.sort(key=lambda x: x["timestamp"])
    return candidates


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--score-min", type=float, default=55.0)
    parser.add_argument("--lookback-hours", type=int, default=48)
    parser.add_argument("--outcome-hours", type=int, default=24)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    load_env_files()

    if not ALERTS_CSV.exists():
        print(f"ERROR: {ALERTS_CSV} not found")
        return 1

    token = os.environ.get("OANDA_API_TOKEN", "").strip()
    base_url = os.environ.get("OANDA_API_URL", "https://api-fxpractice.oanda.com").strip().rstrip("/")

    server_now, clock_status = server_device_now_utc()
    if server_now is None:
        print(f"ERROR: {clock_status}")
        return 1

    print(f"trusted_server_utc={server_now.isoformat()}")
    print(f"server_clock_status={clock_status}")

    candidates = build_candidates(args.score_min, args.lookback_hours)
    final_keys = read_existing_final_keys(OUTPUT_JSONL)
    candidates = [c for c in candidates if c["key"] not in final_keys]

    print(f"score_min={args.score_min}")
    print(f"lookback_hours={args.lookback_hours}")
    print(f"outcome_hours={args.outcome_hours}")
    print(f"candidate_count={len(candidates)}")
    print(f"existing_final_keys={len(final_keys)}")
    print(f"output={OUTPUT_JSONL}")
    print(f"same_candle_policy={SAME_CANDLE_POLICY}")

    if args.dry_run:
        print("")
        print("DRY_RUN=YES")
        print("FETCH_CANDLES=NO")
        print("WRITE_OUTPUT=NO")
        for c in candidates[:80]:
            ts = c["timestamp"].strftime("%Y-%m-%dT%H:%MZ")
            print(
                f"{ts} {c['pair']} {c['direction']} "
                f"score={c['score']:.1f} "
                f"h1_neutral={c['h1_neutral']} "
                f"h1_veto={c['h1_veto']} "
                f"score_gate={c['score_gate']} "
                f"filter={str(c['filter_reason'])[:80]}"
            )
        if len(candidates) > 80:
            print(f"... truncated {len(candidates) - 80} more")
        print("FILES_REPLACED=YES | PRODUCTION_CHANGED=NO | STRATEGY_CHANGED=NO | OUTPUT_WRITTEN=NO")
        return 0

    if not token:
        print("ERROR: OANDA_API_TOKEN not available from env/.env.runtime/.env/config/strategy.env")
        return 1

    if not candidates:
        print("nothing new to track")
        print("FILES_REPLACED=YES | PRODUCTION_CHANGED=NO | STRATEGY_CHANGED=NO | OUTPUT_WRITTEN=NO")
        return 0

    OUTPUT_JSONL.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    current = server_now

    with OUTPUT_JSONL.open("a", encoding="utf-8") as out:
        for c in candidates:
            ts = c["timestamp"]
            start_dt = next_m15_after(ts)
            requested_end = ts + timedelta(hours=args.outcome_hours)
            end_dt = min(current, requested_end)

            candles, fetch_error = fetch_oanda_m15(c["pair"], start_dt, end_dt, token, base_url)

            if fetch_error:
                outcome = "FETCH_ERROR_RETRYABLE"
                outcome_pips = 0.0
                outcome_ts = None
            else:
                raw_outcome, outcome_pips, outcome_ts = simulate_tp_first(
                    c["direction"], c["entry"], c["sl"], c["tp"], candles, c["pair"]
                )
                if raw_outcome in {"TP_HIT", "SL_HIT"}:
                    outcome = raw_outcome
                elif current >= requested_end:
                    outcome = "EXPIRED_NO_HIT"
                else:
                    outcome = "OPEN_PENDING"

            record = {
                "key": c["key"],
                "timestamp": ts.isoformat(),
                "pair": c["pair"],
                "tf": c["tf"],
                "direction": c["direction"],
                "score": c["score"],
                "entry": c["entry"],
                "sl": c["sl"],
                "tp": c["tp"],
                "risk_pips": round(abs(c["entry"] - c["sl"]) / pip_size(c["pair"]), 1),
                "reward_pips": round(abs(c["tp"] - c["entry"]) / pip_size(c["pair"]), 1),
                "filter_reason": str(c["filter_reason"])[:300],
                "reasons": str(c["reasons"])[:500],
                "h1_neutral": c["h1_neutral"],
                "h1_veto": c["h1_veto"],
                "score_gate": c["score_gate"],
                "rr_gate": c["rr_gate"],
                "outcome": outcome,
                "outcome_pips": outcome_pips,
                "outcome_ts": outcome_ts,
                "candles_checked": len(candles),
                "window_start_utc": start_dt.isoformat(),
                "window_end_utc": end_dt.isoformat(),
                "checked_at": current.isoformat(),
                "trusted_server_utc": server_now.isoformat(),
                "fetch_error": fetch_error,
                "same_candle_policy": SAME_CANDLE_POLICY,
                "production_changed": False,
                "strategy_changed": False,
            }

            out.write(json.dumps(record, separators=(",", ":"), ensure_ascii=False) + "\n")
            written += 1

            print(
                f"{ts.strftime('%m-%d %H:%M')} {c['pair']} {c['direction']} "
                f"score={c['score']:.1f} -> {outcome} {outcome_pips:+.1f}p "
                f"candles={len(candles)}"
            )

    print("")
    print(f"written={written}")
    print(f"output={OUTPUT_JSONL}")
    print("FILES_REPLACED=YES | PRODUCTION_CHANGED=NO | STRATEGY_CHANGED=NO | OUTPUT_WRITTEN=YES")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
