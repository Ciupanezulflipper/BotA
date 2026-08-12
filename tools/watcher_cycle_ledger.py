#!/usr/bin/env python3
"""Reconcile one bounded watcher run into terminal pair/timeframe decisions.

Only evidence produced by the current watcher cycle is considered. Historical
``alerts.csv`` files may contain legacy 13-column headers followed by newer
25-column rows, so appended rows are parsed by their actual width rather than
blindly by the first retained header.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

DEFAULT_EXPECTED = (
    ("EURUSD", "M15"),
    ("GBPUSD", "M15"),
    ("USDJPY", "M15"),
)
MAX_NEW_BYTES = 262_144

LEGACY_ALERT_FIELDS_13 = (
    "ts_local", "pair", "tf", "direction", "score", "score_raw",
    "entry", "sl", "tp", "provider", "rejected", "filter_reasons",
    "features",
)
CANONICAL_ALERT_FIELDS_25 = LEGACY_ALERT_FIELDS_13 + (
    "ema_comp", "rsi_comp", "macd_comp", "adx_comp", "adx", "rsi",
    "macd_hist", "macro6", "h1_trend", "tier", "session", "regime",
)


def _split_scope(raw: str) -> tuple[str, ...]:
    if not raw:
        return ()
    tokens = [item.strip().upper() for item in raw.replace(",", " ").split()]
    return tuple(token for token in tokens if token)


def expected_scope() -> tuple[tuple[str, str], ...]:
    explicit = os.environ.get("BOTA_REQUIRED_DECISIONS", "").strip()
    if explicit:
        entries: list[tuple[str, str]] = []
        for token in _split_scope(explicit):
            if ":" not in token:
                continue
            pair, _, timeframe = token.partition(":")
            if pair and timeframe:
                entries.append((pair, timeframe))
        if entries:
            return tuple(entries)

    pairs = _split_scope(os.environ.get("PAIRS", ""))
    timeframes = _split_scope(os.environ.get("TIMEFRAMES", ""))
    if pairs and timeframes:
        return tuple((pair, tf) for pair in pairs for tf in timeframes)
    return DEFAULT_EXPECTED


EXPECTED = DEFAULT_EXPECTED


def root_dir() -> Path:
    value = os.environ.get("BOTA_ROOT", "").strip()
    return Path(value).expanduser() if value else Path(__file__).resolve().parent.parent


def read_new_bytes(path: Path, offset: int) -> str:
    if not path.exists():
        return ""
    size = path.stat().st_size
    if offset < 0 or offset > size:
        offset = size
    with path.open("rb") as handle:
        handle.seek(offset)
        data = handle.read(MAX_NEW_BYTES + 1)
    if len(data) > MAX_NEW_BYTES:
        data = data[-MAX_NEW_BYTES:]
        if b"\n" in data:
            data = data.split(b"\n", 1)[1]
    return data.decode(errors="replace")


def read_header(path: Path) -> list[str]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
        line = handle.readline()
    return next(csv.reader([line]), []) if line else []


def _row_schema(values: list[str]) -> tuple[str, ...] | None:
    if len(values) == len(CANONICAL_ALERT_FIELDS_25):
        return CANONICAL_ALERT_FIELDS_25
    if len(values) == len(LEGACY_ALERT_FIELDS_13):
        return LEGACY_ALERT_FIELDS_13
    return None


def parse_new_rows(path: Path, offset: int) -> list[dict[str, str]]:
    """Parse appended rows by actual width; malformed widths fail closed."""
    header = read_header(path)
    segment = read_new_bytes(path, offset)
    if not segment.strip():
        return []

    rows: list[dict[str, str]] = []
    for values in csv.reader(io.StringIO(segment)):
        if not values:
            continue
        if header and values == header:
            continue
        if tuple(values) in {LEGACY_ALERT_FIELDS_13, CANONICAL_ALERT_FIELDS_25}:
            continue
        schema = _row_schema(values)
        if schema is None:
            continue
        rows.append(dict(zip(schema, values, strict=True)))
    return rows


def truthy(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "on"}


def normalized_rejected(row: dict[str, str]) -> bool:
    """Normalize legacy/new rejection keys; never treat an explicit true as false."""
    if "filter_rejected" in row and str(row.get("filter_rejected", "")).strip() != "":
        return truthy(row.get("filter_rejected"))
    return truthy(row.get("rejected"))


def pair_lines(log_text: str, pair: str, timeframe: str) -> list[str]:
    token = f"{pair} {timeframe}"
    return [line for line in log_text.splitlines() if token in line]


def trusted_server_epoch(cli_epoch: int, log_text: str) -> int:
    if cli_epoch > 1_000_000_000:
        return cli_epoch
    matches = re.findall(r"BOTA_SERVER_EPOCH=(\d+)", log_text)
    if not matches:
        return 0
    value = int(matches[-1])
    return value if value > 1_000_000_000 else 0


def log_outcome(lines: list[str]) -> tuple[str, str, str, str]:
    joined = "\n".join(lines)
    rules = (
        (r"raw_cache missing/invalid", "raw_cache_invalid"),
        (r"candle_stale", "candle_stale"),
        (r"daily -3R circuit breaker active", "pause_guard"),
        (r"\[NEWS_GATE ", "news_gate"),
        (r"\[CALENDAR_BLOCK ", "calendar_gate"),
        (r"parse_error", "parse_error"),
        (r"rejected_by_filter", "filter_rejected"),
        (r"gate: score_int=.*TELEGRAM_MIN_SCORE", "telegram_score_gate"),
        (r"tier_skip", "telegram_tier_gate"),
        (r"cooldown active", "telegram_cooldown"),
        (r"already delivered", "delivery_dedup"),
        (r"SENT: via", "telegram_sent"),
        (r"send failed|FAILED:", "telegram_failed"),
        (r"accepted score=", "accepted_no_delivery_evidence"),
    )
    outcome = "no_terminal_outcome"
    for pattern, name in rules:
        if re.search(pattern, joined):
            outcome = name
            break

    telegram = "not_attempted"
    if "SENT: via" in joined:
        telegram = "sent"
    elif "send failed" in joined or "FAILED:" in joined:
        telegram = "failed"
    elif outcome in {"telegram_score_gate", "telegram_tier_gate", "telegram_cooldown", "delivery_dedup"}:
        telegram = outcome

    supabase = "not_attempted"
    if "publish failed" in joined:
        supabase = "failed"
    elif "published" in joined.lower():
        supabase = "published"
    elif "skip non-GREEN" in joined:
        supabase = "skipped_non_green"

    rejection = ""
    match = re.findall(r"filters=([^\n]+)", joined)
    if match:
        rejection = match[-1][:1000]
    return outcome, telegram, supabase, rejection


def extract_stale_fields(lines: list[str]) -> tuple[str, int | None]:
    joined = "\n".join(lines)
    ts_match = re.findall(r"last=([^ ]+)", joined)
    age_match = re.findall(r"candle_stale age=(\d+)s", joined)
    timestamp = ts_match[-1] if ts_match else ""
    age = int(age_match[-1]) if age_match else None
    return timestamp, age


def ledger_decision(*, cycle_id: str, server_epoch: int, pair: str, timeframe: str,
                    row: dict[str, str] | None, lines: list[str]) -> dict[str, Any]:
    row = row or {}
    outcome, telegram, supabase, rejection = log_outcome(lines)
    persisted = bool(row)
    rejected = normalized_rejected(row)
    if persisted and rejected:
        outcome = "filter_rejected"
    elif persisted and outcome == "no_terminal_outcome":
        outcome = "decision_persisted_no_delivery_evidence"
    candle_timestamp, candle_age = extract_stale_fields(lines)

    command = [
        sys.executable, str(root_dir() / "tools" / "pipeline_ledger.py"), "decision",
        "--component", "watcher", "--status", "completed" if outcome != "no_terminal_outcome" else "failed",
        "--cycle-id", cycle_id, "--pair", pair, "--timeframe", timeframe,
        "--outcome", outcome, "--provider", row.get("provider", "unknown") or "unknown",
        "--candle-timestamp", candle_timestamp,
        "--filter-rejected", "true" if rejected else "false",
        "--rejection-gate", row.get("filter_reasons", "") or rejection,
        "--alerts-csv-persisted", "true" if persisted else "false",
        "--telegram-result", telegram, "--supabase-result", supabase,
        "--server-epoch", str(server_epoch),
    ]
    if candle_age is not None:
        command.extend(["--candle-age", str(candle_age)])
    score = row.get("score", "").strip()
    if score:
        command.extend(["--score", score])
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    return {
        "pair": pair, "timeframe": timeframe, "outcome": outcome,
        "persisted": persisted, "telegram": telegram, "supabase": supabase,
        "server_epoch": server_epoch, "ledger_rc": result.returncode,
        "ledger_stderr": result.stderr.strip()[:500],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cycle-id", required=True)
    parser.add_argument("--alerts-offset", type=int, required=True)
    parser.add_argument("--log-offset", type=int, default=0)
    parser.add_argument("--log-path", type=Path, default=None,
                        help="Exact current-cycle watcher stderr. Falls back to cron.signals.log for compatibility.")
    parser.add_argument("--server-epoch", type=int, default=0)
    args = parser.parse_args()

    root = root_dir()
    alerts = root / "logs" / "alerts.csv"
    log_path = args.log_path if args.log_path is not None else root / "logs" / "cron.signals.log"
    rows = parse_new_rows(alerts, args.alerts_offset)
    log_text = read_new_bytes(log_path, args.log_offset)
    effective_epoch = trusted_server_epoch(args.server_epoch, log_text)
    results: list[dict[str, Any]] = []

    for pair, timeframe in expected_scope():
        matching = [row for row in rows
                    if str(row.get("pair", "")).upper() == pair
                    and str(row.get("tf", row.get("timeframe", ""))).upper() == timeframe]
        results.append(ledger_decision(
            cycle_id=args.cycle_id, server_epoch=effective_epoch, pair=pair, timeframe=timeframe,
            row=matching[-1] if matching else None, lines=pair_lines(log_text, pair, timeframe)))

    healthy = all(item["outcome"] != "no_terminal_outcome" and item["ledger_rc"] == 0 for item in results)
    status = "completed" if healthy else "failed"
    subprocess.run([
        sys.executable, str(root / "tools" / "pipeline_ledger.py"), "component",
        "--component", "watcher", "--status", status, "--cycle-id", args.cycle_id,
        "--details", json.dumps(results, separators=(",", ":")),
        "--server-epoch", str(effective_epoch),
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    print(json.dumps({"healthy": healthy, "cycle_id": args.cycle_id,
                      "server_epoch": effective_epoch, "results": results}, indent=2, sort_keys=True))
    return 0 if healthy else 3


if __name__ == "__main__":
    raise SystemExit(main())
