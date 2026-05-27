#!/usr/bin/env python3
"""
tools/product_message_v1.py
BotA Product Message Layer — V1

Reads existing cache files only.
Does NOT publish to Supabase.
Does NOT change signal logic, scoring, or thresholds.

Usage:
    python3 tools/product_message_v1.py --type market_pulse --shadow
    python3 tools/product_message_v1.py --type market_pulse --shadow --pair EURUSD
    python3 tools/product_message_v1.py --type market_pulse --shadow --no-fusion
    python3 tools/product_message_v1.py --type market_pulse --send --chat-id "<CHAT_ID>"

Outputs:
    stdout                          — formatted Telegram-safe message preview
    logs/product_messages_v1.jsonl  — one JSONL record per run
"""

import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# ── CONFIG ────────────────────────────────────────────────────────────────────

ACTIVE_PAIRS = ["EURUSD", "GBPUSD"]

CACHE_DIR  = Path("cache")
LOGS_DIR   = Path("logs")
SHADOW_LOG = LOGS_DIR / "product_messages_v1.jsonl"

MAX_AGE_M15_MIN = 30
MAX_AGE_H1_MIN  = 75
MAX_AGE_H4_MIN  = 270

ADX_WEAK_THRESHOLD   = 20.0
ADX_STRONG_THRESHOLD = 30.0

RSI_OVERSOLD   = 40.0
RSI_OVERBOUGHT = 60.0

# ── PRODUCT CONTRACT — DO NOT VIOLATE ─────────────────────────────────────────
PRODUCT_CONTRACT = {
    "type":                               "market_pulse",
    "may_include_entry":                  False,
    "may_include_sl_tp":                  False,
    "may_publish_to_supabase_as_active":  False,
}

# ── SAFE NUMERIC HELPER ───────────────────────────────────────────────────────

def safe_float(value, fallback: float = 0.0) -> float:
    if value is None:
        return fallback
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback

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


BASH_BIN      = "/data/data/com.termux/files/usr/bin/bash"
ROOT_DIR      = Path(__file__).resolve().parents[1]
FUSION_SCRIPT = ROOT_DIR / "tools" / "m15_h1_fusion.sh"


