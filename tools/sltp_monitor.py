#!/usr/bin/env python3
"""
sltp_monitor.py — GEM-101: Real-time SL/TP hit monitor + daily summary.
- Runs every 15min via cron (same cadence as signal watcher)
- Tracks sent alerts in state file to avoid duplicates
- Sends Telegram alert when SL or TP is hit
- Daily summary at 23:50 UTC via --summary flag
"""
import os, sys, json, csv, time
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT      = Path(os.environ.get("BOTA_ROOT", Path.home() / "BotA"))
LOGS      = ROOT / "logs"
CACHE     = ROOT / "cache"
STATE_FILE = LOGS / "sltp_monitor_state.json"
ALERTS_CSV = LOGS / "alerts.csv"

def _env(key, default=""):
    return os.environ.get(key, default).strip()

def get_token():
    return _env("TELEGRAM_BOT_TOKEN")

def get_chat():
    return _env("TELEGRAM_CHAT_ID")

def send_telegram(msg: str) -> bool:
    import urllib.error, urllib.parse, urllib.request
    token = get_token(); chat = get_chat()
    if not token or not chat:
        print("[sltp] TELEGRAM not configured", file=sys.stderr); return False
    url  = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode({"chat_id": chat, "text": msg, "parse_mode": "HTML"}).encode()
    try:
        with urllib.request.urlopen(url, data=data, timeout=15) as r:
            return json.load(r).get("ok", False)
    except (urllib.error.URLError, OSError, ValueError) as e:
        print(f"[sltp] Telegram error: {type(e).__name__}: {e}", file=sys.stderr); return False

def load_state() -> dict:
    """Load the dedupe state.

    A missing file is normal on first run. A corrupt file is reported loudly
    because starting from an empty state can re-alert already reported hits.
    """
    empty = {"hit": {}, "daily_summary_sent": ""}
    try:
        with open(STATE_FILE) as f: state = json.load(f)
    except FileNotFoundError:
        return empty
    except (OSError, ValueError) as e:
        print(
            f"[sltp] state unusable at {STATE_FILE}, duplicate alerts possible: {type(e).__name__}: {e}",
            file=sys.stderr,
        )
        return empty
    if not isinstance(state, dict):
        print(f"[sltp] state malformed at {STATE_FILE}, duplicate alerts possible", file=sys.stderr)
        return empty
    state.setdefault("hit", {})
    state.setdefault("daily_summary_sent", "")
    return state

def save_state(state: dict):
    LOGS.mkdir(parents=True, exist_ok=True)
    tmp = str(STATE_FILE) + ".tmp"
    with open(tmp, "w") as f: json.dump(state, f, indent=2)
    os.replace(tmp, str(STATE_FILE))

def get_current_price(pair: str, tf: str = "M15") -> float:
    path = CACHE / f"{pair}_{tf}.json"
    if not path.exists(): return 0.0
    try:
        with open(path) as f: raw = json.load(f)
        rows = raw.get("rows", [])
        if rows: return float(rows[-1].get("close", 0))
    except (OSError, ValueError, TypeError, AttributeError) as e:
        print(f"[sltp] price cache unusable at {path}: {type(e).__name__}: {e}", file=sys.stderr)
    return 0.0

def get_cache_age_secs(pair: str, tf: str = "M15") -> int:
    path = CACHE / f"{pair}_{tf}.json"
    if not path.exists(): return 9999
    try: return int(time.time() - path.stat().st_mtime)
    except OSError as e:
        print(f"[sltp] cannot stat {path}, treating cache as stale: {e}", file=sys.stderr)
        return 9999

