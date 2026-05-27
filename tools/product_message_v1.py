#!/usr/bin/env python3
"""
tools/product_message_v1.py
BotA Product Message Layer — V1

Modes:
    shadow  — print to stdout + log, no Telegram send
    send    — send to Telegram (requires explicit --chat-id) + log

Usage:
    python3 tools/product_message_v1.py --type market_pulse --shadow
    python3 tools/product_message_v1.py --type market_pulse --send --chat-id "CHAT_ID"

Outputs:
    stdout                          — formatted message preview
    logs/product_messages_v1.jsonl  — one JSONL record per run

Product contract:
    - No entry price, SL, or TP in any message type
    - No Supabase publish
    - TELEGRAM_CHAT_ID env var never used automatically
    - --send requires explicit --chat-id
    - Cron/schedule gates live in tools/run_daily_pulse.sh, not here
    - Path-robust: uses ROOT_DIR derived from __file__, not cwd
"""

import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# ── PATH RESOLUTION ───────────────────────────────────────────────────────────
# Robust regardless of working directory when called from cron or wrapper.
ROOT_DIR      = Path(__file__).resolve().parents[1]
CACHE_DIR     = ROOT_DIR / "cache"
LOGS_DIR      = ROOT_DIR / "logs"
SHADOW_LOG    = LOGS_DIR / "product_messages_v1.jsonl"
FUSION_SCRIPT = ROOT_DIR / "tools" / "m15_h1_fusion.sh"

# ── CONFIG ────────────────────────────────────────────────────────────────────

ACTIVE_PAIRS = ["EURUSD", "GBPUSD"]

BASH_BIN = "/data/data/com.termux/files/usr/bin/bash"

MAX_AGE_M15_MIN = 30
MAX_AGE_H1_MIN  = 75
MAX_AGE_H4_MIN  = 270

ADX_WEAK_THRESHOLD   = 20.0
ADX_STRONG_THRESHOLD = 30.0

RSI_OVERSOLD   = 40.0
RSI_OVERBOUGHT = 60.0

# macro6=3 is the neutral baseline — present on valid GREEN signals too.
MACRO6_NEUTRAL = "macro6=3"

# Separator for premium message template
SEP = "━" * 32

# ── PRODUCT CONTRACT — DO NOT VIOLATE ─────────────────────────────────────────
PRODUCT_CONTRACT = {
    "type":                               "market_pulse",
    "may_include_entry":                  False,
    "may_include_sl_tp":                  False,
    "may_publish_to_supabase_as_active":  False,
    "telegram_chat_id_auto_used":         False,
}

# ── SAFE NUMERIC HELPER ───────────────────────────────────────────────────────

def safe_float(value, fallback: float = 0.0) -> float:
    """Convert any cache value to float safely. Returns fallback on failure."""
    if value is None:
        return fallback
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback

# ── DISPLAY HELPERS ───────────────────────────────────────────────────────────

def pair_display(pair: str) -> str:
    """Convert EURUSD → EUR/USD for subscriber-facing output."""
    if len(pair) == 6:
        return f"{pair[:3]}/{pair[3:]}"
    return pair


def redact_chat_id(chat_id: str) -> str:
    """Show only last 4 chars of chat ID in output and logs."""
    if not chat_id or len(chat_id) <= 4:
        return "***"
    return f"***{chat_id[-4:]}"


def derive_status(fusion: dict) -> tuple:
    """
    Return (emoji, description) for subscriber-facing pair status.

    States:
        ⚪ No setup       — HOLD direction, score=0, or no fusion data
        🟡 Watching       — directional bias present, not yet triggered
        🟢 Setup forming  — score 55+, direction confirmed

    Rules:
        - H1 not-confirmed is detected ONLY by "H1_trend_neutral" in
          filter_reasons, not by any string containing "H1".
          "H1_trend_confirmed" means H1 IS confirmed — must not mislabel it.
        - filter_rejected=False means signal passed all gates.
          Do not claim a trade alert was sent — the pulse cannot prove that.
        - 🔴 Trade Alert never appears inside Market Pulse.
    """
    if not fusion:
        return "⚪", "No setup"

    direction       = fusion.get("direction", "HOLD")
    score           = safe_float(fusion.get("score"))
    filter_rejected = fusion.get("filter_rejected", True)
    filter_reasons  = fusion.get("filter_reasons", [])

    if direction == "HOLD":
        return "⚪", "No setup"

    dir_label = "bullish" if direction == "BUY" else "bearish"

    # Precise H1 check — only "H1_trend_neutral" means H1 is not confirmed.
    # "H1_trend_confirmed" is the positive case and must NOT be treated as absent.
    h1_not_confirmed = "H1_trend_neutral" in filter_reasons

    # Signal passed all gate filters — show as forming, no alert claim.
    if not filter_rejected:
        return "🟢", f"Setup forming — {dir_label} structure aligned"

    if score >= 55:
        if h1_not_confirmed:
            return "🟡", f"Watching — {dir_label} structure, awaiting H1 confirmation"
        return "🟢", f"Setup forming — {dir_label} structure aligned"

    if score >= 30:
        return "🟡", f"Watching — {dir_label} bias present"

    return "⚪", "No setup"

