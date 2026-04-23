#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None  # type: ignore

ROOT = Path.home() / "BotA"
LOG_DIR = ROOT / "logs"
REPLAY_DIR = LOG_DIR / "replay_audit"

DEFAULT_ALERTS = LOG_DIR / "alerts.csv"
DEFAULT_SUMMARY_JSONL = LOG_DIR / "daily_replay_audit.jsonl"
DEFAULT_SUMMARY_TEXT = LOG_DIR / "daily_replay_audit_latest.txt"
SIMULATOR = ROOT / "tools" / "shadow_outcome_simulator.py"


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def parse_ts(value: str) -> Optional[datetime]:
    s = str(value or "").strip()
    if not s:
        return None
    try:
        s = s.replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            return None
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(str(value).strip())
    except Exception:
        return default


def truthy(value: Any) -> bool:
    s = str(value or "").strip().lower()
    return s in {"1", "true", "yes", "y", "on"}


def parse_sl_tp_from_reasons(reasons: str) -> Tuple[Optional[float], Optional[float]]:
    m = re.search(r"SL:([\d.]+),TP:([\d.]+)", str(reasons or ""))
    if not m:
        return None, None
    try:
        return float(m.group(1)), float(m.group(2))
    except Exception:
        return None, None


def parse_d1_trend(reasons: str) -> str:
    m = re.search(r"d1_filter=([A-Z_]+)", str(reasons or ""))
    return m.group(1) if m else "ANY"


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


def write_jsonl(path: Path, rows: Iterable[Dict[str, Any]], mode: str = "w") -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open(mode, encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, separators=(",", ":"), ensure_ascii=False) + "\n")
            count += 1
    return count


def target_local_date(date_arg: str, tz_name: str) -> date:
    if ZoneInfo is None:
        raise RuntimeError("zoneinfo not available")
    tz = ZoneInfo(tz_name)
    now_local = now_utc().astimezone(tz).date()
    raw = str(date_arg or "").strip().lower()
    if raw in {"", "yesterday"}:
        return now_local - timedelta(days=1)
    if raw == "today":
        return now_local
    try:
        return datetime.strptime(raw, "%Y-%m-%d").date()
    except ValueError as exc:
        raise RuntimeError(
            f"invalid --date '{date_arg}', expected YYYY-MM-DD|today|yesterday"
        ) from exc


def build_source_key(ts_utc_iso: str, pair: str, tf: str, direction: str, entry: float) -> str:
    return "|".join([ts_utc_iso, pair, tf, direction, str(entry)])


def category_for(filter_rejected: bool, status: str) -> str:
    s = str(status or "").strip().upper()
    if s == "WIN":
        return "vetoed_winner" if filter_rejected else "winner"
    if s == "LOSS":
        return "vetoed_loser" if filter_rejected else "loser"
    if s == "OPEN_EXPIRED":
        return "vetoed_neutral" if filter_rejected else "executed_open_expired"
    if s in {"ERROR_FETCH_CANDLES", "MISSING_OUTPUT"}:
        return "error"
    return "error"


