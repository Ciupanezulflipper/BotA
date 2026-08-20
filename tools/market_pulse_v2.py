#!/usr/bin/env python3
"""BotA three-pair user-facing market pulse.

Purpose:
- provide a concise Telegram status for EURUSD, GBPUSD and USDJPY;
- summarize the authoritative pipeline decision ledger instead of triggering
  another strategy evaluation;
- distinguish no-setup from stale/data-failure conditions;
- retry scheduled sends after definite connectivity failures;
- never blindly retry a Telegram request after an unknown outcome.

This module does not change strategy, thresholds, scoring, risk, provider policy,
or trade-alert delivery semantics.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import socket
import ssl
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

PAIRS = ("EURUSD", "GBPUSD", "USDJPY")
TIMEFRAME = "M15"
FRESH_SECONDS = 1500
PULSE_WEEKDAYS = {0, 2, 4}  # Monday, Wednesday, Friday
PULSE_START_HOUR_UTC = 8
PULSE_END_HOUR_UTC = 18
UNKNOWN_OUTCOME_RC = 75
RETRYABLE_FAILURE_RC = 2


def root_dir() -> Path:
    configured = os.environ.get("BOTA_ROOT", "").strip()
    return Path(configured).expanduser() if configured else Path(__file__).resolve().parent.parent


def boot_id() -> str:
    try:
        return Path("/proc/sys/kernel/random/boot_id").read_text(encoding="utf-8").strip()
    except OSError:
        return "unknown"


def monotonic_ns() -> int:
    clock = getattr(time, "CLOCK_BOOTTIME", None)
    return time.clock_gettime_ns(clock) if clock is not None else time.monotonic_ns()


def load_pipeline_state() -> dict[str, Any]:
    path = root_dir() / "state" / "pipeline_progress.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _event_age_seconds(event: dict[str, Any], now_ns: int) -> int | None:
    try:
        event_ns = int(event["monotonic_ns"])
    except (KeyError, TypeError, ValueError):
        return None
    delta = now_ns - event_ns
    return None if delta < 0 else delta // 1_000_000_000


def estimated_utc_now(state: dict[str, Any]) -> tuple[datetime, str]:
    """Estimate current UTC from the freshest trusted server epoch in the ledger."""
    current_boot = boot_id()
    now_ns = monotonic_ns()
    candidates: list[tuple[int, int]] = []

    components = state.get("components")
    if isinstance(components, dict) and state.get("boot_id") == current_boot:
        for raw in components.values():
            if not isinstance(raw, dict):
                continue
            try:
                event_ns = int(raw.get("monotonic_ns") or 0)
                server_epoch = int(raw.get("server_epoch") or 0)
            except (TypeError, ValueError):
                continue
            if event_ns > 0 and server_epoch > 1_000_000_000 and now_ns >= event_ns:
                candidates.append((event_ns, server_epoch))

    if candidates:
        event_ns, server_epoch = max(candidates)
        elapsed = (now_ns - event_ns) / 1_000_000_000
        return (
            datetime.fromtimestamp(server_epoch, tz=timezone.utc) + timedelta(seconds=elapsed),
            "ledger_server_epoch",
        )

    return datetime.now(timezone.utc), "local_utc_fallback"


def pair_display(pair: str) -> str:
    return f"{pair[:3]}/{pair[3:]}" if len(pair) == 6 else pair


def friendly_reason(event: dict[str, Any]) -> str:
    raw = " ".join(
        str(event.get(key) or "")
        for key in ("outcome", "rejection_gate", "terminal_outcome", "market_reason")
    ).lower()

    mappings = (
        (("candle_stale", "data_stale"), "Market data is stale"),
        (("raw_cache_invalid", "data_fetch_failed"), "Market data unavailable"),
        (("news_gate", "calendar_gate"), "News filter blocked the setup"),
        (("h1_trend_neutral", "h1"), "Awaiting H1 confirmation"),
        (("score",), "Score below trade threshold"),
        (("adx",), "Trend strength below threshold"),
        (("rr", "risk/reward"), "Risk/reward requirement not met"),
        (("direction_not_tradeable", "hold"), "No tradeable direction"),
        (("pause_guard",), "Trading pause is active"),
        (("parse_error",), "Decision data could not be parsed"),
    )
    for needles, label in mappings:
        if any(needle in raw for needle in needles):
            return label
    return "No setup passed all filters"


def classify_pair(
    pair: str,
    event: dict[str, Any] | None,
    state_boot: str,
    current_boot: str,
    now_ns: int,
) -> dict[str, Any]:
    if not isinstance(event, dict):
        return {
            "pair": pair,
            "state": "data_issue",
            "headline": "⚠️ No recent scan",
            "detail": "No decision recorded",
            "age_seconds": None,
            "score": None,
            "provider": "",
        }

    age = _event_age_seconds(event, now_ns) if state_boot == current_boot else None
    status = str(event.get("status") or "missing")
    outcome = str(event.get("outcome") or "missing")
    terminal = str(event.get("terminal_outcome") or "")
    rejected = event.get("filter_rejected") is True
    score = event.get("score")
    provider = str(event.get("provider") or "")
    raw = f"{outcome} {terminal}".lower()

    if age is None or age > FRESH_SECONDS or status != "completed":
        if age is None:
            detail = "No fresh decision on this boot"
        else:
            detail = f"Last decision {max(1, age // 60)}m ago"
        return {
            "pair": pair,
            "state": "data_issue",
            "headline": "⚠️ Scan stale",
            "detail": detail,
            "age_seconds": age,
            "score": score,
            "provider": provider,
        }

    if any(token in raw for token in ("raw_cache_invalid", "candle_stale", "data_fetch")):
        return {
            "pair": pair,
            "state": "data_issue",
            "headline": "⚠️ Data issue",
            "detail": friendly_reason(event),
            "age_seconds": age,
            "score": score,
            "provider": provider,
        }

    if not rejected and bool(event.get("alerts_csv_persisted")):
        detail = "Trade alert handled separately"
        telegram = str(event.get("telegram_result") or "")
        if "sent" in telegram.lower():
            detail = "Trade alert sent"
        return {
            "pair": pair,
            "state": "qualified",
            "headline": "🟢 Qualified setup",
            "detail": detail,
            "age_seconds": age,
            "score": score,
            "provider": provider,
        }

    return {
        "pair": pair,
        "state": "no_setup",
        "headline": "⚪ No setup",
        "detail": friendly_reason(event),
        "age_seconds": age,
        "score": score,
        "provider": provider,
    }


def build_pair_rows(state: dict[str, Any]) -> list[dict[str, Any]]:
    decisions = state.get("decisions")
    if not isinstance(decisions, dict):
        decisions = {}
    now_ns = monotonic_ns()
    current_boot = boot_id()
    state_boot = str(state.get("boot_id") or "")
    return [
        classify_pair(
            pair,
            decisions.get(f"{pair}:{TIMEFRAME}"),
            state_boot,
            current_boot,
            now_ns,
        )
        for pair in PAIRS
    ]


def _score_text(value: Any) -> str:
    try:
        return f"Score {float(value):.0f}"
    except (TypeError, ValueError):
        return "Score —"


def format_message(rows: list[dict[str, Any]], generated_at: datetime) -> str:
    lines = [
        "📡 BOTA · MARKET CHECK",
        generated_at.strftime("%a %d %b · %H:%M UTC"),
        "",
    ]

    for row in rows:
        age = row.get("age_seconds")
        age_text = "scan —" if age is None else f"scan {max(0, int(age)) // 60}m ago"
        provider = str(row.get("provider") or "").upper()
        meta = f"{_score_text(row.get('score'))} · {age_text}"
        if provider and provider != "UNKNOWN":
            meta += f" · {provider}"

        lines.extend(
            [
                pair_display(str(row["pair"])),
                str(row["headline"]),
                str(row["detail"]),
                meta,
                "",
            ]
        )

    qualified = sum(row["state"] == "qualified" for row in rows)
    clean = sum(row["state"] == "no_setup" for row in rows)
    issues = sum(row["state"] == "data_issue" for row in rows)
    lines.extend(
        [
            f"3 pairs · {qualified} qualified · {clean} no setup · {issues} data issue",
            "Trade alerts are sent separately.",
        ]
    )
    return "\n".join(lines)


def pulse_state_dir() -> Path:
    path = root_dir() / "state" / "market_pulse_v2"
    path.mkdir(parents=True, exist_ok=True)
    return path


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    temp = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, sort_keys=True, separators=(",", ":"))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
        dir_fd = os.open(str(path.parent), os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    finally:
        try:
            temp.unlink()
        except FileNotFoundError:
            pass


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def scheduled_window(now: datetime) -> bool:
    return (
        now.weekday() in PULSE_WEEKDAYS
        and PULSE_START_HOUR_UTC <= now.hour <= PULSE_END_HOUR_UTC
    )


def telegram_send(text: str, token: str, chat_id: str) -> tuple[str, int | None, str]:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = urllib.parse.urlencode({"chat_id": chat_id, "text": text}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            body = response.read().decode("utf-8", errors="replace")
            data = json.loads(body)
            if data.get("ok") is True:
                message_id = data.get("result", {}).get("message_id")
                return "sent", int(message_id) if isinstance(message_id, int) else None, ""
            return "retryable_failure", None, "telegram_ok_false"
    except urllib.error.HTTPError as exc:
        return "retryable_failure", None, f"http_{exc.code}"
    except urllib.error.URLError as exc:
        reason = exc.reason
        text_reason = str(reason).lower()
        if isinstance(reason, (socket.gaierror, ssl.SSLError)):
            return "retryable_failure", None, type(reason).__name__
        if any(
            token_text in text_reason
            for token_text in (
                "name or service not known",
                "temporary failure in name resolution",
                "no address associated with hostname",
                "certificate verify failed",
                "connection refused",
                "network is unreachable",
            )
        ):
            return "retryable_failure", None, type(reason).__name__
        if "timed out" in text_reason:
            return "unknown_outcome", None, "timeout"
        return "retryable_failure", None, type(reason).__name__
    except (TimeoutError, socket.timeout):
        return "unknown_outcome", None, "timeout"
    except Exception as exc:  # defensive: ambiguous after request handoff
        return "unknown_outcome", None, type(exc).__name__


def scheduled_send() -> int:
    state = load_pipeline_state()
    now, time_source = estimated_utc_now(state)
    if not scheduled_window(now):
        print(f"MARKET_PULSE=SKIP_OUTSIDE_WINDOW utc={now.isoformat()} source={time_source}")
        return 0

    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        print("MARKET_PULSE=CONFIG_MISSING")
        return 2

    directory = pulse_state_dir()
    day_key = now.strftime("%Y-%m-%d")
    state_file = directory / f"{day_key}.json"
    lock_file = directory / "send.lock"

    with lock_file.open("a+") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        prior = load_json(state_file)
        prior_status = str(prior.get("status") or "")
        if prior_status == "sent":
            print(f"MARKET_PULSE=ALREADY_SENT date={day_key}")
            return 0
        if prior_status == "unknown_outcome":
            print(f"MARKET_PULSE=BLOCKED_UNKNOWN_OUTCOME date={day_key}")
            return UNKNOWN_OUTCOME_RC

        rows = build_pair_rows(state)
        message = format_message(rows, now)
        atomic_json(
            state_file,
            {
                "schema": 1,
                "status": "intent",
                "date": day_key,
                "time_source": time_source,
                "created_at": now.isoformat(),
            },
        )

        status, message_id, reason = telegram_send(message, token, chat_id)
        atomic_json(
            state_file,
            {
                "schema": 1,
                "status": status,
                "date": day_key,
                "time_source": time_source,
                "updated_at": estimated_utc_now(load_pipeline_state())[0].isoformat(),
                "message_id": message_id,
                "reason": reason,
            },
        )

        if status == "sent":
            print(f"MARKET_PULSE=SENT date={day_key} message_id={message_id}")
            return 0
        if status == "unknown_outcome":
            print(f"MARKET_PULSE=UNKNOWN_OUTCOME date={day_key} reason={reason}")
            return UNKNOWN_OUTCOME_RC

        print(f"MARKET_PULSE=RETRYABLE_FAILURE date={day_key} reason={reason}")
        return RETRYABLE_FAILURE_RC


def shadow_preview() -> int:
    state = load_pipeline_state()
    now, source = estimated_utc_now(state)
    rows = build_pair_rows(state)
    print(format_message(rows, now))
    print(f"\n[preview] time_source={source}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--shadow", action="store_true")
    group.add_argument("--scheduled-send", action="store_true")
    args = parser.parse_args()
    return scheduled_send() if args.scheduled_send else shadow_preview()


if __name__ == "__main__":
    raise SystemExit(main())