# ── CACHE READERS ─────────────────────────────────────────────────────────────

def load_indicator(pair: str, tf: str) -> dict:
    path = CACHE_DIR / f"indicators_{pair}_{tf}.json"
    if not path.exists():
        return {"error": f"missing:{path}", "tf_ok": False, "weak": True}
    try:
        return json.loads(path.read_text(errors="replace"))
    except Exception as e:
        return {"error": f"parse:{type(e).__name__}", "tf_ok": False, "weak": True}


def load_d1_trend(pair: str) -> dict:
    path = CACHE_DIR / f"d1_trend_{pair}.json"
    if not path.exists():
        return {"error": f"missing:{path}", "trend": "UNKNOWN", "weak": True}
    try:
        return json.loads(path.read_text(errors="replace"))
    except Exception as e:
        return {"error": f"parse:{type(e).__name__}", "trend": "UNKNOWN", "weak": True}


def run_fusion(pair: str) -> dict:
    """
    Run tools/m15_h1_fusion.sh to get current filter state.
    Uses absolute FUSION_SCRIPT path — not dependent on cwd.
    Read-only: fusion only reads cache, does not write signals.
    Returns parsed JSON dict, or empty dict on any failure.
    """
    if not FUSION_SCRIPT.exists():
        return {}
    try:
        result = subprocess.run(
            [BASH_BIN, str(FUSION_SCRIPT), pair],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
            cwd=str(ROOT_DIR),
        )
        stdout = result.stdout.strip()
        if not stdout:
            return {}
        return json.loads(stdout)
    except Exception:
        return {}

# ── PAIR SUMMARY BUILDER ──────────────────────────────────────────────────────

def derive_blockers(
    m15: dict, h1: dict, d1_trend: dict, fusion: dict
) -> list:
    """
    Derive blocker reasons from real cached data only.
    Stored in JSONL log — not shown in subscriber-facing message.
    macro6=3 is neutral baseline and is never reported as a blocker.
    """
    blockers = []

    if fusion:
        reasons_str    = str(fusion.get("reasons", ""))
        filter_reasons = fusion.get("filter_reasons", [])

        if "Closed" in reasons_str or "fail_closed" in filter_reasons:
            blockers.append("market closed")
        if "direction_not_tradeable" in filter_reasons:
            blockers.append("no tradeable direction (HOLD)")
        if any("score" in r for r in filter_reasons):
            score = safe_float(fusion.get("score"))
            blockers.append(f"score below threshold ({score:.0f})")
        if any("rr" in r for r in filter_reasons):
            blockers.append("risk/reward not met")

        macro_reasons     = [r for r in filter_reasons if "macro" in r]
        non_neutral_macro = [r for r in macro_reasons if r != MACRO6_NEUTRAL]
        if non_neutral_macro:
            blockers.append(f"macro: {', '.join(non_neutral_macro)}")

    if not m15.get("tf_ok", True) or m15.get("weak"):
        blockers.append(f"M15 data issue: {m15.get('error', 'unknown')}")
    if not h1.get("tf_ok", True) or h1.get("weak"):
        blockers.append(f"H1 data issue: {h1.get('error', 'unknown')}")

    if not fusion:
        adx_m15 = safe_float(m15.get("adx"))
        if 0 < adx_m15 < ADX_WEAK_THRESHOLD:
            blockers.append(f"M15 ADX low ({adx_m15:.1f})")
        adx_h1 = safe_float(h1.get("adx"))
        if 0 < adx_h1 < ADX_WEAK_THRESHOLD:
            blockers.append(f"H1 ADX low ({adx_h1:.1f}) — H1 veto risk")

    if d1_trend.get("weak") or d1_trend.get("error"):
        blockers.append("D1 trend data weak or unavailable")

    seen, deduped = set(), []
    for b in blockers:
        if b not in seen:
            seen.add(b)
            deduped.append(b)
    return deduped


