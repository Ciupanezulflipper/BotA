#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

ROOT="${HOME}/BotA"
LOG_DIR="${ROOT}/logs"
IN_JSONL="${LOG_DIR}/shadow_adx_scoring.jsonl"
OUT_JSONL="${LOG_DIR}/shadow_adx_weekly_summary.jsonl"
WINDOW_DAYS="${WINDOW_DAYS:-7}"

mkdir -p "${LOG_DIR}"

python3 - <<'PY'
from __future__ import annotations
import json
import os
import statistics
from datetime import datetime, timezone, timedelta

ROOT = os.path.expanduser("~/BotA")
LOG_DIR = os.path.join(ROOT, "logs")
IN_JSONL = os.path.join(LOG_DIR, "shadow_adx_scoring.jsonl")
OUT_JSONL = os.path.join(LOG_DIR, "shadow_adx_weekly_summary.jsonl")
WINDOW_DAYS = int(os.environ.get("WINDOW_DAYS", "7"))

now_utc = datetime.now(timezone.utc)
window_start = now_utc - timedelta(days=WINDOW_DAYS)

def parse_iso(ts: str):
    try:
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            return None
        return dt.astimezone(timezone.utc)
    except Exception:
        return None

rows = []
if os.path.exists(IN_JSONL):
    with open(IN_JSONL, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                if isinstance(obj, dict):
                    rows.append(obj)
            except Exception:
                continue

window_rows = []
for r in rows:
    ts = parse_iso(str(r.get("timestamp", "")))
    if ts is None:
        continue
    if ts >= window_start:
        window_rows.append(r)

non_hold = [r for r in window_rows if str(r.get("direction_pre_gate", "")).upper() != "HOLD"]
buy_count = sum(1 for r in non_hold if str(r.get("direction_pre_gate", "")).upper() == "BUY")
sell_count = sum(1 for r in non_hold if str(r.get("direction_pre_gate", "")).upper() == "SELL")

scores = []
adx_values = []
pairs = {}
d1_aligned = 0
d1_total = 0

for r in non_hold:
    try:
        scores.append(float(r.get("score_partial_pre_gate", 0.0) or 0.0))
    except Exception:
        pass
    try:
        adx_values.append(float(r.get("adx", 0.0) or 0.0))
    except Exception:
        pass

    pair = str(r.get("pair", "")).upper()
    if pair:
        pairs[pair] = pairs.get(pair, 0) + 1

    d = str(r.get("direction_pre_gate", "")).upper()
    d1 = str(r.get("d1_trend", "")).upper()
    if d1:
        d1_total += 1
        if d == d1:
            d1_aligned += 1

score_ge_52 = sum(1 for s in scores if s >= 52.0)

summary = {
    "timestamp_utc": now_utc.isoformat(),
    "window_days": WINDOW_DAYS,
    "window_start_utc": window_start.isoformat(),
    "shadow_entries_total": len(window_rows),
    "shadow_entries_non_hold": len(non_hold),
    "buy_count": buy_count,
    "sell_count": sell_count,
    "avg_partial_score": round(statistics.mean(scores), 2) if scores else 0.0,
    "max_partial_score": round(max(scores), 2) if scores else 0.0,
    "min_partial_score": round(min(scores), 2) if scores else 0.0,
    "avg_adx": round(statistics.mean(adx_values), 2) if adx_values else 0.0,
    "count_score_ge_52": score_ge_52,
    "d1_alignment_ratio": round((d1_aligned / d1_total), 4) if d1_total else None,
    "pairs": pairs,
    "last_entry_timestamp": window_rows[-1].get("timestamp") if window_rows else None,
}

os.makedirs(LOG_DIR, exist_ok=True)

with open(OUT_JSONL, "a", encoding="utf-8") as f:
    f.write(json.dumps(summary, separators=(",", ":"), ensure_ascii=False) + "\n")

print("SUMMARY_WRITTEN=YES")
print(json.dumps(summary, indent=2, ensure_ascii=False))
PY
