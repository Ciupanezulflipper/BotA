#!/usr/bin/env python3
"""Render/send the professional BotA end-of-day Telegram report.

Presentation/measurement only: this script does not alter strategy, thresholds,
pairs, timeframes, cooldowns, SL/TP, watcher decisions, or signal state.
"""
from __future__ import annotations

import argparse
import csv
import http.client
import json
import os
import urllib.parse
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PAIRS = ("EURUSD", "GBPUSD", "USDJPY")
TELEGRAM_HOST = "api.telegram.org"


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError, OverflowError):
        return default


def _truthy(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "on"}


def _load_env_file(path: Path) -> None:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        key, value = line.split("=", 1)
        key = key.strip()
        if not key.replace("_", "a").isalnum() or key[:1].isdigit():
            continue
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def _row_is_day(value: str, day: str) -> bool:
    text = str(value or "").strip()
    if text.startswith(day):
        return True
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return False
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).strftime("%Y-%m-%d") == day


def read_alerts(path: Path, day: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    try:
        with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
            reader = csv.reader(handle)
            for values in reader:
                if len(values) < 13 or values[0].lower().startswith(("ts", "timestamp")):
                    continue
                if not _row_is_day(values[0], day):
                    continue
                rows.append(
                    {
                        "ts": values[0],
                        "pair": values[1].upper(),
                        "tf": values[2].upper(),
                        "direction": values[3].upper(),
                        "score": _safe_float(values[4]),
                        "confidence": _safe_float(values[5]),
                        "entry": values[6],
                        "sl": values[7],
                        "tp": values[8],
                        "rejected": _truthy(values[10]),
                        "filter_reasons": values[11],
                    }
                )
    except (OSError, csv.Error):
        return []
    return rows


def read_pipeline_events(path: Path, day: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    if not path.exists():
        return events
    try:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                try:
                    item = json.loads(line)
                except ValueError:
                    continue
                if not isinstance(item, dict):
                    continue
                if not str(item.get("timestamp_utc", "")).startswith(day):
                    continue
                events.append(item)
    except OSError:
        return []
    return events


def _unique_signals(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, ...]] = set()
    output: list[dict[str, Any]] = []
    for row in rows:
        if row["direction"] not in {"BUY", "SELL"} or row["rejected"]:
            continue
        identity = (
            row["pair"],
            row["tf"],
            row["direction"],
            f"{row['score']:.2f}",
            row["entry"],
            row["sl"],
            row["tp"],
        )
        if identity in seen:
            continue
        seen.add(identity)
        output.append(row)
    return output


def _health(mutable_root: Path) -> dict[str, Any]:
    for name in ("vps_orchestrator_health.json", "runtime_health.json"):
        value = _load_json(mutable_root / "state" / name)
        if value:
            return value
    return {}


def _pair_display(pair: str) -> str:
    return f"{pair[:3]}/{pair[3:]}" if len(pair) == 6 else pair


def _watcher_cycle_ids(events: list[dict[str, Any]]) -> set[str]:
    cycle_ids = {
        str(event.get("cycle_id"))
        for event in events
        if event.get("component") == "watcher"
        and event.get("event_type") == "component"
        and event.get("status") == "completed"
        and event.get("market_reason") == "MARKET_OPEN"
    }
    cycle_ids.discard("")
    return cycle_ids


def _delivery_stats(events: list[dict[str, Any]]) -> tuple[set[tuple[str, str, str, str]], int]:
    delivered: set[tuple[str, str, str, str]] = set()
    failures = 0
    for event in events:
        if event.get("event_type") != "decision":
            continue
        result = str(event.get("telegram_result", "")).lower()
        identity = (
            str(event.get("pair", "")),
            str(event.get("timeframe", "")),
            str(event.get("outcome", "")),
            str(event.get("server_epoch", "")),
        )
        if result in {"sent", "reconciled_sent", "pass", "success"}:
            delivered.add(identity)
        elif result in {"failed", "definite_failure", "unknown_outcome"}:
            failures += 1
    return delivered, failures


def _runtime_snapshot(health: dict[str, Any]) -> tuple[bool, str, str, str]:
    lifecycle = str(health.get("lifecycle", health.get("bot_mode", "UNKNOWN"))).upper()
    process_liveness = health.get("process_liveness")
    online = lifecycle in {"RUNNING", "HEALTHY"} and process_liveness is not False
    release = str(health.get("release_git_sha", "unknown"))
    runtime_instance = str(health.get("runtime_instance_id", "unknown"))
    return online, lifecycle, release, runtime_instance


def _day_label(day: str) -> str:
    try:
        return datetime.strptime(day, "%Y-%m-%d").strftime("%d %b %Y").upper()
    except ValueError:
        return day


def _pair_activity_lines(pair_scans: Counter[str], pair_qualified: Counter[str]) -> list[str]:
    return [
        f"{_pair_display(pair)} · {pair_scans[pair]} scans · {pair_qualified[pair]} qualified"
        for pair in PAIRS
    ]


def _session_summary_lines(
    *,
    clean_collection: bool,
    qualified: list[dict[str, Any]],
    delivered_count: int,
) -> list[str]:
    if clean_collection and not qualified:
        return ["0 signals — market scanned normally; no setup satisfied BotA policy."]
    if not qualified:
        return ["No qualified signals recorded; collection evidence is incomplete or requires review."]
    by_direction = Counter(row["direction"] for row in qualified)
    lines = [
        f"{len(qualified)} unique qualified setup(s): "
        f"{by_direction['BUY']} BUY · {by_direction['SELL']} SELL."
    ]
    if delivered_count == 0:
        lines.append("No Telegram delivery confirmation is present in today's decision ledger.")
    return lines


def _quality_issues(
    *,
    online: bool,
    watcher_cycles: set[str],
    pair_scans: Counter[str],
    delivery_failures: int,
) -> list[str]:
    issues: list[str] = []
    if not online:
        issues.append("runtime not proven online")
    if not watcher_cycles:
        issues.append("no market-open watcher completion")
    missing_pairs = [pair for pair in PAIRS if pair_scans[pair] == 0]
    if missing_pairs:
        issues.append("missing pair activity: " + ", ".join(missing_pairs))
    if delivery_failures:
        issues.append(f"Telegram delivery failures: {delivery_failures}")
    return issues


def build_report(
    *,
    day: str,
    alerts: list[dict[str, Any]],
    events: list[dict[str, Any]],
    health: dict[str, Any],
) -> str:
    pair_scans = Counter(row["pair"] for row in alerts if row["pair"] in PAIRS)
    qualified = _unique_signals(alerts)
    pair_qualified = Counter(row["pair"] for row in qualified)
    watcher_cycles = _watcher_cycle_ids(events)
    delivered_identities, delivery_failures = _delivery_stats(events)
    online, lifecycle, release, runtime_instance = _runtime_snapshot(health)

    all_pairs_seen = all(pair_scans[pair] > 0 for pair in PAIRS)
    clean_collection = online and all_pairs_seen and bool(watcher_cycles)
    status_icon = "🟢" if clean_collection else "🟠"
    status_text = "NORMAL" if clean_collection else "REVIEW REQUIRED"
    issues = _quality_issues(
        online=online,
        watcher_cycles=watcher_cycles,
        pair_scans=pair_scans,
        delivery_failures=delivery_failures,
    )

    lines = [
        "📊 BOTA · DAILY MARKET REPORT",
        f"{_day_label(day)} · UTC",
        "",
        f"{status_icon} SYSTEM STATUS",
        f"Runtime: {'ONLINE' if online else lifecycle or 'UNKNOWN'}",
        f"Market-open watcher cycles: {len(watcher_cycles)}",
        f"Release: {release[:12] if release != 'unknown' else 'unknown'}",
        "",
        "📈 PAIR ACTIVITY",
        *_pair_activity_lines(pair_scans, pair_qualified),
        "",
        "🎯 SIGNALS",
        f"Qualified setups: {len(qualified)}",
        f"Telegram confirmed: {len(delivered_identities)}",
    ]
    if delivery_failures:
        lines.append(f"Delivery issues: {delivery_failures}")

    lines.extend(["", "🧾 SESSION SUMMARY"])
    lines.extend(
        _session_summary_lines(
            clean_collection=clean_collection,
            qualified=qualified,
            delivered_count=len(delivered_identities),
        )
    )
    lines.extend(
        [
            "",
            "⚙️ DATA QUALITY",
            f"All 3 pairs observed: {'YES' if all_pairs_seen else 'NO'}",
            f"Runtime issues: {'None observed' if not issues else '; '.join(issues)}",
            f"Runtime instance: {runtime_instance[:8] if runtime_instance != 'unknown' else 'unknown'}",
            "",
            f"BOTA • STATUS: {status_text}",
        ]
    )
    return "\n".join(lines)


def _telegram_credentials() -> tuple[str, str]:
    token = os.environ.get("TELEGRAM_BOT_TOKEN") or os.environ.get("TELEGRAM_TOKEN") or ""
    chat_id = os.environ.get("TELEGRAM_CHAT_ID") or os.environ.get("CHAT_ID") or ""
    if not token or not chat_id:
        raise ValueError("missing_token_or_chat")
    return token, chat_id


def send_report(text: str) -> bool:
    token, chat_id = _telegram_credentials()
    body = urllib.parse.urlencode(
        {"chat_id": chat_id, "text": text, "disable_web_page_preview": "true"}
    ).encode("utf-8")
    connection = http.client.HTTPSConnection(TELEGRAM_HOST, timeout=20)
    try:
        connection.request(
            "POST",
            f"/bot{token}/sendMessage",
            body=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        response = connection.getresponse()
        payload = json.loads(response.read().decode("utf-8"))
    except (OSError, ValueError, http.client.HTTPException):
        return False
    finally:
        connection.close()
    return 200 <= response.status < 300 and isinstance(payload, dict) and payload.get("ok") is True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--send", action="store_true")
    parser.add_argument("--date", default="")
    args = parser.parse_args()

    code_root = Path(
        os.environ.get("BOTA_CODE_ROOT") or os.environ.get("BOTA_ROOT") or str(Path.home() / "BotA")
    ).expanduser().resolve()
    mutable_root = Path(os.environ.get("BOTA_MUTABLE_ROOT", str(code_root))).expanduser().resolve()

    for env_file in (
        code_root / ".env",
        code_root / ".env.runtime",
        code_root / "config" / "signal.env",
        code_root / "config" / "tele.env",
    ):
        _load_env_file(env_file)

    day = args.date or os.environ.get("SUMMARY_DATE") or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    alerts = read_alerts(mutable_root / "logs" / "alerts.csv", day)
    events = read_pipeline_events(mutable_root / "logs" / "pipeline_events.jsonl", day)
    health = _health(mutable_root)
    report = build_report(day=day, alerts=alerts, events=events, health=health)
    print(report)

    if not args.send or os.environ.get("DAILY_SUMMARY_SEND", "1") == "0":
        print("TELEGRAM_SEND=SKIPPED")
        return 0

    try:
        ok = send_report(report)
    except ValueError:
        ok = False
    print("TELEGRAM_SEND=PASS" if ok else "TELEGRAM_SEND=FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