def build_pair_summary(pair: str, use_fusion: bool = True) -> dict:
    m15      = load_indicator(pair, "M15")
    h1       = load_indicator(pair, "H1")
    h4       = load_indicator(pair, "H4")
    d1_trend = load_d1_trend(pair)
    fusion   = run_fusion(pair) if use_fusion else {}

    price    = safe_float(m15.get("price") or h1.get("price"))
    blockers = derive_blockers(m15, h1, d1_trend, fusion)

    return {
        "pair":     pair,
        "price":    price,
        "m15":      m15,
        "h1":       h1,
        "h4":       h4,
        "d1_trend": d1_trend,
        "fusion":   fusion,
        "blockers": blockers,
    }

# ── MESSAGE FORMATTER ─────────────────────────────────────────────────────────

def format_market_pulse(summaries: list, generated_at: str) -> str:
    """
    Premium subscriber-facing Market Pulse.
    PRODUCT CONTRACT ENFORCED: no entry, no SL, no TP anywhere in output.
    Technical metrics stored in JSONL log, not shown to subscribers.
    """
    lines = [
        SEP,
        "📊  BotA · Market Pulse",
        generated_at,
        SEP,
        "",
    ]

    for s in summaries:
        display  = pair_display(s["pair"])
        price    = s["price"]
        d1_trend = s["d1_trend"]
        fusion   = s["fusion"]

        trend       = d1_trend.get("trend", "UNKNOWN")
        trend_weak  = d1_trend.get("weak", False)
        trend_err   = bool(d1_trend.get("error"))
        trend_emoji = (
            "📈" if trend == "BUY"
            else "📉" if trend == "SELL"
            else "➡️"
        )
        if trend_err or trend_weak:
            trend_emoji = "➡️"

        decimals  = 3 if "JPY" in s["pair"] else 5
        price_str = f"{price:.{decimals}f}" if price else "–"

        status_emoji, status_desc = derive_status(fusion)

        lines.append(f"{display}  {trend_emoji}  {price_str}")
        lines.append(f"{status_emoji}  {status_desc}")
        lines.append("")

    scan_pairs = "  ·  ".join(s["pair"] for s in summaries)

    lines += [
        SEP,
        f"Scan: {scan_pairs}",
        "No active trade alert in this pulse.",
        "",
        "No setup = quality standard held.",
        "📊 Pulse = context  ·  🔴 Alert = executable",
        SEP,
    ]

    return "\n".join(lines)

# ── TELEGRAM SENDER ───────────────────────────────────────────────────────────

def send_telegram(text: str, token: str, chat_id: str) -> bool:
    """
    Send message via Telegram Bot API using urllib only — no new dependencies.
    Returns True on confirmed success (HTTP 200 + ok=true).
    TELEGRAM_CHAT_ID env var is never used — chat_id must be passed explicitly.
    """
    url     = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = urllib.parse.urlencode({
        "chat_id":    chat_id,
        "text":       text,
        "parse_mode": "HTML",
    }).encode("utf-8")

    try:
        req = urllib.request.Request(url, data=payload, method="POST")
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            data = json.loads(body)
            if data.get("ok") is True:
                msg_id = data.get("result", {}).get("message_id", "?")
                print(f"[send] ✅ Telegram confirmed: message_id={msg_id}")
                return True
            else:
                print(f"[send] ❌ Telegram ok=false: {body[:200]}", file=sys.stderr)
                return False
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"[send] ❌ HTTP {e.code}: {body[:200]}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"[send] ❌ {type(e).__name__}: {e}", file=sys.stderr)
        return False

# ── SHADOW LOG WRITER ─────────────────────────────────────────────────────────

