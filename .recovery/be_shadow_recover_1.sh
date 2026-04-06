python3 - <<'PY'
from pathlib import Path
import os, sys, requests, gzip, base64, py_compile

BASE = Path.home() / "BotA"
cfg = BASE / "config" / "strategy.env"
cfg.parent.mkdir(parents=True, exist_ok=True)

def load_env(path: Path):
    env = {}
    if not path.exists():
        return env
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        s = raw.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        if s.startswith("export "):
            s = s[7:]
        k, v = s.split("=", 1)
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env

env = {}
for p in [BASE/".env.runtime", BASE/".env", BASE/"config"/"strategy.env", BASE/"strategy.env"]:
    env.update(load_env(p))

token = env.get("OANDA_API_TOKEN") or env.get("OANDA_API_KEY") or ""
if not token:
    print("FAIL: OANDA_API_TOKEN/OANDA_API_KEY missing")
    print("FILE REPLACED: NO")
    sys.exit(1)

mode = None
for name, url in [
    ("PRACTICE", "https://api-fxpractice.oanda.com/v3/accounts"),
    ("LIVE", "https://api-fxtrade.oanda.com/v3/accounts"),
]:
    try:
        r = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=12)
        if r.status_code == 200:
            mode = name
            break
    except Exception:
        pass

if not mode:
    print("FAIL: could not auto-detect OANDA_MODE with current token")
    print("FILE REPLACED: NO")
    sys.exit(1)

updates = {
    "SUPABASE_URL": env.get("SUPABASE_URL") or "https://ozgkeslgjqbqfewojnmr.supabase.co",
    "SHADOW_ENABLED": "true",
    "BE_R_THRESHOLD": "1.0",
    "OANDA_MODE": mode,
    "MIRROR_DIVERGENCE_THRESHOLD_PIPS": "2.0",
    "RECONCILE_RETRY_COOLDOWN_MINUTES": "60",
    "RECONCILE_MAX_AGE_HOURS": "96",
}

existing = cfg.read_text(encoding="utf-8", errors="ignore").splitlines() if cfg.exists() else []
out = []
seen = set()
for line in existing:
    s = line.strip()
    if "=" in s and not s.startswith("#"):
        k = s.split("=", 1)[0].strip()
        if k in updates:
            out.append(f"{k}={updates[k]}")
            seen.add(k)
            continue
    out.append(line)
for k, v in updates.items():
    if k not in seen:
        out.append(f"{k}={v}")
cfg.write_text("\n".join(out).rstrip() + "\n", encoding="utf-8")

blob = """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’wini+LKQS6A0uCjBpPq7q6KrjnjtpBNa9yjNAcsk5nOx/8RhMzbdEY8t7U7pXqjr6d8nZpjdI’winiVRbzLDXZWk1hCGhIgjwULm7xoPfh6bNVWXHKIQSaFjDIyFiYx7r5QJmPK8T4UUcL+fQyjg+ZwmhXmBc16V6Y7RuQFxP9D19t8UyWWB2Dg7B1JwET8a+0vjhXDCP9tMP42d7Uಳ್ಳಿLI1iaAAOyo6kgjQ+1Yc9VDGChJKSQQG+QoeC4mL2C+YbcQVO6gsRWuCs+8H9m0uPY6VBwH3kyg0nvyxgdPMPwdhuIuiElKhkiLQnMR4/E/5ivvi6RPEA7QmWGEW1/mBrqYAp4J+NRqzLIlHwKiA54I6Qqo2H9bxiaZJyt5DdrjWgE5rbhrZYR8uMGP+JL6tK21uilv8vH5brcVAfgC8PuilletIU2qdvHH5dYBuPRzqvWl9po8aQATj/Vs+0zuilletBznNa8+5ywrSJLVaO3FExMHOin4JYxT7/vu8hbm+OM6vTVweFzg/Mz9wr+86scGvbfxqNstJcBT5uiladfWaMq4EU9WJzN6rMp9q7JxurKdVfxsD4kt3vfXnDX0U0uilEGR0PbuilC4frscNrO5utDq8HfhSuilGH9MfGsvBkONqM9ri+ec6h5fX/oNGlEHBca8HcWuilVk/W0aHBA7mZIeNuilvti++cp6Ghr6Ulp5R48FuilAVnGkg+KQeCx7MZ+f9Muilz8Gg5vL90hfnHHVxbraDgmme1/7Y3Bduil+9Si4Kr5yVgNNuL7NWAdwgUfv/IBnHA4MsPvdIBvpjlwmmM8ObjlwmuqtstfO18z/Zbm/TK6AhKU+MTbb3Z4EroqWuil7HF3a44+Qnjlwm+4AEL02efvz58YA13uilSWuMaLOu3iKRRVrg+7ryhN1XfU8s3CgPxxIHXz5w8Qvquil5dm1ZSJduil08AgRPsQifMfwOq0fr7FUwAA"""
target = BASE / "tools" / "be_shadow_manager.py"
target.parent.mkdir(parents=True, exist_ok=True)
target.write_bytes(gzip.decompress(base64.b64decode(blob)))
py_compile.compile(str(target), doraise=True)

print("PASS: be_shadow_manager.py written and syntax OK")
print("FILE REPLACED: YES")
print(f"OANDA_MODE auto-detected: {mode}")
print(f"SUPABASE_URL set: {updates['SUPABASE_URL']}")
print("PASS/FAIL GUIDE: PASS only if you see this message and no traceback above")
print("SMART USAGE: one recent-terminal fetch per cycle, no separate MFE observer, unresolved reconciliation cooldown = 60m")
PY
