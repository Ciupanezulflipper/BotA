#!/usr/bin/env python3
"""Pre-network uniqueness guard for the canonical BotA Telegram sender."""
from __future__ import annotations

import argparse
import csv
import io
import os
import sys
from pathlib import Path

from telegram_delivery import CURRENT_FIELDS, LEGACY_FIELDS, parse_message

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
    if not identity:
        raise ValueError("message_identity_unparseable")
    matches = 0
    for values in csv.reader(io.StringIO(current_segment())):
        if not values:
            continue
        if len(values) == len(CURRENT_FIELDS):
            row = dict(zip(CURRENT_FIELDS, values, strict=True))
        elif len(values) == len(LEGACY_FIELDS):
            row = dict(zip(LEGACY_FIELDS, values, strict=True))
        else:
            raise ValueError("alerts_row_width_invalid")
        rejected = str(row.get("filter_rejected", row.get("rejected", ""))).strip().lower()
        if rejected in {"1", "true", "yes", "y", "on"}:
            continue
        if (
            str(row.get("pair") or "").upper() == identity["pair"]
            and str(row.get("tf") or "").upper() == identity["timeframe"]
            and str(row.get("direction") or "").upper() == identity["direction"]
            and str(row.get("score") or "") == identity["score"]
            and str(row.get("entry") or "") == identity["entry"]
            and str(row.get("sl") or "") == identity["sl"]
            and str(row.get("tp") or "") == identity["tp"]
        ):
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
