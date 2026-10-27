#!/usr/bin/env python3
"""Public Telegram presentation for BotA watcher messages.

This module changes presentation only. It receives the already-validated legacy
watcher message and renders modern forex-channel copy for the final Telegram
network request. It must not change pair, timeframe, direction, score, entry,
SL, TP, eligibility, cooldown or delivery identity.
"""
from __future__ import annotations

import os
import re
from datetime import datetime, timezone


HEADER_RE = re.compile(r"\bBotA\s+([A-Z]{6})\s+([A-Z0-9]+)\s+(BUY|SELL)\b")
SCORE_RE = re.compile(r"Score:\s*([0-9]+(?:\.[0-9]+)?)", re.I)
CONF_RE = re.compile(r"Confidence:\s*([0-9]+(?:\.[0-9]+)?)", re.I)
ENTRY_RE = re.compile(r"Entry:\s*([0-9]+(?:\.[0-9]+)?)", re.I)
SL_RE = re.compile(r"(?:SL|Stop Loss):\s*([0-9]+(?:\.[0-9]+)?)", re.I)
TP_RE = re.compile(r"(?:TP|Take Profit):\s*([0-9]+(?:\.[0-9]+)?)", re.I)


def _first(regex: re.Pattern[str], message: str) -> str:
    match = regex.search(message)
    return match.group(1) if match else ""


def _pair_display(pair: str) -> str:
    return f"{pair[:3]}/{pair[3:]}" if len(pair) == 6 else pair


def _score_display(score: str) -> str:
    try:
        value = float(score)
    except (TypeError, ValueError):
        return score or "N/A"
    return str(int(value)) if value.is_integer() else f"{value:.1f}"


def _rr(entry: str, sl: str, tp: str) -> str:
    try:
        e = float(entry)
        s = float(sl)
        t = float(tp)
        risk = abs(e - s)
        reward = abs(t - e)
        if risk <= 0 or reward <= 0:
            return "N/A"
        value = reward / risk
        rendered = f"{value:.2f}".rstrip("0").rstrip(".")
        return f"1:{rendered}"
    except (TypeError, ValueError, OverflowError):
        return "N/A"


def _event_time() -> datetime:
    raw = str(os.environ.get("BOTA_SERVER_EPOCH", "")).strip()
    if raw.isdigit() and int(raw) > 1_000_000_000:
        return datetime.fromtimestamp(int(raw), timezone.utc)
    return datetime.now(timezone.utc)


def format_public_signal(message: str) -> str:
    """Render a modern channel message from canonical BotA watcher text."""
    identity = HEADER_RE.search(message)
    if identity is None:
        raise ValueError("signal_identity_unparseable")

    pair, timeframe, direction = identity.groups()
    score = _first(SCORE_RE, message)
    confidence = _first(CONF_RE, message)
    entry = _first(ENTRY_RE, message)
    sl = _first(SL_RE, message)
    tp = _first(TP_RE, message)
    pair_display = _pair_display(pair)
    now = _event_time()
    timestamp = now.strftime("%H:%M UTC · %d %b %Y")

    is_actionable = bool(entry and sl and tp)
    direction_icon = "🟢" if direction == "BUY" else "🔴"

    if is_actionable:
        lines = [
            f"{direction_icon} BOTA · {direction} SIGNAL",
            "",
            f"{pair_display} · {timeframe}",
            "",
            f"🎯 Entry: {entry}",
            f"🛑 Stop Loss: {sl}",
            f"💰 Take Profit: {tp}",
            f"⚖️ R:R: {_rr(entry, sl, tp)}",
            "",
            f"📊 Signal Score: {_score_display(score)}/100 {direction_icon}",
        ]
        if confidence:
            lines.append(f"Confidence: {_score_display(confidence)}/100")
        lines.extend(
            [
                "",
                f"🕒 {timestamp}",
                f"BOTA • {pair} • {timeframe}",
            ]
        )
        return "\n".join(lines)

    return "\n".join(
        [
            "🟡 BOTA · WATCHLIST",
            "",
            f"{pair_display} · {timeframe} · {direction}",
            "",
            f"📊 Signal Score: {_score_display(score)}/100",
            "👀 Confirmation pending — no trade levels published",
            "",
            f"🕒 {timestamp}",
            f"BOTA • {pair} • {timeframe}",
        ]
    )


__all__ = ["format_public_signal"]