def send_telegram(text: str) -> Tuple[bool, str]:
    token = (
        os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
        or os.environ.get("TELEGRAM_TOKEN", "").strip()
    )
    chat_id = (
        os.environ.get("TELEGRAM_CHAT_ID", "").strip()
        or os.environ.get("CHAT_ID", "").strip()
    )
    if not token or not chat_id:
        return False, "telegram env missing"

    body = urllib.parse.urlencode(
        {
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": "true",
        }
    ).encode("utf-8")

    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:  # nosec B310
            payload = resp.read().decode("utf-8", errors="replace")
        if '"ok":true' in payload:
            return True, "sent"
        return False, f"telegram api response not ok: {payload[:200]}"
    except Exception as exc:
        return False, f"telegram send exception: {type(exc).__name__}: {exc}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Daily replay audit for BotA alerts.csv using shadow_outcome_simulator.py"
    )
    parser.add_argument(
        "--date",
        default="yesterday",
        help="Audit local date in Europe/Bucharest by default: yesterday|today|YYYY-MM-DD",
    )
    parser.add_argument(
        "--timezone",
        default="Europe/Bucharest",
        help="Local timezone used for date bucketing",
    )
    parser.add_argument(
        "--alerts",
        default=str(DEFAULT_ALERTS),
        help="Path to alerts.csv (relative to ~/BotA if not absolute)",
    )
    parser.add_argument(
        "--pair",
        default="",
        help="Optional pair filter, e.g. EURUSD",
    )
    parser.add_argument(
        "--send-telegram",
        action="store_true",
        help="Send Telegram summary after run",
    )
    args = parser.parse_args()

    audit_date = target_local_date(args.date, args.timezone)

    alerts_path = Path(args.alerts)
    if not alerts_path.is_absolute():
        alerts_path = ROOT / alerts_path

    if not alerts_path.exists():
        print(f"ERROR: alerts file not found: {alerts_path}", file=sys.stderr)
        return 1
    if not SIMULATOR.exists():
        print(f"ERROR: simulator not found: {SIMULATOR}", file=sys.stderr)
        return 1
    if ZoneInfo is None:
        print("ERROR: zoneinfo not available", file=sys.stderr)
        return 1

    pair_filter = str(args.pair or "").strip().upper()
    tz = ZoneInfo(args.timezone)

    selected: List[Dict[str, Any]] = []
    skipped_non_tradeable = 0
    skipped_bad_fields = 0

    with alerts_path.open("r", encoding="utf-8", errors="replace", newline="") as f:
        reader = csv.DictReader(f)
        for raw in reader:
            row = {
                str(k or "").strip().lower(): str(v or "").strip()
                for k, v in raw.items()
                if k is not None
            }

            ts = parse_ts(row.get("timestamp", ""))
            if ts is None:
                continue
            if ts.astimezone(tz).date() != audit_date:
                continue

            pair = row.get("pair", "").upper()
            if pair_filter and pair != pair_filter:
                continue

            direction = row.get("direction", "").upper()
            if direction not in {"BUY", "SELL"}:
                skipped_non_tradeable += 1
                continue

            tf = (row.get("tf") or row.get("timeframe") or "").upper()
            if tf != "M15":
                skipped_non_tradeable += 1
                continue

            entry = safe_float(row.get("entry"))
            sl = safe_float(row.get("sl"))
            tp = safe_float(row.get("tp"))
            if not sl or not tp:
                sl2, tp2 = parse_sl_tp_from_reasons(row.get("reasons", ""))
                sl = sl or safe_float(sl2)
                tp = tp or safe_float(tp2)

            if not entry or not sl or not tp:
                skipped_bad_fields += 1
                continue

            ts_utc_iso = ts.astimezone(timezone.utc).isoformat()
            score = safe_float(row.get("score"))
            adx = safe_float(row.get("adx_raw") or row.get("adx"))
            filter_rejected = truthy(row.get("filter_rejected"))
            reasons = row.get("reasons", "")

            input_row = {
                "timestamp": ts_utc_iso,
                "pair": pair,
                "timeframe": tf,
                "adx": adx,
                "direction_pre_gate": direction,
                "score_partial_pre_gate": score,
                "entry": entry,
                "sl": sl,
                "tp": tp,
                "volatility": row.get("adx_regime") or row.get("volatility") or "unknown",
                "gate_status_current": row.get("filter_reasons") if filter_rejected else "passed",
                "gate_status_shadow": "daily_replay_audit",
                "d1_trend": parse_d1_trend(reasons),
            }

            selected.append(
                {
                    "alert": row,
                    "timestamp_utc": ts_utc_iso,
                    "source_key": build_source_key(ts_utc_iso, pair, tf, direction, entry),
                    "input": input_row,
                }
            )

    REPLAY_DIR.mkdir(parents=True, exist_ok=True)
    audit_tag = audit_date.isoformat()
    pair_tag = pair_filter or "ALL"
    replay_in = REPLAY_DIR / f"replay_input_{audit_tag}_{pair_tag}.jsonl"
    replay_out = REPLAY_DIR / f"replay_output_{audit_tag}_{pair_tag}.jsonl"

    write_jsonl(replay_in, (item["input"] for item in selected), mode="w")
    if replay_out.exists():
        replay_out.unlink()

    sim_stdout = ""
    sim_stderr = ""
    sim_rc = 0

    if selected:
        cmd = [
            sys.executable,
            str(SIMULATOR),
            "--in",
            str(replay_in),
            "--out",
            str(replay_out),
            "--allow-duplicates",
        ]
        if pair_filter:
            cmd.extend(["--pair", pair_filter])

        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(ROOT),
            env=os.environ.copy(),
            check=False,
        )
        sim_stdout = proc.stdout.strip()
        sim_stderr = proc.stderr.strip()
        sim_rc = proc.returncode

        if sim_stdout:
            print(sim_stdout)
        if sim_stderr:
            print(sim_stderr, file=sys.stderr)
        if sim_rc != 0:
            print(f"ERROR: simulator rc={sim_rc}", file=sys.stderr)
            return sim_rc

    outputs = load_jsonl(replay_out)
    out_by_key: Dict[str, Dict[str, Any]] = {}
    for row in outputs:
        key = str(row.get("source_key", "")).strip()
        if key:
            out_by_key[key] = row

    counts = Counter()
    result_rows: List[str] = []

    for item in selected:
        alert = item["alert"]
        sim = out_by_key.get(item["source_key"], {})
        status = str(sim.get("status", "MISSING_OUTPUT"))
        result_pips = safe_float(sim.get("result_pips"))
        category = category_for(truthy(alert.get("filter_rejected")), status)
        counts[category] += 1

        result_rows.append(
            " | ".join(
                [
                    alert.get("timestamp", ""),
                    alert.get("pair", ""),
                    alert.get("tf", ""),
                    alert.get("direction", ""),
                    f"score={alert.get('score', '')}",
                    f"filter_rejected={alert.get('filter_rejected', '')}",
                    f"status={status}",
                    f"pips={result_pips}",
                    f"category={category}",
                ]
            )
        )

    total_signals = len(selected)
    counts["total_signals"] = total_signals
    counts["skipped_non_tradeable"] = skipped_non_tradeable
    counts["skipped_bad_fields"] = skipped_bad_fields

    summary_json = {
        "run_utc": now_utc().isoformat(),
        "audit_date_local": audit_tag,
        "timezone": args.timezone,
        "pair_filter": pair_filter or "ALL",
        "alerts_file": str(alerts_path),
        "replay_input_file": str(replay_in),
        "replay_output_file": str(replay_out),
        "simulator_stdout": sim_stdout,
        "simulator_stderr": sim_stderr,
        "simulator_rc": sim_rc,
        "counts": dict(counts),
    }
    write_jsonl(DEFAULT_SUMMARY_JSONL, [summary_json], mode="a")

    latest_lines = [
        "Daily Replay Audit",
        f"audit_date_local={audit_tag}",
        f"timezone={args.timezone}",
        f"pair_filter={pair_filter or 'ALL'}",
        f"total_signals={total_signals}",
        f"winner={counts.get('winner', 0)}",
        f"loser={counts.get('loser', 0)}",
        f"vetoed_winner={counts.get('vetoed_winner', 0)}",
        f"vetoed_loser={counts.get('vetoed_loser', 0)}",
        f"vetoed_neutral={counts.get('vetoed_neutral', 0)}",
        f"executed_open_expired={counts.get('executed_open_expired', 0)}",
        f"error={counts.get('error', 0)}",
        f"skipped_non_tradeable={skipped_non_tradeable}",
        f"skipped_bad_fields={skipped_bad_fields}",
        f"replay_input_file={replay_in}",
        f"replay_output_file={replay_out}",
        f"simulator_rc={sim_rc}",
        "",
        "Rows:",
    ]
    latest_lines.extend(result_rows if result_rows else ["NO_SIGNALS_FOR_DATE"])
    DEFAULT_SUMMARY_TEXT.write_text("\n".join(latest_lines) + "\n", encoding="utf-8")

    if args.send_telegram:
        tg_lines = [
            "[BotA Daily Replay Audit]",
            f"date={audit_tag} {args.timezone}",
            f"pair={pair_filter or 'ALL'} total={total_signals}",
            f"winner={counts.get('winner', 0)} loser={counts.get('loser', 0)}",
            f"vetoed_winner={counts.get('vetoed_winner', 0)} vetoed_loser={counts.get('vetoed_loser', 0)} vetoed_neutral={counts.get('vetoed_neutral', 0)}",
            f"executed_open_expired={counts.get('executed_open_expired', 0)} error={counts.get('error', 0)}",
            f"log={DEFAULT_SUMMARY_TEXT}",
        ]
        ok, note = send_telegram("\n".join(tg_lines))
        print(f"TELEGRAM={'PASS' if ok else 'FAIL'} {note}")

    print(f"AUDIT_SUMMARY_FILE={DEFAULT_SUMMARY_TEXT}")
    print(f"AUDIT_JSONL_FILE={DEFAULT_SUMMARY_JSONL}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
