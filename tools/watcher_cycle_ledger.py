#!/usr/bin/env python3
"""Reconcile one bounded watcher run into terminal pair/timeframe decisions.

Only evidence produced by the current watcher cycle is considered. Historical
``alerts.csv`` files retain a legacy 13-column header while newer rows use the
current 25-column schema, so appended rows are parsed by their actual width.
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
    "timestamp", "pair", "tf", "direction", "score", "confidence",
    "entry", "sl", "tp", "provider", "rejected", "filter_str", "reasons",
)
CURRENT_ALERT_FIELDS_25 = (
    "ts", "pair", "tf", "direction", "score", "confidence",
    "entry", "sl", "tp", "provider", "filter_rejected", "filter_reasons",
    "reasons", "ema_comp", "rsi_comp", "macd_comp", "adx_comp", "adx_raw",
    "rsi_raw", "macd_hist_raw", "macro6", "h1_trend", "tier", "session",
    "adx_regime",
)
CANONICAL_ALERT_FIELDS_25 = CURRENT_ALERT_FIELDS_25  # compatibility for tests/importers
VALID_SUPABASE_STATUSES = {
    "published",
    "skipped_active_exists",
    "skipped_non_green",
    "failed_missing_service_key",
    "failed_dedup_check",
    "failed_publish",
}


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
    if len(values) == len(CURRENT_ALERT_FIELDS_25):
        return CURRENT_ALERT_FIELDS_25
    if len(values) == len(LEGACY_ALERT_FIELDS_13):
        return LEGACY_ALERT_FIELDS_13
    return None


def parse_new_rows(path: Path, offset: int) -> list[dict[str, str]]:
    """Parse appended rows by actual width and surface malformed evidence."""
    header = read_header(path)
    segment = read_new_bytes(path, offset)
    if not segment.strip():
        return []

    rows: list[dict[str, str]] = []
    known_headers = {tuple(LEGACY_ALERT_FIELDS_13), tuple(CURRENT_ALERT_FIELDS_25)}
    for values in csv.reader(io.StringIO(segment)):
        if not values:
            continue
        if header and values == header:
            continue
        if tuple(values) in known_headers:
            continue
        schema = _row_schema(values)
        if schema is None:
            rows.append(
                {
                    "_malformed": "true",
                    "_width": str(len(values)),
                    "pair": values[1].upper() if len(values) > 1 else "",
                    "tf": values[2].upper() if len(values) > 2 else "",
                }
            )
            continue
        rows.append(dict(zip(schema, values, strict=True)))
    return rows


def truthy(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "on"}


def normalized_rejected(row: dict[str, str]) -> bool:
    """Normalize legacy/new rejection keys; never turn explicit true into false."""
    if "filter_rejected" in row and str(row.get("filter_rejected", "")).strip() != "":
        return truthy(row.get("filter_rejected"))
    return truthy(row.get("rejected"))


def normalized_filter_reasons(row: dict[str, str]) -> str:
    return str(row.get("filter_reasons") or row.get("filter_str") or "")


def pair_lines(log_text: str, pair: str, timeframe: str) -> list[str]:
    """Return the pair's contiguous cycle span, including unscoped send lines."""
    target = (pair, timeframe)
    scope = expected_scope()
    current: tuple[str, str] | None = None
    selected: list[str] = []
    for line in log_text.splitlines():
        matched = [item for item in scope if f"{item[0]} {item[1]}" in line]
        if len(matched) == 1:
            current = matched[0]
        elif len(matched) > 1:
            current = None
        if current == target:
            selected.append(line)
    return selected


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
    elif outcome in {
        "telegram_score_gate", "telegram_tier_gate", "telegram_cooldown", "delivery_dedup",
    }:
        telegram = outcome

    supabase = "not_attempted"
    if "publish failed" in joined:
        supabase = "failed"
    elif "skip non-GREEN" in joined:
        supabase = "skipped_non_green"

    rejection = ""
    match = re.findall(r"filters=([^\n]+)", joined)
    if match:
        rejection = match[-1][:1000]
    return outcome, telegram, supabase, rejection


def parse_supabase_results(path: Path | None) -> tuple[list[dict[str, str]], bool]:
    """Read watcher-owned structured Supabase results; malformed evidence fails closed."""
    if path is None:
        return [], False
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return [], False
    except OSError:
        return [], True

    results: list[dict[str, str]] = []
    malformed = False
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except ValueError:
            malformed = True
            continue
        if not isinstance(value, dict):
            malformed = True
            continue
        pair = str(value.get("pair") or "").upper()
        timeframe = str(value.get("timeframe") or "").upper()
        status = str(value.get("status") or "")
        if not pair or not timeframe or status not in VALID_SUPABASE_STATUSES:
            malformed = True
            continue
        results.append({
            "pair": pair,
            "timeframe": timeframe,
            "direction": str(value.get("direction") or "").upper(),
            "entry": str(value.get("entry") or ""),
            "tier": str(value.get("tier") or "").upper(),
            "status": status,
        })
    return results, malformed


