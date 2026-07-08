#!/data/data/com.termux/files/usr/bin/bash
# FILE: tools/daily_summary.sh
# ROLE: BotA Daily Proof-of-Work Summary
#
# Reports what BotA actually did today:
# - cron/runtime status
# - market gate status
# - scan/candidate/rejection counts
# - best candidate and rejection reason
# - API credit usage
# - clock drift status
#
# Safety:
# - No strategy changes
# - No threshold changes
# - No H1 logic changes
# - No signal generation changes

set -euo pipefail

ROOT="${BOTA_ROOT:-${HOME}/BotA}"
LOGDIR="${ROOT}/logs"
CFGDIR="${ROOT}/config"
mkdir -p "${LOGDIR}"

DOTENV="${ROOT}/.env"
RUNTIME_ENV="${ROOT}/.env.runtime"
SIGENV="${CFGDIR}/signal.env"
TELEENV="${CFGDIR}/tele.env"

ts_utc() { date -u +'%Y-%m-%d %H:%M:%S UTC'; }

load_env_file() {
  local f="$1"
  [[ -f "$f" ]] || return 0

  while IFS= read -r line || [[ -n "$line" ]]; do
    [[ -z "$line" || "$line" =~ ^[[:space:]]*# || "$line" != *"="* ]] && continue

    local key val
    key="${line%%=*}"
    val="${line#*=}"

    key="$(printf '%s' "$key" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
    val="$(printf '%s' "$val" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"

    [[ "$key" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] || continue

    val="${val%\"}"
    val="${val#\"}"
    val="${val%\'}"
    val="${val#\'}"

    if [[ -z "${!key-}" ]]; then
      export "${key}=${val}"
    fi
  done < "$f"
}

load_env_file "$DOTENV"
load_env_file "$RUNTIME_ENV"
load_env_file "$SIGENV"
load_env_file "$TELEENV"

tg_send_plain() {
  local text="$1"
  local token="${TELEGRAM_BOT_TOKEN:-${TELEGRAM_TOKEN:-${BOT_TOKEN:-}}}"
  local chat_id="${TELEGRAM_CHAT_ID:-${CHAT_ID:-${TG_CHAT_ID:-}}}"

  if [[ "${DAILY_SUMMARY_SEND:-1}" = "0" ]]; then
    echo "[daily] SEND_SKIPPED DAILY_SUMMARY_SEND=0"
    return 0
  fi

  if [[ -z "$token" || -z "$chat_id" ]]; then
    echo "[daily] TELEGRAM_SEND=SKIPPED reason=missing_token_or_chat"
    return 0
  fi

  local api="https://api.telegram.org/bot${token}/sendMessage"
  local resp http_code body

  resp="$(
    curl -sS -w $'\nHTTP_STATUS:%{http_code}\n' -X POST "$api" \
      --data-urlencode "chat_id=${chat_id}" \
      --data-urlencode "disable_web_page_preview=true" \
      --data-urlencode "text=${text}" || true
  )"

  http_code="$(printf '%s' "$resp" | sed -n 's/^HTTP_STATUS:\([0-9][0-9][0-9]\)$/\1/p' | tail -n 1)"
  body="$(printf '%s' "$resp" | sed '/^HTTP_STATUS:[0-9][0-9][0-9]$/d')"

  if printf '%s' "$body" | grep -q '"ok":true'; then
    echo "[daily] TELEGRAM_SEND=PASS http=${http_code:-unknown}"
  else
    echo "[daily] TELEGRAM_SEND=FAIL http=${http_code:-unknown} body=$(printf '%s' "$body" | tr '\n' ' ' | head -c 240)"
  fi
}

SUMMARY="$(
BOTA_ROOT="$ROOT" python3 - <<'PY'
import csv
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(os.environ.get("BOTA_ROOT", str(Path.home() / "BotA"))).expanduser().resolve()
LOGDIR = ROOT / "logs"
TODAY = os.environ.get("SUMMARY_DATE") or datetime.now(timezone.utc).strftime("%Y-%m-%d")
NOW_UTC = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

ALERTS = LOGDIR / "alerts.csv"
API_STATE = LOGDIR / "api_credits.json"
CLOCK_STATE = LOGDIR / "clock_drift_status.json"
CRON_SIGNALS = LOGDIR / "cron.signals.log"
CRON_INDICATORS = LOGDIR / "cron.indicators.log"
CRON_CLOSER = LOGDIR / "cron.closer.log"
CRON_SHADOW = LOGDIR / "cron.shadow.log"
CRON_SUPERVISOR = LOGDIR / "cron.supervisor.log"
RUNTIME_HEALTH = ROOT / "state" / "runtime_health.json"
VERIFY_CANONICAL = ROOT / "tools" / "verify_canonical_crontab.sh"

API_DAILY_LIMIT = int(os.environ.get("API_DAILY_LIMIT", "800"))

def safe_float(value, default=0.0):
    try:
        return float(str(value).strip())
    except Exception:
        return default

def safe_int(value, default=0):
    try:
        return int(float(str(value).strip()))
    except Exception:
        return default

TELEGRAM_MIN_SCORE = safe_float(os.environ.get("TELEGRAM_MIN_SCORE", "70"), 70.0)
RUNTIME_HEALTH_FRESH_MAX_MIN = safe_int(os.environ.get("RUNTIME_HEALTH_FRESH_MAX_MIN", "10"), 10)
RUNTIME_JOB_FRESH_MAX_MIN = safe_int(os.environ.get("RUNTIME_JOB_FRESH_MAX_MIN", "30"), 30)

def load_json(path, default):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        pass
    return default

def parse_dt_any(ts):
    ts = (ts or "").strip()
    if not ts:
        return None
    try:
        # Handles 2026-05-19T18:45:25+1000
        return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S%z").astimezone(timezone.utc)
    except Exception:
        pass
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return None

def row_is_today(ts):
    ts = (ts or "").strip()
    if ts.startswith(TODAY):
        return True
    dt = parse_dt_any(ts)
    return bool(dt and dt.strftime("%Y-%m-%d") == TODAY)

def clean_filter_text(text):
    text = (text or "").strip()
    if not text:
        return "none"
    return " ".join(text.replace(" | ", " / ").split())

def crond_status():
    try:
        r = subprocess.run(["pgrep", "-x", "crond"], text=True, capture_output=True, timeout=3)
        return "running" if r.returncode == 0 else "not_running"
    except Exception:
        return "unknown"

def market_gate_status():
    script = ROOT / "tools" / "market_open.sh"
    if not script.exists():
        return "unknown", "market_open.sh missing"
    try:
        env = os.environ.copy()
        env["MARKET_OPEN_DEBUG"] = "1"
        r = subprocess.run(
            ["bash", str(script)],
            text=True,
            capture_output=True,
            timeout=30,
            env=env,
        )
        status = (r.stdout or "").strip() or ("Open" if r.returncode == 0 else "Closed")
        debug_lines = [x.strip() for x in (r.stderr or "").splitlines() if x.strip()]
        reason = debug_lines[-1].replace("[MARKET_OPEN]", "").strip() if debug_lines else "no_debug_reason"
        return status, reason
    except subprocess.TimeoutExpired:
        return "unknown", "market_open timeout"
    except Exception as exc:
        return "unknown", f"market_open error {type(exc).__name__}"

def read_alert_rows():
    rows = []
    if not ALERTS.exists():
        return rows
    try:
        with ALERTS.open("r", encoding="utf-8", errors="ignore", newline="") as f:
            reader = csv.reader(f)
            for row in reader:
                if not row or len(row) < 13:
                    continue
                if row[0].lower().startswith("timestamp") or row[0].lower().startswith("ts"):
                    continue
                if not row_is_today(row[0]):
                    continue

                direction = (row[3] if len(row) > 3 else "").strip().upper()
                score = safe_float(row[4] if len(row) > 4 else 0)
                conf = safe_float(row[5] if len(row) > 5 else 0)
                rejected_raw = (row[10] if len(row) > 10 else "").strip().lower()
                rejected = rejected_raw in ("true", "1", "yes", "y")
                filters = row[11] if len(row) > 11 else ""
                reason = row[12] if len(row) > 12 else ""

                rows.append({
                    "ts": row[0],
                    "pair": (row[1] if len(row) > 1 else "").strip(),
                    "tf": (row[2] if len(row) > 2 else "").strip(),
                    "direction": direction,
                    "score": score,
                    "confidence": conf,
                    "entry": row[6] if len(row) > 6 else "",
                    "sl": row[7] if len(row) > 7 else "",
                    "tp": row[8] if len(row) > 8 else "",
                    "provider": row[9] if len(row) > 9 else "",
                    "rejected": rejected,
                    "filters": filters,
                    "reason": reason,
                })
    except Exception:
        return rows
    return rows

def count_signal_log_today():
    if not CRON_SIGNALS.exists():
        return {"filter_lines": 0, "accepted_lines": 0, "skip_lines": 0}
    try:
        text = CRON_SIGNALS.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception:
        return {"filter_lines": 0, "accepted_lines": 0, "skip_lines": 0}

    filter_lines = 0
    accepted_lines = 0
    skip_lines = 0
    for line in text[-3000:]:
        if TODAY not in line and "market_closed_or_gate_failed" in line:
            # Some skip lines have no timestamp. Count only recent tail as rough operational evidence.
            skip_lines += 1
            continue
        if TODAY not in line:
            continue
        if "rejected_by_filter" in line:
            filter_lines += 1
        if " accepted" in line or "accepted " in line:
            accepted_lines += 1
        if "market_closed_or_gate_failed" in line:
            skip_lines += 1
    return {"filter_lines": filter_lines, "accepted_lines": accepted_lines, "skip_lines": skip_lines}

# PHASE4C_RUNTIME_HEALTH_V1
def safe_int_or_none(value):
    if value is None:
        return None
    try:
        return int(float(str(value).strip()))
    except Exception:
        return None

def file_age_min(path):
    try:
        age = int((datetime.now(timezone.utc).timestamp() - path.stat().st_mtime) // 60)
        return max(age, 0)
    except Exception:
        return None

def age_from_utc_value(value):
    dt = parse_dt_any(str(value or ""))
    if not dt:
        return None
    return int((datetime.now(timezone.utc) - dt).total_seconds() // 60)

def fmt_age(age):
    if age is None:
        return "N/A"
    if age < 0:
        return f"future {abs(age)}m"
    if age < 60:
        return f"{age}m"
    return f"{age // 60}h{age % 60:02d}m"

def compact_reasons(reasons, limit=260):
    cleaned = []
    for reason in reasons:
        r = " ".join(str(reason).replace(str(ROOT), "<ROOT>").split())
        if r and r not in cleaned:
            cleaned.append(r)
    if not cleaned:
        return "none"
    out = "; ".join(cleaned)
    if len(out) <= limit:
        return out
    return out[:limit].rstrip() + "..."

def run_canonical_verify():
    if not VERIFY_CANONICAL.exists():
        return {"status": "UNKNOWN", "hash_match": "UNKNOWN", "reason": "canonical verifier missing"}

    try:
        r = subprocess.run(
            ["bash", str(VERIFY_CANONICAL)],
            cwd=str(ROOT),
            text=True,
            capture_output=True,
            timeout=10,
        )
        out = ((r.stdout or "") + "\n" + (r.stderr or ""))[:12000]
    except subprocess.TimeoutExpired:
        return {"status": "UNKNOWN", "hash_match": "UNKNOWN", "reason": "canonical verifier timeout"}
    except Exception as exc:
        return {"status": "UNKNOWN", "hash_match": "UNKNOWN", "reason": f"canonical verifier error {type(exc).__name__}"}

    pass_yes = "PHASE2_VERIFY_PASS=YES" in out
    pass_no = "PHASE2_VERIFY_PASS=NO" in out
    hash_yes = "BOTA_BLOCK_HASH_MATCH=YES" in out
    hash_no = "BOTA_BLOCK_HASH_MATCH=NO" in out

    if pass_yes and hash_yes:
        return {"status": "PASS", "hash_match": "YES", "reason": "none"}
    if pass_no or hash_no:
        return {"status": "FAIL", "hash_match": "NO" if hash_no else "UNKNOWN", "reason": "canonical verification failed"}
    if r.returncode != 0:
        return {"status": "UNKNOWN", "hash_match": "UNKNOWN", "reason": f"canonical verifier rc={r.returncode}"}
    return {"status": "UNKNOWN", "hash_match": "UNKNOWN", "reason": "canonical verifier markers missing"}

def load_runtime_health_strict():
    if not RUNTIME_HEALTH.exists():
        return None, "missing"
    try:
        return json.loads(RUNTIME_HEALTH.read_text(encoding="utf-8", errors="ignore")), None
    except Exception:
        return None, "corrupt"

def runtime_health_summary():
    health, err = load_runtime_health_strict()
    reasons = []
    reported = "UNKNOWN"
    last_supervisor = "N/A"
    supervisor_age = None
    health_file_age = file_age_min(RUNTIME_HEALTH)

    job_ages = {
        "watcher": file_age_min(CRON_SIGNALS),
        "updater": file_age_min(CRON_INDICATORS),
        "closer": file_age_min(CRON_CLOSER),
        "shadow": file_age_min(CRON_SHADOW),
    }
    cache_ages = {
        "EUR_M15": None,
        "GBP_M15": None,
        "EUR_H1": None,
        "GBP_H1": None,
    }

    if err == "missing":
        reasons.append("runtime_health missing")
        return {
            "effective": "UNKNOWN",
            "reported": reported,
            "last_supervisor": last_supervisor,
            "supervisor_age": supervisor_age,
            "health_file_age": health_file_age,
            "job_ages": job_ages,
            "cache_ages": cache_ages,
            "reasons": reasons,
        }

    if err == "corrupt":
        reasons.append("runtime_health corrupt")
        return {
            "effective": "DEGRADED",
            "reported": reported,
            "last_supervisor": last_supervisor,
            "supervisor_age": supervisor_age,
            "health_file_age": health_file_age,
            "job_ages": job_ages,
            "cache_ages": cache_ages,
            "reasons": reasons,
        }

    if isinstance(health, dict):
        reported = str(health.get("bot_mode", "UNKNOWN")).upper()
        last_supervisor = str(health.get("last_supervisor_run_utc", "N/A"))
        supervisor_age = age_from_utc_value(last_supervisor)

        job_ages["watcher"] = safe_int_or_none(health.get("watcher_log_age_min")) or job_ages["watcher"]
        job_ages["updater"] = safe_int_or_none(health.get("updater_log_age_min")) or job_ages["updater"]
        job_ages["shadow"] = safe_int_or_none(health.get("shadow_log_age_min")) or job_ages["shadow"]

        cache_ages["EUR_M15"] = safe_int_or_none(health.get("eurusd_m15_cache_age_min"))
        cache_ages["GBP_M15"] = safe_int_or_none(health.get("gbpusd_m15_cache_age_min"))
        cache_ages["EUR_H1"] = safe_int_or_none(health.get("eurusd_h1_cache_age_min"))
        cache_ages["GBP_H1"] = safe_int_or_none(health.get("gbpusd_h1_cache_age_min"))

        failure_reasons = health.get("failure_reasons")
        if failure_reasons:
            reasons.append(f"reported failure: {failure_reasons}")

    if health_file_age is None:
        reasons.append("runtime_health file age unknown")
    elif health_file_age > RUNTIME_HEALTH_FRESH_MAX_MIN:
        reasons.append(f"runtime_health file stale:{health_file_age}m")

    if supervisor_age is None:
        reasons.append("supervisor timestamp missing")
    elif supervisor_age < -2:
        reasons.append(f"supervisor timestamp future:{supervisor_age}m")
    elif supervisor_age > RUNTIME_HEALTH_FRESH_MAX_MIN:
        reasons.append(f"supervisor stale:{supervisor_age}m")

    for name, age in job_ages.items():
        if age is None:
            reasons.append(f"{name} age unknown")
        elif age > RUNTIME_JOB_FRESH_MAX_MIN:
            reasons.append(f"{name} stale:{age}m")

    if reported != "HEALTHY":
        reasons.append(f"reported mode:{reported}")

    effective = "HEALTHY" if not reasons and reported == "HEALTHY" else "DEGRADED"
    return {
        "effective": effective,
        "reported": reported,
        "last_supervisor": last_supervisor,
        "supervisor_age": supervisor_age,
        "health_file_age": health_file_age,
        "job_ages": job_ages,
        "cache_ages": cache_ages,
        "reasons": reasons,
    }

def build_runtime_truth_lines(runtime, canonical):
    reasons = list(runtime["reasons"])

    if canonical["status"] == "FAIL" or canonical["hash_match"] == "NO":
        reasons.append(canonical["reason"])
        effective = "DEGRADED"
    elif canonical["status"] != "PASS" or canonical["hash_match"] != "YES":
        reasons.append(canonical["reason"])
        effective = "UNKNOWN" if runtime["effective"] == "HEALTHY" else runtime["effective"]
    else:
        effective = runtime["effective"]

    status_icon = {"HEALTHY": "✅", "DEGRADED": "⚠️", "UNKNOWN": "❓"}.get(effective, "❓")
    verify_icon = "✅" if canonical["status"] == "PASS" else "❌" if canonical["status"] == "FAIL" else "❓"
    hash_icon = "✅" if canonical["hash_match"] == "YES" else "❌" if canonical["hash_match"] == "NO" else "❓"

    j = runtime["job_ages"]
    c = runtime["cache_ages"]

    return [
        f"Runtime: {status_icon} {effective} | Reported: {runtime['reported']}",
        f"Supervisor: {fmt_age(runtime['supervisor_age'])} ago | Last: {runtime['last_supervisor']}",
        f"Jobs: watcher {fmt_age(j.get('watcher'))} | updater {fmt_age(j.get('updater'))} | closer {fmt_age(j.get('closer'))} | shadow {fmt_age(j.get('shadow'))}",
        f"Caches: EUR M15 {fmt_age(c.get('EUR_M15'))} | GBP M15 {fmt_age(c.get('GBP_M15'))} | EUR H1 {fmt_age(c.get('EUR_H1'))} | GBP H1 {fmt_age(c.get('GBP_H1'))}",
        f"Canonical crontab: {verify_icon} {canonical['status']} | Hash match: {hash_icon} {canonical['hash_match']}",
        f"Reasons: {compact_reasons(reasons)}",
    ]

rows = read_alert_rows()
tradeable = [r for r in rows if r["direction"] in ("BUY", "SELL")]
holds = [r for r in rows if r["direction"] not in ("BUY", "SELL")]
filter_accepted = [r for r in tradeable if not r["rejected"]]
filter_rejected = [r for r in tradeable if r["rejected"]]
telegram_threshold_eligible = [r for r in filter_accepted if r["score"] >= TELEGRAM_MIN_SCORE]

best = max(tradeable, key=lambda r: r["score"], default=None)
latest = rows[-1] if rows else None

h1_rejects = sum(1 for r in filter_rejected if "H1" in r["filters"])
score_rejects = sum(1 for r in filter_rejected if "score<" in r["filters"])
macro_rejects = sum(1 for r in rows if "macro6" in r["filters"])
not_tradeable = sum(1 for r in rows if "direction_not_tradeable" in r["filters"] or r["direction"] == "HOLD")

api = load_json(API_STATE, {})
api_used = safe_int(api.get("used", 0))
api_limit = safe_int(os.environ.get("API_DAILY_LIMIT", API_DAILY_LIMIT), API_DAILY_LIMIT)
api_pct = (api_used / api_limit * 100.0) if api_limit else 0.0
api_warned = api.get("warned", False)
api_icon = "🟢" if api_pct < 50 else "🟡" if api_pct < 75 else "🔴"

clock = load_json(CLOCK_STATE, {})
clock_status = clock.get("status", "UNKNOWN")
drift = clock.get("drift_seconds", "UNKNOWN")
clock_ok = clock.get("server_clock_ok", "UNKNOWN")
clock_unsafe = clock.get("local_clock_unsafe", "UNKNOWN")

market_status, market_reason = market_gate_status()
cron_status = crond_status()
siglog = count_signal_log_today()
runtime_truth = runtime_health_summary()
canonical_truth = run_canonical_verify()
runtime_truth_lines = build_runtime_truth_lines(runtime_truth, canonical_truth)

def best_line(r):
    if not r:
        return "none"
    if r["rejected"]:
        return f'{r["pair"]} {r["direction"]} score={r["score"]:.2f} → filter-rejected: {clean_filter_text(r["filters"])}'
    if r["score"] >= TELEGRAM_MIN_SCORE:
        return f'{r["pair"]} {r["direction"]} score={r["score"]:.2f} → filter-accepted / Telegram-threshold eligible'
    return f'{r["pair"]} {r["direction"]} score={r["score"]:.2f} → filter-accepted / below Telegram threshold {TELEGRAM_MIN_SCORE:.2f}'

def latest_line(r):
    if not r:
        return "none"
    return f'{r["pair"]} {r["tf"]} {r["direction"]} score={r["score"]:.2f} filters={clean_filter_text(r["filters"])}'

lines = []
lines.append(f"✅ BotA Daily Proof-of-Work — {TODAY}")
lines.append(f"Generated: {NOW_UTC}")
lines.append("")
lines.extend(runtime_truth_lines)
lines.append("")
lines.append(f"Cron: {cron_status} | Market gate now: {market_status}")
lines.append(f"Market reason: {market_reason}")
lines.append("")
lines.append(f"Scans logged: {len(rows)} | Candidates: {len(tradeable)} | HOLD/no-trade: {len(holds)}")
lines.append(f"Filter-accepted candidates: {len(filter_accepted)} | Filter-rejected candidates: {len(filter_rejected)}")
lines.append(f"Telegram-threshold eligible: {len(telegram_threshold_eligible)} | Send threshold: {TELEGRAM_MIN_SCORE:.2f}")
lines.append(f"Reject mix: H1={h1_rejects} | score_gate={score_rejects} | macro6={macro_rejects} | no_trade={not_tradeable}")
lines.append("")
lines.append(f"Best candidate: {best_line(best)}")
lines.append(f"Latest row: {latest_line(latest)}")
lines.append("")
lines.append(f"Signal log evidence: filter_lines={siglog['filter_lines']} | watcher_accepted_log_lines={siglog['accepted_lines']} | market_skip_tail={siglog['skip_lines']}")
lines.append(f"API usage: {api_used}/{api_limit} ({api_pct:.1f}%) {api_icon} | warned={str(api_warned).lower()}")
lines.append(f"Clock drift: {clock_status} | drift={drift}s | server_clock_ok={str(clock_ok).lower()} | local_clock_unsafe={str(clock_unsafe).lower()}")
lines.append("")
lines.append("Strategy: unchanged | H1: unchanged | thresholds: unchanged")
lines.append("Production trading behavior: unchanged")

print("\n".join(lines))
PY
)"

echo "$SUMMARY"

SEND_RESULT="$(tg_send_plain "$SUMMARY" || true)"

{
  echo "[$(ts_utc)] DAILY_PROOF_OF_WORK"
  echo "$SEND_RESULT"
  echo "$SUMMARY"
  echo
} >> "${LOGDIR}/daily_summary.log"

echo "$SEND_RESULT"

exit 0
