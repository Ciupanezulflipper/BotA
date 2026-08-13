#!/data/data/com.termux/files/usr/bin/python3
# BotA — Telegram Controller (menu + signals) — v2 with webhook auto-clear
# Fixes: HTTP Error 409 (can't use getUpdates while webhook is active)
# Env: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, optional ANALYZE_PAIRS

import os, re, sys, json, time, html, subprocess, textwrap
import urllib.request, urllib.parse, urllib.error

PAIR_RE = re.compile(r"^[A-Z]{6,7}$")

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID", "").strip()
API_BASE  = f"https://api.telegram.org/bot{BOT_TOKEN}"

STATE_DIR = os.path.join(os.environ.get("HOME","/data/data/com.termux/files/home"), "BotA", "state")
os.makedirs(STATE_DIR, exist_ok=True)
OFFSET_FILE = os.path.join(STATE_DIR, "tele_update_offset.txt")
PAUSE_FILE  = os.path.join(STATE_DIR, "paused.flag")
PAIRS_FILE  = os.path.join(STATE_DIR, "analyze_pairs.txt")  # if present, overrides ANALYZE_PAIRS env
DEFAULT_PAIRS = os.getenv("ANALYZE_PAIRS", "EURUSD,GBPUSD")

BOTA_TOOLS     = os.path.join(os.environ.get("HOME", ""), "BotA", "tools")
ANALYZE_NOW_SH = os.path.join(BOTA_TOOLS, "analyze_now.sh")
METRICS_VERIFY = os.path.join(BOTA_TOOLS, "metrics_verify.sh")
PHASE10_VERIFY = os.path.join(BOTA_TOOLS, "phase10_verify.sh")
DAILY_REPORT   = os.path.join(BOTA_TOOLS, "daily_report.py")

def _http_json(url, data=None, timeout=30):
    req = urllib.request.Request(url, headers={"Content-Type":"application/json"})
    payload = json.dumps(data).encode("utf-8") if data is not None else None
    with urllib.request.urlopen(req, data=payload, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))

def _http_get(url, timeout=30):
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))

def ensure_long_poll_ready():
    """If a webhook is configured, delete it (drop pending updates) to avoid 409."""
    try:
        info = _http_get(f"{API_BASE}/getWebhookInfo")
        if info.get("ok") and info.get("result", {}).get("url"):
            # A webhook is set: remove it for long polling
            _http_json(f"{API_BASE}/deleteWebhook", {"drop_pending_updates": True})
            # tiny wait to let Telegram clear state
            time.sleep(0.8)
    except Exception as e:
        sys.stderr.write(f"[tele_control] ensure_long_poll_ready warn: {e}\n")

def send_message(chat_id, text, reply_markup=None):
    data = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    if reply_markup:
        data["reply_markup"] = reply_markup
    return _http_json(f"{API_BASE}/sendMessage", data)

def answer_callback_query(cb_id, text=""):
    return _http_json(f"{API_BASE}/answerCallbackQuery",
                      {"callback_query_id": cb_id, "text": text[:200]})

def get_updates(offset=None, timeout=25):
    params = {"timeout": timeout}
    if offset is not None:
        params["offset"] = offset
    url = f"{API_BASE}/getUpdates?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(url, timeout=timeout+5) as resp:
        return json.loads(resp.read().decode("utf-8"))

def valid_pairs(candidates):
    """Keep only well-formed symbols so no caller text reaches a command line."""
    cleaned = [c.strip().upper() for c in candidates if c and c.strip()]
    return [c for c in cleaned if PAIR_RE.match(c)]

def analyze_argv(pairs):
    return [ANALYZE_NOW_SH], dict(os.environ, ANALYZE_PAIRS=",".join(pairs))

def run_cmd(argv, env=None, max_len=3500, max_lines=None):
    try:
        proc = subprocess.run(argv, shell=False, check=False,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              env=env, timeout=120)
        out = proc.stdout.decode("utf-8", "ignore")
        if max_lines:
            out = "\n".join(out.splitlines()[:max_lines])
        return out if len(out) <= max_len else out[:max_len] + "\n…(truncated)…"
    except Exception as e:
        return f"[tele_control] Exception running command: {e}"

def read_offset():
    try:
        with open(OFFSET_FILE, "r") as f:
            return int(f.read().strip())
    except:
        return None

def write_offset(v):
    try:
        with open(OFFSET_FILE, "w") as f:
            f.write(str(v))
    except:
        pass

def paused(): return os.path.exists(PAUSE_FILE)
def set_paused(flag): open(PAUSE_FILE, "a").close() if flag else (os.remove(PAUSE_FILE) if os.path.exists(PAUSE_FILE) else None)