def run_fusion(pair: str) -> dict:
    """
    Run tools/m15_h1_fusion.sh to get current filter state.
    Read-only: fusion only reads cache, does not write signals.
    """
    try:
        result = subprocess.run(
            [BASH_BIN, str(FUSION_SCRIPT), pair],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        stdout = result.stdout.strip()
        if not stdout:
            return {}
        return json.loads(stdout)
    except Exception:
        return {}

# ── INTERPRETATION HELPERS ────────────────────────────────────────────────────

def describe_adx(value) -> str:
    adx = safe_float(value)
    if adx < ADX_WEAK_THRESHOLD:
        return f"weak ({adx:.1f})"
    if adx < ADX_STRONG_THRESHOLD:
        return f"moderate ({adx:.1f})"
    return f"strong ({adx:.1f})"


def describe_rsi(value) -> str:
    rsi = safe_float(value, fallback=50.0)
    if rsi < RSI_OVERSOLD:
        return f"oversold zone ({rsi:.1f})"
    if rsi > RSI_OVERBOUGHT:
        return f"overbought zone ({rsi:.1f})"
    return f"neutral ({rsi:.1f})"


def describe_ema_slope(ema9_raw, ema21_raw) -> str:
    ema9  = safe_float(ema9_raw)
    ema21 = safe_float(ema21_raw)
    if ema9 == 0.0 and ema21 == 0.0:
        return "EMA slope: unavailable"
    if ema9 > ema21:
        return "EMA slope: bullish"
    if ema9 < ema21:
        return "EMA slope: bearish"
    return "EMA slope: flat"


def age_label(value, max_age: float) -> str:
    age = safe_float(value)
    if age == 0.0:
        return "age: unknown"
    if age > max_age:
        return f"⚠️ stale ({age:.0f}min old)"
    return f"✅ fresh ({age:.0f}min old)"


def derive_fusion_blockers(fusion: dict) -> list:
    blockers = []
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

    # macro6=3 is neutral/default — only flag actual opposing macro conditions
    if any("macro" in r for r in filter_reasons):
        macro6 = safe_float(fusion.get("macro6"), fallback=3.0)
        if macro6 != 3.0:
            blockers.append("macro filter active")

    return blockers


def derive_data_blockers(m15: dict, h1: dict, d1_trend: dict) -> list:
    blockers = []

    if not m15.get("tf_ok", True) or m15.get("weak"):
        blockers.append(f"M15 data issue: {m15.get('error', 'unknown')}")

    if not h1.get("tf_ok", True) or h1.get("weak"):
        blockers.append(f"H1 data issue: {h1.get('error', 'unknown')}")

    if d1_trend.get("weak") or d1_trend.get("error"):
        blockers.append("D1 trend data weak or unavailable")

    return blockers


def derive_cache_only_adx_blockers(m15: dict, h1: dict) -> list:
    blockers = []

    adx_m15 = safe_float(m15.get("adx"))
    if 0 < adx_m15 < ADX_WEAK_THRESHOLD:
        blockers.append(f"M15 ADX low ({adx_m15:.1f})")

    adx_h1 = safe_float(h1.get("adx"))
    if 0 < adx_h1 < ADX_WEAK_THRESHOLD:
        blockers.append(f"H1 ADX low ({adx_h1:.1f}) — H1 veto risk")

    return blockers


def dedupe_preserve_order(items: list) -> list:
    seen: set = set()
    result = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def derive_blockers(
    m15: dict, h1: dict, d1_trend: dict, fusion: dict
) -> list:
    """
    Derive human-readable blocker reasons from real cached data only.
    Never invent reasons. Only report what the data actually shows.
    """
    blockers = []

    if fusion:
        blockers.extend(derive_fusion_blockers(fusion))

    blockers.extend(derive_data_blockers(m15, h1, d1_trend))

    if not fusion:
        blockers.extend(derive_cache_only_adx_blockers(m15, h1))

    return dedupe_preserve_order(blockers)

# ── PAIR SUMMARY BUILDER ──────────────────────────────────────────────────────

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
    Format Market Pulse message.
    PRODUCT CONTRACT ENFORCED: no entry, no SL, no TP anywhere in output.
    """
    lines = [
        "📊 BotA Market Pulse",
        f"🕐 {generated_at}",
        "─" * 34,
        "ℹ️  Monitoring snapshot — not a trade alert.",
        "🚨 Only 🔴 TRADE ALERT messages are executable.",
        "",
    ]

    for s in summaries:
        pair     = s["pair"]
        price    = s["price"]
        m15      = s["m15"]
        h1       = s["h1"]
        h4       = s["h4"]
        d1_trend = s["d1_trend"]
        blockers = s["blockers"]

        lines.append(f"▪️ {pair}")

        decimals = 3 if "JPY" in pair else 5
        if price:
            lines.append(f"  Price: {price:.{decimals}f}")

        trend      = d1_trend.get("trend", "UNKNOWN")
        trend_weak = d1_trend.get("weak", False)
        trend_err  = bool(d1_trend.get("error"))
        if trend_err or trend_weak:
            lines.append("  D1 bias: unavailable")
        else:
            emoji = "📈" if trend == "BUY" else ("📉" if trend == "SELL" else "➡️")
            lines.append(f"  D1 bias: {emoji} {trend}")

        if m15.get("tf_ok") and not m15.get("weak"):
            lines.append(
                f"  M15: {describe_adx(m15.get('adx'))} trend · "
                f"RSI {describe_rsi(m15.get('rsi'))} · "
                f"{describe_ema_slope(m15.get('ema9'), m15.get('ema21'))} · "
                f"{age_label(m15.get('age_min'), MAX_AGE_M15_MIN)}"
            )
        else:
            lines.append("  M15: data unavailable")

        if h1.get("tf_ok") and not h1.get("weak"):
            lines.append(
                f"  H1:  {describe_adx(h1.get('adx'))} trend · "
                f"RSI {describe_rsi(h1.get('rsi'))} · "
                f"{age_label(h1.get('age_min'), MAX_AGE_H1_MIN)}"
            )
        else:
            lines.append("  H1:  data unavailable")

        if h4.get("tf_ok") and not h4.get("weak"):
            lines.append(
                f"  H4:  {describe_adx(h4.get('adx'))} trend · "
                f"RSI {describe_rsi(h4.get('rsi'))} · "
                f"{age_label(h4.get('age_min'), MAX_AGE_H4_MIN)}"
            )
        else:
            lines.append("  H4:  data unavailable")

        if blockers:
            lines.append(f"  ⛔ No setup: {' | '.join(blockers)}")
        else:
            lines.append("  👁️  Watching — no confirmed setup detected")

        lines.append("")

    lines.append("─" * 34)
    lines.append("BotA active signal scan: EURUSD · GBPUSD")
    lines.append("Silence = safety. Quality gates are strict by design.")

    return "\n".join(lines)

# ── TELEGRAM SENDER ───────────────────────────────────────────────────────────

def send_telegram_message(token: str, chat_id: str, text: str) -> bool:
    """Send message via Telegram Bot API using stdlib urllib only."""
    url     = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = json.dumps({"chat_id": chat_id, "text": text}).encode("utf-8")
    req     = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            return bool(body.get("ok", False))
    except urllib.error.HTTPError as e:
        try:
            body = json.loads(e.read().decode("utf-8"))
            print(f"ERROR: Telegram API error: {body}", file=sys.stderr)
        except Exception:
            print(f"ERROR: Telegram HTTP {e.code}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"ERROR: Telegram send failed: {e}", file=sys.stderr)
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
        "pairs": [
            {
                "pair":                   s["pair"],
                "price":                  s["price"],
                "d1_trend":               s["d1_trend"].get("trend", "UNKNOWN"),
                "blockers":               s["blockers"],
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
        description="BotA Product Message Layer V1"
    )
    parser.add_argument(
        "--type",
        choices=["market_pulse"],
        required=True,
    )

    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument(
        "--shadow",
        action="store_true",
        help="Preview only — does not send Telegram.",
    )
    mode_group.add_argument(
        "--send",
        action="store_true",
        help="Send to Telegram. Requires --chat-id.",
    )

    parser.add_argument(
        "--chat-id",
        default=None,
        help="Telegram chat ID to send to. Required when --send is used.",
    )
    parser.add_argument(
        "--pair",
        choices=ACTIVE_PAIRS,
        default=None,
    )
    parser.add_argument(
        "--no-fusion",
        action="store_true",
        help="Skip m15_h1_fusion.sh — cache-only blocker derivation",
    )
    args = parser.parse_args()

    if args.send and not args.chat_id:
        print("ERROR: --send requires --chat-id.", file=sys.stderr)
        sys.exit(1)

    pairs        = [args.pair] if args.pair else ACTIVE_PAIRS
    use_fusion   = not args.no_fusion
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    mode         = "send" if args.send else "shadow"

    if args.type == "market_pulse":
        summaries = [build_pair_summary(p, use_fusion=use_fusion) for p in pairs]
        message   = format_market_pulse(summaries, generated_at)

        if args.shadow:
            print("\n" + "=" * 42)
            print("SHADOW OUTPUT — NOT SENT TO TELEGRAM")
            print("=" * 42)
            print(message)
            print("=" * 42)

            log_record = write_shadow_log(
                "market_pulse", summaries, message, generated_at,
                mode="shadow", telegram_sent=False,
            )

            print(f"\n[shadow] logged  → {SHADOW_LOG}")
            print(f"[shadow] pairs   → {[s['pair'] for s in summaries]}")
            print(f"[shadow] mode               : shadow")
            print(f"[shadow] telegram_sent      : {log_record['telegram_sent']}")
            print(f"[shadow] supabase_published : {log_record['supabase_published']}")

        elif args.send:
            import os
            token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
            if not token:
                print("ERROR: TELEGRAM_BOT_TOKEN is not set or empty.", file=sys.stderr)
                sys.exit(1)

            print("\n" + "=" * 42)
            print(f"SEND MODE — chat_id: {args.chat_id}")
            print("=" * 42)
            print(message)
            print("=" * 42)
            print("\n[send] Sending to Telegram...")

            ok = send_telegram_message(token, args.chat_id, message)

            if not ok:
                print("ERROR: Telegram send failed — see stderr for details.", file=sys.stderr)
                log_record = write_shadow_log(
                    "market_pulse", summaries, message, generated_at,
                    mode="send", telegram_sent=False,
                )
                print(f"[send] telegram_sent      : False")
                print(f"[send] supabase_published : {log_record['supabase_published']}")
                sys.exit(1)

            log_record = write_shadow_log(
                "market_pulse", summaries, message, generated_at,
                mode="send", telegram_sent=True,
            )

            print(f"[send] logged  → {SHADOW_LOG}")
            print(f"[send] pairs   → {[s['pair'] for s in summaries]}")
            print(f"[send] mode               : send")
            print(f"[send] telegram_sent      : {log_record['telegram_sent']}")
            print(f"[send] supabase_published : {log_record['supabase_published']}")


if __name__ == "__main__":
    main()
