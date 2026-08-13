from __future__ import annotations
import os, sys, json, subprocess
from datetime import datetime

BOT_ROOT = os.path.expanduser("~/BotA")
if BOT_ROOT not in sys.path:
    sys.path.insert(0, BOT_ROOT)

def _short_env(keys):
    out={}
    for k in keys:
        v=os.getenv(k)
        if v:
            out[k]=(v[:4]+"…"+v[-3:]) if len(v)>10 else v
    return out

def _cmd(argv, limit=None):
    """Run argv without a shell and return (ok, output)."""
    try:
        out=subprocess.check_output(argv, stderr=subprocess.STDOUT, text=True, timeout=12)
        out=out.strip()
        return True, out[:limit] if limit else out
    except Exception as e:
        return False, str(e)

def main():
    checks={"python_version": sys.version}
    for mod in ("tools.indicators_ext","tools.scoring_v2","tools.signal_card","tools.runner_confluence","tools.providers","tools.indicators_patch"):
        try:
            __import__(mod)
            checks[f"import:{mod}"]="ok"
        except Exception as e:
            checks[f"import:{mod}"]=f"FAIL: {e}"

    checks["env"]=_short_env(["TELEGRAM_BOT_TOKEN","TELEGRAM_CHAT_ID","TWELVE_DATA_API_KEY","ALPHA_VANTAGE_API_KEY","FINNHUB_API_KEY"])

    ok,out=_cmd(["grep","-n","reason=hourly",os.path.expanduser("~/.termux/cron.d/bota_heartbeat")])
    checks["cron_file"]={"ok":ok,"out":out}

    ok,out=_cmd(["ps","-Af"])
    if ok:
        out="\n".join(ln for ln in out.splitlines() if "crond" in ln.lower())
    checks["crond_ps"]={"ok":ok,"out":out}

    ok,out=_cmd(["tmux","ls"])
    checks["tmux_ls"]={"ok":ok,"out":out}

    tg_token=os.getenv("TELEGRAM_BOT_TOKEN")
    if tg_token and os.getenv("TELEGRAM_CHAT_ID"):
        # Only the HTTP status code is captured, so the token is never echoed.
        ok,out=_cmd(["curl","-sS","-o","/dev/null","-w","%{http_code}",
                     f"https://api.telegram.org/bot{tg_token}/getMe"])
        checks["ping_tg"]={"ok":True,"out":("OK" if ok and out=="200" else "FAIL")}
    else:
        checks["ping_tg"]={"ok":True,"out":"ENV not set"}

    providers={
        "twelvedata": ("TWELVE_DATA_API_KEY",
                       "https://api.twelvedata.com/time_series"
                       "?symbol=EUR/USD&interval=15min&outputsize=3&apikey={key}"),
        "alphavantage": ("ALPHA_VANTAGE_API_KEY",
                         "https://www.alphavantage.co/query"
                         "?function=FX_DAILY&from_symbol=EUR&to_symbol=USD&apikey={key}"),
    }
    for name,(env_key,url_tmpl) in providers.items():
        key=os.getenv(env_key)
        if not key:
            checks[name]={"ok":True,"out":f"{env_key} not set"}
            continue
        ok,out=_cmd(["curl","-sS",url_tmpl.format(key=key)], limit=240)
        checks[name]={"ok":ok,"out":out}

    for tag, path in {"bot_log_tail":"~/BotA/logs/bot.log","tg_log_tail":"~/BotA/logs/tg_bot.log","hb_log_tail":"~/BotA/logs/statusd.log"}.items():
        ok,out=_cmd(["tail","-n","40",os.path.expanduser(path)])
        checks[tag]={"ok":ok,"out":out}

    print("=== SELF CHECK ===")
    print(json.dumps({"timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"), "checks":checks}, indent=2))

    print("\n=== PRD CARD SMOKE (DRY RUN) ===")
    ok,out=_cmd([sys.executable,"-m","tools.runner_confluence","--pair","EURUSD","--tf","M15","--force","--dry-run=true"])
    print(out if ok else f"[FATAL] runner error: {out}")
if __name__=="__main__": main()