def get_pairs_from_state():
    if os.path.exists(PAIRS_FILE):
        try:
            txt = open(PAIRS_FILE).read().strip().replace(",", " ")
            pairs = " ".join(p for p in txt.split() if p)
            return pairs if pairs else DEFAULT_PAIRS.replace(",", " ")
        except:
            return DEFAULT_PAIRS.replace(",", " ")
    return DEFAULT_PAIRS.replace(",", " ")

def set_pairs_to_state(pairs_list):
    with open(PAIRS_FILE, "w") as f:
        f.write(",".join(pairs_list))

def menu_keyboard():
    return {
        "inline_keyboard": [
            [
                {"text":"▶️ Analyze Now", "callback_data":"ANALYZE_NOW"},
                {"text":"📊 Status",       "callback_data":"STATUS"},
            ],
            [
                {"text":"🧪 Audit",        "callback_data":"AUDIT"},
                {"text":"🩺 Health",       "callback_data":"HEALTH"},
            ],
            [
                {"text":("⏸ Pause Alerts" if not paused() else "▶️ Resume Alerts"),
                 "callback_data":("PAUSE" if not paused() else "RESUME")},
                {"text":"📅 Daily Report", "callback_data":"DAILY"},
            ],
            [
                {"text":"⚙️ Set Pairs: EURUSD,GBPUSD", "callback_data":"SETPAIRS_EURUSD_GBPUSD"},
            ],
        ]
    }

def render_menu_text():
    pairs = get_pairs_from_state().replace(" ", ",")
    status = "PAUSED" if paused() else "RUNNING"
    return textwrap.dedent(f"""\
        <b>BotA — Control Panel</b>
        mode: <b>{status}</b>
        pairs: <code>{html.escape(pairs)}</code>

        Use the buttons below:
        ▶ Analyze Now — pretty signal text for the configured pairs
        📊 Status — quick metrics + freshness
        🧪 Audit — metrics_verify snapshot
        🩺 Health — phase10 DRY health ping
        ⏸/▶ Alerts — toggle alert loop
        📅 Daily Report — push the 24h report
    """)

def handle_command(text, chat_id, entities=None):
    parts = text.strip().split()
    cmd = parts[0].lower()
    args = parts[1:]
    if cmd in ("/start", "/menu"):
        send_message(chat_id, render_menu_text(), {"inline_keyboard": menu_keyboard()["inline_keyboard"]}); return
    if cmd == "/pause":
        set_paused(True); send_message(chat_id, "🔕 Alerts <b>PAUSED</b>.", {"inline_keyboard": menu_keyboard()["inline_keyboard"]}); return
    if cmd in ("/resume","/start_alerts"):
        set_paused(False); send_message(chat_id, "🔔 Alerts <b>RESUMED</b>.", {"inline_keyboard": menu_keyboard()["inline_keyboard"]}); return
    if cmd == "/pairs":
        if args:
            pairs = valid_pairs(args)
            if not pairs:
                send_message(chat_id, "❌ Invalid pairs. Usage: <code>/pairs EURUSD GBPUSD</code>"); return
            set_pairs_to_state(pairs); send_message(chat_id, f"✅ Pairs set to: <code>{' '.join(pairs)}</code>", {"inline_keyboard": menu_keyboard()["inline_keyboard"]})
        else:
            cur = get_pairs_from_state()
            send_message(chat_id, f"ℹ️ Current pairs: <code>{cur}</code>\nUsage: <code>/pairs EURUSD GBPUSD XAUUSD</code>")
        return
    if cmd == "/analyze":
        pairs = valid_pairs(args) if args else valid_pairs(get_pairs_from_state().split())
        if not pairs:
            send_message(chat_id, "❌ Invalid pairs. Usage: <code>/analyze EURUSD GBPUSD</code>"); return
        argv, env = analyze_argv(pairs)
        out = run_cmd(argv, env=env)
        send_message(chat_id, out); return
    if cmd == "/status":
        out = run_cmd([METRICS_VERIFY], max_lines=120)
        send_message(chat_id, f"<b>Status</b>\n<code>{html.escape(out)}</code>"); return
    if cmd == "/audit":
        out = run_cmd([METRICS_VERIFY])
        send_message(chat_id, f"<b>Audit</b>\n<code>{html.escape(out)}</code>"); return
    if cmd == "/health":
        out = run_cmd([PHASE10_VERIFY], max_lines=80)
        send_message(chat_id, f"<b>Health</b>\n<code>{html.escape(out)}</code>"); return
    if cmd == "/daily":
        out = run_cmd(["python3", DAILY_REPORT], env=dict(os.environ, DRY="0"), max_lines=80)
        send_message(chat_id, out); return
    send_message(chat_id, render_menu_text(), {"inline_keyboard": menu_keyboard()["inline_keyboard"]})

