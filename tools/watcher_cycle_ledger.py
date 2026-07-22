#!/usr/bin/env python3
"""Reconcile one bounded watcher run into terminal pair/timeframe decisions.

Only bytes appended after the wrapper-captured offsets are considered. This
prevents historical log/CSV content from being mistaken for current evidence.
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

EXPECTED = (("EURUSD", "M15"), ("GBPUSD", "M15"))
MAX_NEW_BYTES = 262_144


def root_dir() -> Path:
    """Resolve BotA root."""
    value = os.environ.get("BOTA_ROOT", "").strip()
    return Path(value).expanduser() if value else Path(__file__).resolve().parent.parent


def read_new_bytes(path: Path, offset: int) -> str:
    """Read a bounded append-only segment starting at the recorded offset."""
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
    """Read only the first CSV record as the schema."""
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
        line = handle.readline()
    return next(csv.reader([line]), []) if line else []


def parse_new_rows(path: Path, offset: int) -> list[dict[str, str]]:
    """Parse only rows appended during the current cycle."""
    header = read_header(path)
    segment = read_new_bytes(path, offset)
    if not header or not segment.strip():
        return []
    rows: list[dict[str, str]] = []
    for values in csv.reader(io.StringIO(segment)):
        if not values or values == header:
            continue
        padded = values + [""] * max(0, len(header) - len(values))
        rows.append(
            {
                key: padded[index] if index < len(padded) else ""
                for index, key in enumerate(header)
            }
        )
    return rows


def truthy(value: Any) -> bool:
    """Interpret common truthy CSV values."""
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "on"}


def pair_lines(log_text: str, pair: str, timeframe: str) -> list[str]:
    """Return exact current-cycle lines for one configured pair/timeframe."""
    token = f"{pair} {timeframe}"
    return [line for line in log_text.splitlines() if token in line]


def trusted_server_epoch(cli_epoch: int, log_text: str) -> int:
    """Resolve the current cycle's server epoch from CLI or bounded log evidence."""
    if cli_epoch > 1_000_000_000:
        return cli_epoch
    matches = re.findall(r"BOTA_SERVER_EPOCH=(\d+)", log_text)
    if not matches:
        return 0
    value = int(matches[-1])
    return value if value > 1_000_000_000 else 0


def log_outcome(lines: list[str]) -> tuple[str, str, str, str]:
    """Classify a terminal outcome and delivery results from bounded lines."""
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

    telegram = "not_attempted"
    if "SENT: via" in joined:
        telegram = "sent"
    elif "send failed" in joined or "FAILED:" in joined:
        telegram = "failed"
    elif outcome in {
        "telegram_score_gate",
        "telegram_tier_gate",
        "telegram_cooldown",
        "delivery_dedup",
    }:
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
    """Extract candle timestamp and age from exact stale evidence when present."""
    joined = "\n".join(lines)
    ts_match = re.findall(r"last=([^ ]+)", joined)
    age_match = re.findall(r"candle_stale age=(\d+)s", joined)
    timestamp = ts_match[-1] if ts_match else ""
    age = int(age_match[-1]) if age_match else None
    return timestamp, age


def ledger_decision(
    *,
    cycle_id: str,
    server_epoch: int,
    pair: str,
    timeframe: str,
    row: dict[str, str] | None,
    lines: list[str],
) -> dict[str, Any]:
    """Write one decision event and return its classification."""
    row = row or {}
    outcome, telegram, supabase, rejection = log_outcome(lines)
    persisted = bool(row)
    rejected = truthy(row.get("filter_rejected"))
    if persisted and rejected:
        outcome = "filter_rejected"
    elif persisted and outcome == "no_terminal_outcome":
        outcome = "decision_persisted_no_delivery_evidence"
    candle_timestamp, candle_age = extract_stale_fields(lines)

    command = [
        sys.executable,
        str(root_dir() / "tools" / "pipeline_ledger.py"),
        "decision",
        "--component",
        "watcher",
        "--status",
        "completed" if outcome != "no_terminal_outcome" else "failed",
        "--cycle-id",
        cycle_id,
        "--pair",
        pair,
        "--timeframe",
        timeframe,
        "--outcome",
        outcome,
        "--provider",
        row.get("provider", "unknown") or "unknown",
        "--candle-timestamp",
        candle_timestamp,
        "--filter-rejected",
        "true" if rejected else "false",
        "--rejection-gate",
        row.get("filter_reasons", "") or rejection,
        "--alerts-csv-persisted",
        "true" if persisted else "false",
        "--telegram-result",
        telegram,
        "--supabase-result",
        supabase,
        "--server-epoch",
        str(server_epoch),
    ]
    if candle_age is not None:
        command.extend(["--candle-age", str(candle_age)])
    score = row.get("score", "").strip()
    if score:
        command.extend(["--score", score])
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    return {
        "pair": pair,
        "timeframe": timeframe,
        "outcome": outcome,
        "persisted": persisted,
        "telegram": telegram,
        "supabase": supabase,
        "server_epoch": server_epoch,
        "ledger_rc": result.returncode,
        "ledger_stderr": result.stderr.strip()[:500],
    }


def main() -> int:
    """Reconcile and persist current-cycle terminal outcomes."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cycle-id", required=True)
    parser.add_argument("--alerts-offset", type=int, required=True)
    parser.add_argument("--log-offset", type=int, required=True)
    parser.add_argument("--server-epoch", type=int, default=0)
    args = parser.parse_args()

    root = root_dir()
    alerts = root / "logs" / "alerts.csv"
    log_path = root / "logs" / "cron.signals.log"
    rows = parse_new_rows(alerts, args.alerts_offset)
    log_text = read_new_bytes(log_path, args.log_offset)
    effective_epoch = trusted_server_epoch(args.server_epoch, log_text)
    results: list[dict[str, Any]] = []

    for pair, timeframe in EXPECTED:
        matching = [
            row
            for row in rows
            if str(row.get("pair", "")).upper() == pair
            and str(row.get("tf", row.get("timeframe", ""))).upper() == timeframe
        ]
        results.append(
            ledger_decision(
                cycle_id=args.cycle_id,
                server_epoch=effective_epoch,
                pair=pair,
                timeframe=timeframe,
                row=matching[-1] if matching else None,
                lines=pair_lines(log_text, pair, timeframe),
            )
        )

    healthy = all(
        item["outcome"] != "no_terminal_outcome" and item["ledger_rc"] == 0
        for item in results
    )
    status = "completed" if healthy else "failed"
    subprocess.run(
        [
            sys.executable,
            str(root / "tools" / "pipeline_ledger.py"),
            "component",
            "--component",
            "watcher",
            "--status",
            status,
            "--cycle-id",
            args.cycle_id,
            "--details",
            json.dumps(results, separators=(",", ":")),
            "--server-epoch",
            str(effective_epoch),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    print(
        json.dumps(
            {
                "healthy": healthy,
                "cycle_id": args.cycle_id,
                "server_epoch": effective_epoch,
                "results": results,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if healthy else 3


if __name__ == "__main__":
    raise SystemExit(main())
