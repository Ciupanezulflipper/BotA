#!/usr/bin/env python3
"""Modern evidence-backed end-of-day Telegram report for BotA on Hetzner."""
from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

PAIRS = ("EURUSD", "GBPUSD", "USDJPY")


def code_root() -> Path:
    return Path(os.environ.get("BOTA_CODE_ROOT") or os.environ.get("BOTA_ROOT") or Path.home() / "BotA").expanduser()


def mutable_root() -> Path:
    return Path(os.environ.get("BOTA_MUTABLE_ROOT") or os.environ.get("BOTA_ROOT") or code_root()).expanduser()


def load_env_file(path: Path) -> None:
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip()
        if not key or key[0].isdigit() or not key.replace("_", "a").isalnum():
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        os.environ.setdefault(key, value)


def load_runtime_env() -> None:
    root = code_root()
    for path in (
        root / ".env",
        root / ".env.runtime",
        root / "config" / "strategy.env",
        root / "config" / "signal.env",
        root / "config" / "tele.env",
    ):
        load_env_file(path)


def load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeError):
        return default


def events_for_day(day: str) -> list[dict[str, Any]]:
    path = mutable_root() / "logs" / "pipeline_events.jsonl"
    rows: list[dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as handle:
            for line in handle:
                if day not in line:
                    continue
                try:
                    item = json.loads(line)
                except ValueError:
                    continue
                if isinstance(item, dict) and str(item.get("timestamp_utc", "")).startswith(day):
                    rows.append(item)
    except OSError:
        pass
    return rows


def unique_decisions(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected: dict[tuple[str, str], dict[str, Any]] = {}
    for event in events:
        if event.get("component") != "watcher" or event.get("event_type") != "decision":
            continue
        pair = str(event.get("pair", "")).upper()
        if pair not in PAIRS or str(event.get("timeframe", "")).upper() != "M15":
            continue
        cycle = str(event.get("cycle_id", ""))
        if cycle:
            selected[(cycle, pair)] = event
    return list(selected.values())


def market_open_cycles(events: list[dict[str, Any]]) -> set[str]:
    return {
        str(event.get("cycle_id"))
        for event in events
        if event.get("component") == "watcher"
        and event.get("event_type") == "component"
        and event.get("status") == "completed"
        and event.get("market_reason") == "MARKET_OPEN"
        and event.get("cycle_id")
    }


def outcome_summary(day: str) -> dict[str, Any]:
    base = str(os.environ.get("SUPABASE_URL", "")).rstrip("/")
    key = str(os.environ.get("SUPABASE_SERVICE_KEY", "")).strip()
    if not base or not key:
        return {"available": False}

    start = f"{day}T00:00:00Z"
    next_day = (date.fromisoformat(day) + timedelta(days=1)).isoformat() + "T00:00:00Z"
    query = (
        "signals?closed_at=gte." + urllib.parse.quote(start, safe=":-T")
        + "&closed_at=lt." + urllib.parse.quote(next_day, safe=":-T")
        + "&select=id,pair,direction,entry_price,stop_loss,result_pips,status,closed_at"
    )
    req = urllib.request.Request(
        f"{base}/rest/v1/{query}",
        headers={"apikey": key, "Authorization": f"Bearer {key}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=12) as response:
            rows = json.loads(response.read().decode("utf-8"))
    except (OSError, ValueError, urllib.error.HTTPError):
        return {"available": False}
    if not isinstance(rows, list):
        return {"available": False}

    wins = losses = cancelled = resolved_r = 0
    net_r = 0.0
    for row in rows:
        status = str(row.get("status", "")).upper()
        result_pips = float(row.get("result_pips") or 0.0)
        if status == "CANCELLED":
            cancelled += 1
            continue
        if result_pips > 0:
            wins += 1
        elif result_pips < 0:
            losses += 1
        pair = str(row.get("pair", "")).upper()
        entry = float(row.get("entry_price") or 0.0)
        sl = float(row.get("stop_loss") or 0.0)
        pip = 0.01 if "JPY" in pair else 0.0001
        risk_pips = abs(entry - sl) / pip if entry and sl else 0.0
        if risk_pips > 0:
            net_r += result_pips / risk_pips
            resolved_r += 1

    active_req = urllib.request.Request(
        f"{base}/rest/v1/signals?status=eq.ACTIVE&select=id",
        headers={"apikey": key, "Authorization": f"Bearer {key}"},
    )
    try:
        with urllib.request.urlopen(active_req, timeout=12) as response:
            active_rows = json.loads(response.read().decode("utf-8"))
        active = len(active_rows) if isinstance(active_rows, list) else -1
    except (OSError, ValueError, urllib.error.HTTPError):
        active = -1

    return {
        "available": True,
        "wins": wins,
        "losses": losses,
        "cancelled": cancelled,
        "active": active,
        "net_r": net_r,
        "resolved_r": resolved_r,
    }


def render(day: str) -> str:
    root = mutable_root()
    health = load_json(root / "state" / "vps_orchestrator_health.json", {})
    events = events_for_day(day)
    decisions = unique_decisions(events)
    cycles = market_open_cycles(events)

    per_pair = {pair: {"scans": 0, "qualified": 0} for pair in PAIRS}
    delivered = 0
    for event in decisions:
        pair = str(event.get("pair", "")).upper()
        per_pair[pair]["scans"] += 1
        rejected = event.get("filter_rejected") is True
        if not rejected and str(event.get("outcome", "")).lower() not in {"filter_rejected", "hold"}:
            per_pair[pair]["qualified"] += 1
        if str(event.get("telegram_result", "")).lower() in {"sent", "reconciled_sent", "pass", "success"}:
            delivered += 1

    expected = len(cycles) * len(PAIRS)
    completed = len(decisions)
    health_ok = (
        isinstance(health, dict)
        and health.get("lifecycle") == "RUNNING"
        and health.get("process_liveness") is True
        and bool(health.get("release_git_sha"))
    )
    release = str(health.get("release_git_sha", "UNKNOWN"))
    useful = health.get("useful_progress") if isinstance(health.get("useful_progress"), dict) else {}
    updater = useful.get("updater") if isinstance(useful.get("updater"), dict) else {}
    watcher = useful.get("watcher") if isinstance(useful.get("watcher"), dict) else {}

    policy_failures = sum(
        1 for event in decisions
        if "production_policy_failure" in str(event.get("rejection_gate", ""))
    )
    issues: list[str] = []
    if not health_ok:
        issues.append("runtime health not proven")
    if not cycles:
        issues.append("no market-open watcher cycles recorded")
    if expected and completed != expected:
        issues.append(f"scan gap {completed}/{expected}")
    if cycles and any(data["scans"] == 0 for data in per_pair.values()):
        issues.append("one or more pairs missing")
    if updater.get("status") != "PASS":
        issues.append("latest updater not PASS")
    if watcher.get("status") != "PASS":
        issues.append("latest watcher not PASS")
    if policy_failures:
        issues.append(f"production_policy_failure={policy_failures}")

    qualified_total = sum(data["qualified"] for data in per_pair.values())
    status = "NORMAL" if not issues else "ATTENTION"
    lines = [
        "📊 BOTA · DAILY MARKET REPORT",
        f"{datetime.strptime(day, '%Y-%m-%d').strftime('%d %b %Y')} · Session summary",
        "",
        f"{'🟢' if health_ok else '🔴'} System: {'ONLINE' if health_ok else 'ATTENTION'}",
        f"Market-open cycles: {len(cycles)}",
        f"Scans: {completed}/{expected if expected else 0} completed",
        "",
    ]
    for pair in PAIRS:
        pretty = f"{pair[:3]}/{pair[3:]}"
        data = per_pair[pair]
        lines.append(f"{pretty} — {data['scans']} scans · {data['qualified']} qualified")

    lines += ["", f"Signals: {qualified_total} qualified · {delivered} Telegram-confirmed"]
    results = outcome_summary(day)
    if results.get("available"):
        active = results["active"]
        lines.append(
            f"Results: {results['wins']}W · {results['losses']}L · "
            f"{results['cancelled']} cancelled · {active if active >= 0 else 'unknown'} active"
        )
        lines.append(
            f"Net: {results['net_r']:+.2f}R"
            if results["resolved_r"]
            else "Net: no resolved R outcomes today"
        )
    else:
        lines.append("Results: unavailable from outcome store")

    if qualified_total == 0 and not issues:
        lines += ["", "0 signals — market scanned normally; no setup satisfied BotA policy."]

    lines += [
        "",
        f"Data/runtime issues: {'; '.join(issues) if issues else 'None'}",
        f"Release: {release[:12] if release != 'UNKNOWN' else release}",
        "",
        f"{'✅' if status == 'NORMAL' else '⚠️'} Status: {status}",
    ]
    return "\n".join(lines)


def send_telegram(text: str) -> bool:
    token = os.environ.get("TELEGRAM_BOT_TOKEN") or os.environ.get("TELEGRAM_TOKEN") or ""
    chat_id = os.environ.get("TELEGRAM_CHAT_ID") or os.environ.get("CHAT_ID") or ""
    if not token or not chat_id:
        print("TELEGRAM_SEND=SKIPPED reason=missing_token_or_chat")
        return False
    data = urllib.parse.urlencode({"chat_id": chat_id, "text": text, "disable_web_page_preview": "true"}).encode("utf-8")
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, ValueError, urllib.error.HTTPError):
        print("TELEGRAM_SEND=FAIL")
        return False
    ok = isinstance(payload, dict) and payload.get("ok") is True
    print("TELEGRAM_SEND=PASS" if ok else "TELEGRAM_SEND=FAIL")
    return ok


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=os.environ.get("SUMMARY_DATE") or datetime.now(timezone.utc).date().isoformat())
    parser.add_argument("--render-only", action="store_true")
    args = parser.parse_args()
    load_runtime_env()
    text = render(args.date)
    print(text)
    if args.render_only or os.environ.get("DAILY_SUMMARY_SEND", "1") == "0":
        print("TELEGRAM_SEND=SKIPPED render_only=1")
        return 0
    ok = send_telegram(text)
    log = mutable_root() / "logs" / "daily_summary.log"
    try:
        log.parent.mkdir(parents=True, exist_ok=True)
        with log.open("a", encoding="utf-8") as handle:
            handle.write(f"[{datetime.now(timezone.utc).isoformat()}] DAILY_MARKET_REPORT\n{text}\n\n")
    except OSError:
        pass
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