def handle_callback(cb, chat_id):
    data = cb.get("data",""); cb_id = cb.get("id")
    if cb_id: 
        try: answer_callback_query(cb_id, "Working…")
        except: pass
    if data == "ANALYZE_NOW":
        pairs = valid_pairs(get_pairs_from_state().split())
        if not pairs:
            send_message(chat_id, "❌ No valid pairs configured.", {"inline_keyboard": menu_keyboard()["inline_keyboard"]}); return
        argv, env = analyze_argv(pairs)
        out = run_cmd(argv, env=env)
        send_message(chat_id, out, {"inline_keyboard": menu_keyboard()["inline_keyboard"]}); return
    if data == "STATUS":
        out = run_cmd([METRICS_VERIFY], max_lines=120)
        send_message(chat_id, f"<b>Status</b>\n<code>{html.escape(out)}</code>", {"inline_keyboard": menu_keyboard()["inline_keyboard"]}); return
    if data == "AUDIT":
        out = run_cmd([METRICS_VERIFY])
        send_message(chat_id, f"<b>Audit</b>\n<code>{html.escape(out)}</code>", {"inline_keyboard": menu_keyboard()["inline_keyboard"]}); return
    if data == "HEALTH":
        out = run_cmd([PHASE10_VERIFY], max_lines=80)
        send_message(chat_id, f"<b>Health</b>\n<code>{html.escape(out)}</code>", {"inline_keyboard": menu_keyboard()["inline_keyboard"]}); return
    if data == "PAUSE":
        set_paused(True);  send_message(chat_id, "🔕 Alerts <b>PAUSED</b>.", {"inline_keyboard": menu_keyboard()["inline_keyboard"]}); return
    if data == "RESUME":
        set_paused(False); send_message(chat_id, "🔔 Alerts <b>RESUMED</b>.", {"inline_keyboard": menu_keyboard()["inline_keyboard"]}); return
    if data == "DAILY":
        out = run_cmd(["python3", DAILY_REPORT], env=dict(os.environ, DRY="0"), max_lines=80)
        send_message(chat_id, out, {"inline_keyboard": menu_keyboard()["inline_keyboard"]}); return
    if data.startswith("SETPAIRS_"):
        pairs = valid_pairs(data.replace("SETPAIRS_", "").split("_"))
        if not pairs:
            send_message(chat_id, "❌ Invalid pairs.", {"inline_keyboard": menu_keyboard()["inline_keyboard"]}); return
        set_pairs_to_state(pairs)
        send_message(chat_id, f"✅ Pairs set to: <code>{' '.join(pairs)}</code>", {"inline_keyboard": menu_keyboard()["inline_keyboard"]}); return
    send_message(chat_id, "ℹ️ Unknown action.", {"inline_keyboard": menu_keyboard()["inline_keyboard"]})

def poll_loop():
    # call once on start to avoid webhook conflict
    ensure_long_poll_ready()
    # present menu
    try: send_message(CHAT_ID, render_menu_text(), {"inline_keyboard": menu_keyboard()["inline_keyboard"]})
    except Exception as e: sys.stderr.write(f"[tele_control] startup send failed: {e}\n")

    offset = read_offset()
    while True:
        try:
            try:
                resp = get_updates(offset=offset, timeout=25)
            except urllib.error.HTTPError as he:
                # If we ever hit 409 mid-flight, clear webhook and retry
                if he.code == 409:
                    sys.stderr.write("[tele_control] 409 Conflict -> clearing webhook & retrying\n")
                    ensure_long_poll_ready()
                    time.sleep(1.0)
                    continue
                raise
            if not resp.get("ok", False):
                time.sleep(1); continue
            for upd in resp.get("result", []):
                upd_id = upd["update_id"]; offset = upd_id + 1; write_offset(offset)
                if "message" in upd:
                    msg = upd["message"]; chat = msg.get("chat",{}).get("id")
                    if str(chat) != str(CHAT_ID):  # safety
                        continue
                    text = msg.get("text","") or ""
                    if text.startswith("/"): handle_command(text, CHAT_ID, msg.get("entities"))
                    else: send_message(CHAT_ID, render_menu_text(), {"inline_keyboard": menu_keyboard()["inline_keyboard"]})
                if "callback_query" in upd:
                    cb = upd["callback_query"]; chat = cb.get("message",{}).get("chat",{}).get("id")
                    if str(chat) != str(CHAT_ID): 
                        continue
                    handle_callback(cb, CHAT_ID)
        except Exception as e:
            sys.stderr.write(f"[tele_control] loop error: {e}\n")
            time.sleep(2)

def main():
    if not BOT_TOKEN or not CHAT_ID:
        sys.stderr.write("[tele_control] Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID\n")
        sys.exit(1)
    poll_loop()

if __name__ == "__main__":
    main()
