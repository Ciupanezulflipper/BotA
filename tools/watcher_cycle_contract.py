#!/usr/bin/env python3
"""Fail-closed pre-reconciliation contract for one BotA watcher cycle.

This validator does not decide trades. It only proves that evidence consumed by
``watcher_cycle_ledger.py`` is bounded, unambiguous, and internally coherent.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import sys
from pathlib import Path
from typing import Any

MAX_SEGMENT_BYTES = 262_144
LEGACY_WIDTH = 13
CURRENT_WIDTH = 25
VALID_TELEGRAM = {
    "sent", "reconciled_sent", "definite_failure", "unknown_outcome",
    "sent_local_reconcile_failed",
}
VALID_SUPABASE = {
    "published", "skipped_active_exists", "skipped_non_green",
    "failed_missing_service_key", "failed_dedup_check", "failed_publish",
}
BAD_TELEGRAM = {"definite_failure", "unknown_outcome", "sent_local_reconcile_failed"}
BAD_SUPABASE = {"failed_missing_service_key", "failed_dedup_check", "failed_publish"}


def expected_scope() -> tuple[tuple[str, str], ...]:
    explicit = os.environ.get("BOTA_REQUIRED_DECISIONS", "").strip()
    if explicit:
        out = []
        for token in explicit.replace(",", " ").split():
            if ":" in token:
                pair, tf = token.upper().split(":", 1)
                if pair and tf:
                    out.append((pair, tf))
        if out:
            return tuple(out)
    pairs = tuple(x.upper() for x in os.environ.get("PAIRS", "EURUSD GBPUSD USDJPY").split())
    tfs = tuple(x.upper() for x in os.environ.get("TIMEFRAMES", "M15").split())
    return tuple((pair, tf) for tf in tfs for pair in pairs)


def bounded_segment(path: Path, offset: int) -> bytes:
    try:
        size = path.stat().st_size
    except OSError as exc:
        raise ValueError("segment_missing") from exc
    if offset < 0 or offset > size:
        raise ValueError("segment_offset_invalid")
    length = size - offset
    if length > MAX_SEGMENT_BYTES:
        raise ValueError("segment_too_large")
    with path.open("rb") as handle:
        handle.seek(offset)
        return handle.read(length)


def parse_rows(alerts: Path, offset: int) -> dict[tuple[str, str], dict[str, str]]:
    raw = bounded_segment(alerts, offset).decode("utf-8", "replace")
    grouped: dict[tuple[str, str], list[dict[str, str]]] = {}
    for values in csv.reader(io.StringIO(raw)):
        if not values:
            continue
        if len(values) not in {LEGACY_WIDTH, CURRENT_WIDTH}:
            raise ValueError("alerts_row_width_invalid")
        pair = values[1].upper().strip()
        tf = values[2].upper().strip()
        if not pair or not tf:
            raise ValueError("alerts_identity_missing")
        rejected = values[10].strip().lower() in {"1", "true", "yes", "y", "on"}
        row = {
            "pair": pair,
            "timeframe": tf,
            "direction": values[3].upper().strip(),
            "score": values[4].strip(),
            "entry": values[6].strip(),
            "sl": values[7].strip(),
            "tp": values[8].strip(),
            "rejected": "true" if rejected else "false",
            "tier": values[22].upper().strip() if len(values) == CURRENT_WIDTH else "",
        }
        grouped.setdefault((pair, tf), []).append(row)

    out: dict[tuple[str, str], dict[str, str]] = {}
    for scope in expected_scope():
        matches = grouped.get(scope, [])
        if len(matches) != 1:
            raise ValueError(f"decision_count_invalid:{scope[0]}:{scope[1]}:{len(matches)}")
        out[scope] = matches[0]
    return out


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError("structured_evidence_missing") from exc
    out = []
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except ValueError as exc:
            raise ValueError("structured_evidence_json_invalid") from exc
        if not isinstance(value, dict):
            raise ValueError("structured_evidence_type_invalid")
        out.append(value)
    return out


def validate_telegram(rows: dict[tuple[str, str], dict[str, str]], records: list[dict[str, Any]]) -> None:
    seen: set[tuple[str, str]] = set()
    for record in records:
        pair = str(record.get("pair") or "").upper()
        tf = str(record.get("timeframe") or "").upper()
        status = str(record.get("status") or "")
        identity = (pair, tf)
        if identity not in rows or status not in VALID_TELEGRAM:
            raise ValueError("telegram_record_invalid")
        if identity in seen:
            raise ValueError("telegram_record_ambiguous")
        seen.add(identity)
        row = rows[identity]
        for field in ("direction", "score", "entry", "sl", "tp"):
            if not str(record.get(field) or "") or str(record.get(field)) != row[field]:
                raise ValueError(f"telegram_identity_mismatch:{field}")
        if row["rejected"] == "true":
            raise ValueError("telegram_for_rejected_decision")
        if status in BAD_TELEGRAM:
            raise ValueError(f"telegram_delivery_unhealthy:{status}")


def validate_supabase(
    rows: dict[tuple[str, str], dict[str, str]], records: list[dict[str, Any]], cycle_id: str
) -> None:
    by_scope: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for record in records:
        pair = str(record.get("pair") or "").upper()
        tf = str(record.get("timeframe") or "").upper()
        status = str(record.get("status") or "")
        if str(record.get("cycle_id") or "") != cycle_id:
            raise ValueError("supabase_cycle_id_mismatch")
        if not pair or not tf or not str(record.get("direction") or "") or not str(record.get("entry") or ""):
            raise ValueError("supabase_identity_missing")
        if status not in VALID_SUPABASE:
            raise ValueError("supabase_status_invalid")
        by_scope.setdefault((pair, tf), []).append(record)

    service_key_present = bool(os.environ.get("SUPABASE_SERVICE_KEY", "").strip())
    for scope, row in rows.items():
        records_for_scope = by_scope.get(scope, [])
        if len(records_for_scope) > 1:
            raise ValueError("supabase_record_ambiguous")
        if records_for_scope:
            record = records_for_scope[0]
            if str(record.get("direction") or "").upper() != row["direction"]:
                raise ValueError("supabase_direction_mismatch")
            if str(record.get("entry") or "") != row["entry"]:
                raise ValueError("supabase_entry_mismatch")
            if str(record.get("status") or "") in BAD_SUPABASE:
                raise ValueError(f"supabase_delivery_unhealthy:{record['status']}")
        if row["rejected"] == "false" and row["tier"] == "GREEN" and service_key_present:
            # GREEN publication follows successful Telegram delivery. If Telegram
            # evidence says sent/reconciled and the publisher inherited this
            # cycle, absence of its structured result is not authoritative.
            telegram_sent = False
            # Caller passes Telegram records separately; the scope-level sent
            # check is represented through a private marker in main below.
            if os.environ.get(f"_BOTA_TG_SENT_{scope[0]}_{scope[1]}") == "1":
                telegram_sent = True
            if telegram_sent and not records_for_scope:
                raise ValueError("supabase_evidence_missing_after_telegram_send")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cycle-id", required=True)
    parser.add_argument("--alerts-path", type=Path, required=True)
    parser.add_argument("--alerts-offset", type=int, required=True)
    parser.add_argument("--log-path", type=Path, required=True)
    parser.add_argument("--log-offset", type=int, default=0)
    parser.add_argument("--telegram-result-path", type=Path, required=True)
    parser.add_argument("--supabase-result-path", type=Path, required=True)
    args = parser.parse_args()

    try:
        # The log segment must also remain exact/bounded; the older ledger may
        # display a tail for diagnostics, but a truncated/rotated current cycle
        # cannot be authoritative.
        bounded_segment(args.log_path, args.log_offset)
        rows = parse_rows(args.alerts_path, args.alerts_offset)
        telegram = read_jsonl(args.telegram_result_path)
        supabase = read_jsonl(args.supabase_result_path)
        validate_telegram(rows, telegram)
        sent_scopes = {
            (str(r.get("pair") or "").upper(), str(r.get("timeframe") or "").upper())
            for r in telegram if str(r.get("status") or "") in {"sent", "reconciled_sent"}
        }
        for pair, tf in sent_scopes:
            os.environ[f"_BOTA_TG_SENT_{pair}_{tf}"] = "1"
        validate_supabase(rows, supabase, args.cycle_id)
    except (OSError, ValueError) as exc:
        print(f"[WATCHER_CONTRACT] FAIL {exc}", file=sys.stderr)
        return 4

    print("[WATCHER_CONTRACT] PASS", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
