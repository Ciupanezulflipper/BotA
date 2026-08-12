#!/usr/bin/env python3
"""Fail-closed postcondition for watcher decision-journal persistence.

For each pair/timeframe that reached an evaluated accept/reject outcome in the
current-cycle log, require a matching row appended to alerts.csv after the
recorded byte offset. Pre-evaluation gates (stale/news/calendar/pause) do not
require an alerts.csv decision row.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import re
from pathlib import Path

LEGACY_FIELDS = (
    "timestamp","pair","tf","direction","score","confidence","entry","sl","tp",
    "provider","rejected","filter_str","reasons",
)
CURRENT_FIELDS = (
    "ts","pair","tf","direction","score","confidence","entry","sl","tp","provider",
    "filter_rejected","filter_reasons","reasons","ema_comp","rsi_comp","macd_comp",
    "adx_comp","adx_raw","rsi_raw","macd_hist_raw","macro6","h1_trend","tier","session",
    "adx_regime",
)
EVALUATED_RE = re.compile(r"\b([A-Z]{6})\s+([A-Z0-9]+)\s+(?:accepted|rejected_by_filter)\b")


def read_segment(path: Path, offset: int) -> str:
    if not path.exists():
        return ""
    size = path.stat().st_size
    if offset < 0 or offset > size:
        return ""
    with path.open("rb") as handle:
        handle.seek(offset)
        return handle.read(1_048_576).decode("utf-8", "replace")


def parse_pairs(segment: str) -> tuple[set[tuple[str,str]], bool]:
    found: set[tuple[str,str]] = set()
    malformed = False
    for values in csv.reader(io.StringIO(segment)):
        if not values:
            continue
        if tuple(values) in {LEGACY_FIELDS, CURRENT_FIELDS}:
            continue
        if len(values) == len(CURRENT_FIELDS):
            row = dict(zip(CURRENT_FIELDS, values, strict=True))
        elif len(values) == len(LEGACY_FIELDS):
            row = dict(zip(LEGACY_FIELDS, values, strict=True))
        else:
            malformed = True
            continue
        pair = str(row.get("pair","")).upper()
        tf = str(row.get("tf","")).upper()
        if pair and tf:
            found.add((pair,tf))
    return found, malformed


def expected_evaluated(log_text: str) -> set[tuple[str,str]]:
    return {(m.group(1), m.group(2).upper()) for m in EVALUATED_RE.finditer(log_text)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--alerts-path", type=Path, required=True)
    parser.add_argument("--alerts-offset", type=int, required=True)
    parser.add_argument("--log-path", type=Path, required=True)
    args = parser.parse_args()

    try:
        log_text = args.log_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        print(json.dumps({"healthy": False, "reason": "cycle_log_unreadable"}))
        return 3

    required = expected_evaluated(log_text)
    persisted, malformed = parse_pairs(read_segment(args.alerts_path, args.alerts_offset))
    missing = sorted(required - persisted)
    healthy = not malformed and not missing
    print(json.dumps({
        "healthy": healthy,
        "required": sorted([f"{p}:{t}" for p,t in required]),
        "persisted": sorted([f"{p}:{t}" for p,t in persisted]),
        "missing": [f"{p}:{t}" for p,t in missing],
        "malformed": malformed,
    }, sort_keys=True))
    return 0 if healthy else 3


if __name__ == "__main__":
    raise SystemExit(main())