def write_shadow_log(
    message_type: str,
    summaries: list,
    formatted_text: str,
    generated_at: str,
    mode: str,
    telegram_sent: bool,
) -> dict:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    record = {
        "generated_at":       generated_at,
        "message_type":       message_type,
        "mode":               mode,
        "telegram_sent":      telegram_sent,
        "supabase_published": False,
        "shadow_only":        mode == "shadow",
        "pairs": [
            {
                "pair":                   s["pair"],
                "price":                  s["price"],
                "d1_trend":               s["d1_trend"].get("trend", "UNKNOWN"),
                "blockers":               s["blockers"],
                "status_emoji":           derive_status(s["fusion"])[0],
                "status_desc":            derive_status(s["fusion"])[1],
                "m15_adx":                safe_float(s["m15"].get("adx")),
                "m15_rsi":                safe_float(s["m15"].get("rsi")),
                "h1_adx":                 safe_float(s["h1"].get("adx")),
                "h1_rsi":                 safe_float(s["h1"].get("rsi")),
                "h4_adx":                 safe_float(s["h4"].get("adx")),
                "fusion_score":           safe_float(s["fusion"].get("score")),
                "fusion_direction":       s["fusion"].get("direction"),
                "fusion_filter_rejected": s["fusion"].get("filter_rejected"),
                "fusion_filter_reasons":  s["fusion"].get("filter_reasons"),
                "m15_age_min":            safe_float(s["m15"].get("age_min")),
                "h1_age_min":             safe_float(s["h1"].get("age_min")),
            }
            for s in summaries
        ],
        "formatted_preview": formatted_text[:600],
    }

    with SHADOW_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")

    return record

# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="BotA Product Message Layer V1 — shadow or controlled send"
    )
    parser.add_argument("--type", choices=["market_pulse"], required=True)

    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument(
        "--shadow",
        action="store_true",
        help="Shadow mode: print to stdout and log only. No Telegram send.",
    )
    mode_group.add_argument(
        "--send",
        action="store_true",
        help="Send mode: send to Telegram. Requires --chat-id explicitly.",
    )

    parser.add_argument(
        "--chat-id",
        default=None,
        help="Telegram chat ID. Required for --send. Never auto-read from env.",
    )
    parser.add_argument("--pair", choices=ACTIVE_PAIRS, default=None)
    parser.add_argument(
        "--no-fusion",
        action="store_true",
        help="Skip m15_h1_fusion.sh — cache-only mode",
    )
    args = parser.parse_args()

    # Hard gate: --send requires --chat-id
    if args.send and not args.chat_id:
        print(
            "ERROR: --send requires --chat-id.\n"
            "TELEGRAM_CHAT_ID env var is never used automatically.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Hard gate: --send requires TELEGRAM_BOT_TOKEN
    token = None
    if args.send:
        token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
        if not token:
            print("ERROR: TELEGRAM_BOT_TOKEN not set or empty.", file=sys.stderr)
            sys.exit(1)

    pairs        = [args.pair] if args.pair else ACTIVE_PAIRS
    use_fusion   = not args.no_fusion
    dt_now       = datetime.now(timezone.utc)
    generated_at = dt_now.strftime("%a %d %b · %H:%M UTC")
    mode         = "send" if args.send else "shadow"

    if args.type == "market_pulse":
        summaries = [build_pair_summary(p, use_fusion=use_fusion) for p in pairs]
        message   = format_market_pulse(summaries, generated_at)

        print("\n" + "=" * 42)
        if args.shadow:
            print("SHADOW OUTPUT — NOT SENT TO TELEGRAM")
        else:
            print(f"SEND MODE — TARGET CHAT: {redact_chat_id(args.chat_id)}")
        print("=" * 42)
        print(message)
        print("=" * 42)

        telegram_sent = False

        if args.send:
            print(f"\n[send] Sending to {redact_chat_id(args.chat_id)} ...")
            telegram_sent = send_telegram(message, token, args.chat_id)
            if not telegram_sent:
                print("[send] ⚠️  Send failed.", file=sys.stderr)
                write_shadow_log(
                    "market_pulse", summaries, message,
                    generated_at, mode, telegram_sent,
                )
                sys.exit(1)

        log_record = write_shadow_log(
            "market_pulse", summaries, message,
            generated_at, mode, telegram_sent,
        )

        print(f"\n[{mode}] logged             → {SHADOW_LOG}")
        print(f"[{mode}] pairs              → {[s['pair'] for s in summaries]}")
        print(f"[{mode}] telegram_sent      : {log_record['telegram_sent']}")
        print(f"[{mode}] supabase_published : {log_record['supabase_published']}")
        print(f"[{mode}] mode               : {log_record['mode']}")


if __name__ == "__main__":
    main()