def supabase_for_decision(
    results: list[dict[str, str]],
    *,
    pair: str,
    timeframe: str,
    row: dict[str, str] | None,
) -> tuple[str | None, bool]:
    """Return exact structured result and ambiguity flag for one decision."""
    candidates = [
        item for item in results
        if item["pair"] == pair and item["timeframe"] == timeframe
    ]
    if row:
        direction = str(row.get("direction") or "").upper()
        entry = str(row.get("entry") or "")
        if direction:
            candidates = [item for item in candidates if not item["direction"] or item["direction"] == direction]
        if entry:
            candidates = [item for item in candidates if not item["entry"] or item["entry"] == entry]
    if not candidates:
        return None, False
    if len(candidates) != 1:
        return None, True
    return candidates[0]["status"], False


def extract_stale_fields(lines: list[str]) -> tuple[str, int | None]:
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
    structured_supabase: str | None = None,
    supabase_ambiguous: bool = False,
) -> dict[str, Any]:
    row = row or {}
    outcome, telegram, supabase, rejection = log_outcome(lines)
    malformed = truthy(row.get("_malformed")) or supabase_ambiguous
    persisted = bool(row) and not malformed
    rejected = normalized_rejected(row)

    if structured_supabase is not None:
        if structured_supabase.startswith("failed_"):
            supabase = "failed"
        else:
            supabase = structured_supabase

    if malformed:
        outcome = "parse_error"
        telegram = "not_attempted"
        supabase = "not_attempted" if structured_supabase is None else supabase
    elif persisted and rejected:
        outcome = "filter_rejected"
    elif persisted and outcome == "no_terminal_outcome":
        outcome = "decision_persisted_no_delivery_evidence"
    candle_timestamp, candle_age = extract_stale_fields(lines)

    command = [
        sys.executable,
        str(root_dir() / "tools" / "pipeline_ledger.py"),
        "decision",
        "--component", "watcher",
        "--status", "failed" if malformed or outcome == "no_terminal_outcome" else "completed",
        "--cycle-id", cycle_id,
        "--pair", pair,
        "--timeframe", timeframe,
        "--outcome", outcome,
        "--provider", row.get("provider", "unknown") or "unknown",
        "--candle-timestamp", candle_timestamp,
        "--filter-rejected", "true" if rejected else "false",
        "--rejection-gate", normalized_filter_reasons(row) or rejection,
        "--alerts-csv-persisted", "true" if persisted else "false",
        "--telegram-result", telegram,
        "--supabase-result", supabase,
        "--server-epoch", str(server_epoch),
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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cycle-id", required=True)
    parser.add_argument("--alerts-offset", type=int, required=True)
    parser.add_argument("--log-offset", type=int, default=0)
    parser.add_argument("--log-path", type=Path, default=None)
    parser.add_argument("--supabase-result-path", type=Path, default=None)
    parser.add_argument("--server-epoch", type=int, default=0)
    args = parser.parse_args()

    root = root_dir()
    alerts = root / "logs" / "alerts.csv"
    log_path = args.log_path if args.log_path is not None else root / "logs" / "cron.signals.log"
    rows = parse_new_rows(alerts, args.alerts_offset)
    log_text = read_new_bytes(log_path, args.log_offset)
    supabase_results, supabase_malformed = parse_supabase_results(args.supabase_result_path)
    effective_epoch = trusted_server_epoch(args.server_epoch, log_text)
    results: list[dict[str, Any]] = []
    malformed = any(truthy(row.get("_malformed")) for row in rows) or supabase_malformed

    for pair, timeframe in expected_scope():
        matching = [
            row for row in rows
            if str(row.get("pair", "")).upper() == pair
            and str(row.get("tf", row.get("timeframe", ""))).upper() == timeframe
        ]
        selected_row = {"_malformed": "true"} if malformed else (matching[-1] if matching else None)
        supabase_status, supabase_ambiguous = supabase_for_decision(
            supabase_results,
            pair=pair,
            timeframe=timeframe,
            row=selected_row,
        )
        results.append(
            ledger_decision(
                cycle_id=args.cycle_id,
                server_epoch=effective_epoch,
                pair=pair,
                timeframe=timeframe,
                row=selected_row,
                lines=pair_lines(log_text, pair, timeframe),
                structured_supabase=supabase_status,
                supabase_ambiguous=supabase_ambiguous,
            )
        )
        malformed = malformed or supabase_ambiguous

    healthy = (
        not malformed
        and all(
            item["outcome"] != "no_terminal_outcome" and item["ledger_rc"] == 0
            for item in results
        )
    )
    status = "completed" if healthy else "failed"
    subprocess.run(
        [
            sys.executable,
            str(root / "tools" / "pipeline_ledger.py"),
            "component",
            "--component", "watcher",
            "--status", status,
            "--cycle-id", args.cycle_id,
            "--details", json.dumps(results, separators=(",", ":")),
            "--server-epoch", str(effective_epoch),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    print(json.dumps(
        {"healthy": healthy, "cycle_id": args.cycle_id, "server_epoch": effective_epoch, "results": results},
        indent=2,
        sort_keys=True,
    ))
    return 0 if healthy else 3


if __name__ == "__main__":
    raise SystemExit(main())