def load_sent_signals() -> list:
    if not ALERTS_CSV.exists(): return []
    results = []
    try:
        with open(ALERTS_CSV, newline="", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            for row in reader:
                row = {k.strip().lower(): v.strip() if v else ""
                       for k, v in row.items() if k}
                if row.get("rejected", "true").lower() == "true": continue
                direction = row.get("direction", "").upper()
                if direction not in ("BUY", "SELL"): continue
                try:
                    entry = float(row.get("entry", 0) or 0)
                    sl    = float(row.get("sl", 0) or 0)
                    tp    = float(row.get("tp", 0) or 0)
                    score = float(row.get("score", 0) or 0)
                except (TypeError, ValueError) as e:
                    print(f"[sltp] skipping row with unparseable levels: {e}", file=sys.stderr)
                    continue
                if not entry or not sl or not tp: continue
                results.append({
                    "timestamp": row.get("timestamp", ""),
                    "pair":      row.get("pair", ""),
                    "tf":        row.get("tf", "M15"),
                    "direction": direction,
                    "score":     score,
                    "entry":     entry,
                    "sl":        sl,
                    "tp":        tp,
                })
    except (OSError, csv.Error, UnicodeError) as e:
        print(f"[sltp] CSV read error on {ALERTS_CSV}: {type(e).__name__}: {e}", file=sys.stderr)
    return results

def check_hit(direction, current, entry, sl, tp) -> str:
    if direction == "BUY":
        if current >= tp: return "TP"
        if current <= sl: return "SL"
    elif direction == "SELL":
        if current <= tp: return "TP"
        if current >= sl: return "SL"
    return ""

def pip_size(pair: str) -> float:
    return 0.01 if pair.upper().endswith("JPY") else 0.0001

def pips(a: float, b: float, pair: str) -> float:
    return round(abs(a - b) / pip_size(pair), 1)

def sig_key(sig: dict) -> str:
    return f"{sig['timestamp']}|{sig['pair']}|{sig['direction']}"

def run_monitor() -> int:
    """Alert on resolved signals. Returns the number of failed deliveries."""
    state   = load_state()
    signals = load_sent_signals()
    now_utc = datetime.now(timezone.utc)
    cutoff  = now_utc - timedelta(hours=24)
    alerts_sent = 0
    send_failures = 0

    for sig in signals:
        key = sig_key(sig)
        if key in state["hit"]: continue

        try:
            ts_str = sig["timestamp"].replace("Z", "+00:00")
            ts = datetime.fromisoformat(ts_str)
            if ts.tzinfo is None: ts = ts.replace(tzinfo=timezone.utc)
        except (AttributeError, TypeError, ValueError) as e:
            print(f"[sltp] skipping signal with bad timestamp {sig.get('timestamp')!r}: {e}", file=sys.stderr)
            continue

        if ts < cutoff: continue

        age = get_cache_age_secs(sig["pair"], sig["tf"])
        if age > 2700: continue

        current = get_current_price(sig["pair"], sig["tf"])
        if not current: continue

        hit = check_hit(sig["direction"], current, sig["entry"], sig["sl"], sig["tp"])
        if not hit: continue

        pair = sig["pair"]; direction = sig["direction"]
        score = sig["score"]; entry = sig["entry"]
        sl = sig["sl"]; tp = sig["tp"]

        if hit == "TP":
            result_pips = pips(tp, entry, pair)
            emoji = "🎯✅"; result_str = f"+{result_pips} pips WIN"
            r_mult = round(result_pips / pips(entry, sl, pair), 2) if pips(entry, sl, pair) else 0
            r_str = f"+{r_mult}R"
        else:
            result_pips = pips(entry, sl, pair)
            emoji = "🛑❌"; result_str = f"-{result_pips} pips LOSS"
            r_str = "-1R"

        msg = (
            f"{emoji} <b>BotA {pair} {direction} — {hit} HIT</b>\n"
            f"📊 Score: {score:.0f} | {result_str} ({r_str})\n"
            f"💰 Entry: {entry:.5f}\n"
            f"🎯 TP: {tp:.5f}  🛑 SL: {sl:.5f}\n"
            f"📍 Current: {current:.5f}\n"
            f"🕐 Signal: {sig['timestamp'][:16]}"
        )

        if send_telegram(msg):
            state["hit"][key] = {
                "hit": hit, "current": current,
                "result_pips": result_pips if hit == "TP" else -result_pips,
                "r": r_str, "reported_at": now_utc.isoformat()
            }
            save_state(state)
            alerts_sent += 1
            print(f"[sltp] ALERT: {pair} {direction} {hit} @ {current:.5f}")
        else:
            send_failures += 1
            print(f"[sltp] delivery failed, will retry: {pair} {direction} {hit}", file=sys.stderr)

    print(f"[sltp] Done. {len(signals)} signals checked, {alerts_sent} alerts sent, "
          f"{send_failures} deliveries failed.")
    return send_failures

def run_daily_summary() -> int:
    """Send the daily summary. Returns the number of failed deliveries."""
    state = load_state()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if state.get("daily_summary_sent") == today:
        print("[sltp] Summary already sent."); return 0

    hits = state.get("hit", {})
    today_hits = {k: v for k, v in hits.items()
                  if v.get("reported_at", "")[:10] == today}

    if not today_hits:
        if not send_telegram(f"📊 <b>BotA Daily SL/TP Summary — {today}</b>\nNo signals resolved today."):
            print("[sltp] empty summary not delivered, not marking as sent", file=sys.stderr)
            return 1
        state["daily_summary_sent"] = today
        save_state(state); return 0

    wins   = [v for v in today_hits.values() if v.get("hit") == "TP"]
    losses = [v for v in today_hits.values() if v.get("hit") == "SL"]
    total  = len(today_hits)
    wr     = round(len(wins) / total * 100, 1) if total else 0
    total_pips = sum(v.get("result_pips", 0) for v in today_hits.values())
    pips_str = f"+{total_pips:.1f}" if total_pips >= 0 else f"{total_pips:.1f}"
    win_emoji = "🟢" if len(wins) > len(losses) else "🔴" if len(losses) > len(wins) else "🟡"

    msg = (
        f"📊 <b>BotA Daily SL/TP Summary — {today}</b>\n\n"
        f"{win_emoji} Results: {len(wins)}W / {len(losses)}L of {total} resolved\n"
        f"📈 Win Rate: {wr}%\n"
        f"💰 Total Pips: {pips_str}\n\n"
    )
    for k, v in sorted(today_hits.items(), key=lambda x: x[1].get("reported_at","")):
        parts = k.split("|")
        pair = parts[1] if len(parts) > 1 else "?"
        direction = parts[2] if len(parts) > 2 else "?"
        hit = v.get("hit","?"); pips_val = v.get("result_pips",0); r = v.get("r","?")
        e = "✅" if hit == "TP" else "❌"
        msg += f"{e} {pair} {direction} → {hit} {r} ({pips_val:+.1f} pips)\n"

    if not send_telegram(msg):
        print("[sltp] summary not delivered, not marking as sent", file=sys.stderr)
        return 1
    state["daily_summary_sent"] = today
    save_state(state)
    print(f"[sltp] Summary sent: {len(wins)}W/{len(losses)}L")
    return 0

if __name__ == "__main__":
    env_path = ROOT / ".env.runtime"
    if env_path.exists():
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("export "): line = line[7:]
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip('"'))

    failures = run_daily_summary() if "--summary" in sys.argv else run_monitor()
    sys.exit(1 if failures else 0)
