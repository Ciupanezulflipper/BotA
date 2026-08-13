#!/usr/bin/env python3
"""Pre-network uniqueness guard for the canonical BotA Telegram sender."""
from __future__ import annotations

import argparse
import csv
import io
import os
import sys
from pathlib import Path

from telegram_delivery import decision_matches, parse_message, row_dict

MAX_SEGMENT_BYTES = 262_144


def current_segment() -> str:
    root = Path(os.environ.get("BOTA_ROOT", str(Path.home() / "BotA"))).expanduser().resolve()
    alerts = root / "logs" / "alerts.csv"
    raw_offset = os.environ.get("BOTA_ALERTS_OFFSET", "").strip()
    if not raw_offset.isdigit():
        raise ValueError("alerts_offset_missing_or_invalid")
    offset = int(raw_offset)
    try:
        size = alerts.stat().st_size
    except OSError as exc:
        raise ValueError("alerts_missing") from exc
    if offset < 0 or offset > size:
        raise ValueError("alerts_offset_out_of_range")
    length = size - offset
    if length > MAX_SEGMENT_BYTES:
        raise ValueError("alerts_segment_too_large")
    with alerts.open("rb") as handle:
        handle.seek(offset)
        return handle.read(length).decode("utf-8", "replace")


def matching_rows(message: str) -> int:
    identity = parse_message(message)
    matches = 0
    for values in csv.reader(io.StringIO(current_segment())):
        if not values:
            continue
        row = row_dict(values)
        if row is None:
            raise ValueError("alerts_row_width_invalid")
        if decision_matches(row, identity):
            matches += 1
    return matches


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--message", required=True)
    args = parser.parse_args()
    try:
        count = matching_rows(args.message)
    except (OSError, ValueError) as exc:
        print(f"[telegram_send_guard] FAIL {exc}", file=sys.stderr)
        return 65
    if count != 1:
        print(f"[telegram_send_guard] FAIL current_cycle_match_count={count}", file=sys.stderr)
        return 65
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
