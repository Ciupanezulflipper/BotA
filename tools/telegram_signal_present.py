#!/usr/bin/env python3
"""Render BotA watcher alerts in a modern Telegram forex-channel style.

Presentation only: this module does not change qualification, thresholds, prices,
SL/TP, cooldown, delivery identity, or strategy semantics.
"""
from __future__ import annotations

import csv
import io
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PAIR_RE = re.compile(r"\bBotA\s+([A-Z]{6})\s+([A-Z0-9]+)\s+(BUY|SELL)\b")
SCORE_RE = re.compile(r"(?:Score:\s*|score=)([0-9]+(?:\.[0-9]+)?)", re.I)
ENTRY_RE = re.compile(r"Entry:\s*([0-9]+(?:\.[0-9]+)?)", re.I)
SL_RE = re.compile(r"(?:SL|Stop Loss):\s*([0-9]+(?:\.[0-9]+)?)", re.I)
TP_RE = re.compile(r"(?:TP|Take Profit):\s*([0-9]+(?:\.[0-9]+)?)", re.I)
CURRENT_FIELDS = (
    "ts", "pair", "tf", "direction", "score", "confidence", "entry", "sl", "tp",
    "provider", "filter_rejected", "filter_reasons", "reasons", "ema_comp",
    "rsi_comp", "macd_comp", "adx_comp", "adx_raw", "rsi_raw", "macd_hist_raw",
    "macro6", "h1_trend", "tier", "session", "adx_regime",
)


def as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return default


def pair_display(pair: str) -> str:
    return f"{pair[:3]}/{pair[3:]}" if len(pair) == 6 else pair


def mutable_root() -> Path:
    return Path(
        os.environ.get("BOTA_MUTABLE_ROOT")
        or os.environ.get("BOTA_ROOT")
        or Path.home() / "BotA"
    ).expanduser()


def now_utc() -> datetime:
    raw = str(os.environ.get("BOTA_SERVER_EPOCH", "")).strip()
    if raw.isdigit() and int(raw) > 1_000_000_000:
        return datetime.fromtimestamp(int(raw), timezone.utc)
    return datetime.now(timezone.utc)


def parse_legacy(message: str) -> dict[str, str]:
    text = message.replace("\\n", "\n")
    identity = PAIR_RE.search(text)
    score = SCORE_RE.search(text)
    if not identity or not score:
        raise ValueError("legacy_message_identity_unparseable")
    entry = ENTRY_RE.search(text)
    sl = SL_RE.search(text)
    tp = TP_RE.search(text)
    return {
        "pair": identity.group(1),
        "tf": identity.group(2).upper(),
        "direction": identity.group(3),
        "score": score.group(1),
        "entry": entry.group(1) if entry else "",
        "sl": sl.group(1) if sl else "",
        "tp": tp.group(1) if tp else "",
        "watchlist": "1" if "watchlist" in text.lower() else "0",
    }


def current_row(identity: dict[str, str]) -> dict[str, str] | None:
    alerts = mutable_root() / "logs" / "alerts.csv"
    raw_offset = str(os.environ.get("BOTA_ALERTS_OFFSET", "")).strip()
    if not raw_offset.isdigit():
        return None
    try:
        offset = int(raw_offset)
        size = alerts.stat().st_size
        if offset < 0 or offset > size or size - offset > 262_144:
            return None
        with alerts.open("rb") as handle:
            handle.seek(offset)
            segment = handle.read().decode("utf-8", "strict")
    except (OSError, UnicodeDecodeError):
        return None

    selected = None
    for values in csv.reader(io.StringIO(segment)):
        if len(values) != len(CURRENT_FIELDS):
            continue
        row = dict(zip(CURRENT_FIELDS, values, strict=True))
        if row["pair"].upper() != identity["pair"] or row["tf"].upper() != identity["tf"]:
            continue
        if row["direction"].upper() != identity["direction"]:
            continue
        if str(row["filter_rejected"]).strip().lower() in {"1", "true", "yes", "y"}:
            continue
        if abs(as_float(row["score"]) - as_float(identity["score"])) > 0.011:
            continue
        if identity["entry"] and abs(as_float(row["entry"]) - as_float(identity["entry"])) > 0.000001:
            continue
        selected = row
    return selected


def rr(direction: str, entry: float, sl: float, tp: float) -> str:
    if min(entry, sl, tp) <= 0:
        return ""
    risk, reward = ((entry - sl, tp - entry) if direction == "BUY" else (sl - entry, entry - tp))
    if risk <= 0 or reward <= 0:
        return ""
    return f"1:{reward / risk:.2f}"


def setup_label(reasons: str) -> str:
    value = reasons.lower()
    if "pullback_entry" in value:
        return "Pullback entry"
    if "breakout" in value:
        return "Breakout"
    if "divergence" in value:
        return "Divergence"
    return ""


def render(message: str) -> str:
    identity = parse_legacy(message)
    row = current_row(identity)
    pair, tf, direction = identity["pair"], identity["tf"], identity["direction"]
    score = as_float(identity["score"])
    entry, sl, tp = as_float(identity["entry"]), as_float(identity["sl"]), as_float(identity["tp"])
    if row:
        entry, sl, tp = as_float(row.get("entry"), entry), as_float(row.get("sl"), sl), as_float(row.get("tp"), tp)

    watchlist = identity["watchlist"] == "1" or min(entry, sl, tp) <= 0
    emoji = "🟢" if direction == "BUY" else "🔴"
    title = f"{emoji} BOTA · {direction} SIGNAL" if not watchlist else "🟡 BOTA · WATCHLIST"
    lines = [title, "", f"{pair_display(pair)} · {tf}", ""]

    if watchlist:
        lines.append(f"Direction: {direction}")
    else:
        decimals = 3 if "JPY" in pair else 5
        lines += [
            f"🎯 Entry: {entry:.{decimals}f}",
            f"🛑 Stop Loss: {sl:.{decimals}f}",
            f"💰 Take Profit: {tp:.{decimals}f}",
        ]
        rr_text = rr(direction, entry, sl, tp)
        if rr_text:
            lines.append(f"⚖️ R:R: {rr_text}")

    lines += ["", f"Signal Score: {score:.0f}/100"]
    if row:
        h1 = str(row.get("h1_trend", "")).strip()
        adx = as_float(row.get("adx_raw"), -1)
        session = str(row.get("session", "")).strip().replace("_", " ")
        regime = str(row.get("adx_regime", "")).strip()
        setup = setup_label(str(row.get("reasons", "")))
        if h1:
            lines.append(f"H1: {h1}")
        if adx >= 0:
            lines.append(f"ADX: {adx:.1f}")
        if session:
            lines.append(f"Session: {session}")
        if regime:
            lines.append(f"Regime: {regime.title()}")
        if setup:
            lines += ["", f"Setup: {setup}"]

    if watchlist:
        lines += ["", "Waiting for full BotA confirmation."]

    stamp = now_utc().strftime("%H:%M UTC · %d %b %Y")
    # Final identity line intentionally preserves the existing crash-consistent
    # Telegram guard parser contract.
    lines += ["", f"🕒 {stamp}", f"BotA {pair} {tf} {direction}"]
    return "\n".join(lines)


def main() -> int:
    message = sys.stdin.read()
    if not message.strip():
        return 64
    try:
        sys.stdout.write(render(message))
    except ValueError as exc:
        print(f"[telegram_signal_present] {exc}", file=sys.stderr)
        return 65
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
