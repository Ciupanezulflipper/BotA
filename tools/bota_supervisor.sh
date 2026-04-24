#!/data/data/com.termux/files/usr/bin/bash
###############################################################################
# FILE: tools/bota_supervisor.sh  v2.1
# PURPOSE: BotA health watchdog — runs every 5 min via cron.
#          Writes ONLY to state/runtime_health.json (never touches STATE.json).
#          Sends Telegram on state transitions only.
#          Safe restarts: crond only. Never touches trading logic.
#
# CRON:
#   */5 * * * * bash /data/data/com.termux/files/home/BotA/tools/bota_supervisor.sh \
#     >> /data/data/com.termux/files/home/BotA/logs/cron.supervisor.log 2>&1
#
# OUTPUT FILE: state/runtime_health.json
#   This is a live-updating operational file, separate from state/STATE.json.
#   STATE.json remains the canonical human/session snapshot.
#   The handoff pack should read both and merge for display.
###############################################################################

set -euo pipefail
shopt -s inherit_errexit 2>/dev/null || true

ROOT="${HOME}/BotA"
LOGS="${ROOT}/logs"
CACHE="${ROOT}/cache"
RUNTIME_HEALTH="${ROOT}/state/runtime_health.json"
DEGRADED_FLAG="${LOGS}/state/supervisor_degraded.flag"

# ── Thresholds ────────────────────────────────────────────────────────────────
MAX_WATCHER_AGE_MIN=20
MAX_UPDATER_AGE_MIN=20
MAX_SHADOW_AGE_MIN=20
MAX_LOCK_AGE_SECS=900
MAX_M15_CACHE_AGE_MIN=45
MAX_H1_CACHE_AGE_MIN=90

# ── Safe env loader (handles special chars in values) ─────────────────────────
load_env() {
  local f="$1"
  [[ -f "${f}" ]] || return 0
  while IFS= read -r line; do
    [[ "${line}" =~ ^[[:space:]]*# ]] && continue
    [[ -z "${line// }" ]] && continue
    [[ "${line}" =~ ^([A-Za-z_][A-Za-z0-9_]*)=(.*)$ ]] || continue

    local key="${BASH_REMATCH[1]}"
    local val="${BASH_REMATCH[2]}"

    if [[ "${val}" =~ ^\".*\"$ ]]; then
      val="${val:1:${#val}-2}"
    elif [[ "${val}" =~ ^\'.*\'$ ]]; then
      val="${val:1:${#val}-2}"
    fi

    export "${key}=${val}"
  done < "${f}"
}

load_env "${ROOT}/config/tele.env"
load_env "${ROOT}/.env.runtime"

TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-}"
TELEGRAM_CHAT_ID="${TELEGRAM_CHAT_ID:-}"

# ── Logging ──────────────────────────────────────────────────────────────────
log() {
  printf '[SUPERVISOR %s] %s\n' "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" "$*"
}

# ── Telegram ──────────────────────────────────────────────────────────────────
send_telegram() {
  local msg="$1"
  [[ -z "${TELEGRAM_BOT_TOKEN}" || -z "${TELEGRAM_CHAT_ID}" ]] && return 0
  curl -sS --max-time 10 -X POST \
    "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
    -d "chat_id=${TELEGRAM_CHAT_ID}" \
    -d "parse_mode=HTML" \
    --data-urlencode "text=${msg}" \
    > /dev/null 2>&1 || true
}

# ── File age helpers ──────────────────────────────────────────────────────────
file_age_min() {
  local f="$1"
  [[ ! -e "${f}" ]] && echo "99999" && return
  local mtime now
  mtime=$(stat -c %Y "${f}" 2>/dev/null || echo 0)
  now=$(date +%s)
  echo $(( (now - mtime) / 60 ))
}

file_age_secs() {
  local f="$1"
  [[ ! -e "${f}" ]] && echo "99999" && return
  local mtime now
  mtime=$(stat -c %Y "${f}" 2>/dev/null || echo 0)
  now=$(date +%s)
  echo $(( now - mtime ))
}

find_crond_pid() {
  if command -v pgrep >/dev/null 2>&1; then
    pgrep -x crond 2>/dev/null | head -1 || true
  else
    ps -ef 2>/dev/null | awk '/[c]rond/ {print $2; exit}' || true
  fi
}

# ── State variables ───────────────────────────────────────────────────────────
FAILURES=()
CROND_PID=""
LOCK_AGE_SECS=0
WATCHER_AGE_MIN=0
UPDATER_AGE_MIN=0
SHADOW_AGE_MIN=0
M15_EUR_AGE_MIN=0
M15_GBP_AGE_MIN=0
H1_EUR_AGE_MIN=0
H1_GBP_AGE_MIN=0

# ── Checks ────────────────────────────────────────────────────────────────────
check_crond() {
  CROND_PID="$(find_crond_pid)"
  if [[ -n "${CROND_PID}" ]]; then
    log "OK: crond PID=${CROND_PID}"
    return 0
  fi

  log "FAIL: crond not running — attempting restart"
  crond 2>/dev/null || true
  sleep 2

  CROND_PID="$(find_crond_pid)"
  if [[ -n "${CROND_PID}" ]]; then
    log "OK: crond restarted PID=${CROND_PID}"
  else
    FAILURES+=("crond_dead")
    log "FAIL: crond restart failed"
  fi
}

check_log_freshness() {
  WATCHER_AGE_MIN=$(file_age_min "${LOGS}/cron.signals.log")
  UPDATER_AGE_MIN=$(file_age_min "${LOGS}/cron.indicators.log")
  SHADOW_AGE_MIN=$(file_age_min "${LOGS}/cron.shadow.log")

  if (( WATCHER_AGE_MIN > MAX_WATCHER_AGE_MIN )); then
    FAILURES+=("watcher_stale:${WATCHER_AGE_MIN}min")
    log "FAIL: watcher log stale ${WATCHER_AGE_MIN}min"
  else
    log "OK: watcher log age=${WATCHER_AGE_MIN}min"
  fi

  if (( UPDATER_AGE_MIN > MAX_UPDATER_AGE_MIN )); then
    FAILURES+=("updater_stale:${UPDATER_AGE_MIN}min")
    log "FAIL: updater log stale ${UPDATER_AGE_MIN}min"
  else
    log "OK: updater log age=${UPDATER_AGE_MIN}min"
  fi

  if (( SHADOW_AGE_MIN > MAX_SHADOW_AGE_MIN )); then
    FAILURES+=("shadow_stale:${SHADOW_AGE_MIN}min")
    log "FAIL: shadow log stale ${SHADOW_AGE_MIN}min"
  else
    log "OK: shadow log age=${SHADOW_AGE_MIN}min"
  fi
}

check_lock() {
  local lockfile="${LOGS}/state/watcher.lock"
  if [[ ! -f "${lockfile}" ]]; then
    LOCK_AGE_SECS=0
    log "OK: no watcher.lock present"
    return 0
  fi

  LOCK_AGE_SECS=$(file_age_secs "${lockfile}")
  if (( LOCK_AGE_SECS > MAX_LOCK_AGE_SECS )); then
    FAILURES+=("stale_lock:${LOCK_AGE_SECS}s")
    log "FAIL: watcher.lock stale ${LOCK_AGE_SECS}s — removing"
    rm -f "${lockfile}" && log "ACTION: stale lock removed"
  else
    log "OK: watcher.lock age=${LOCK_AGE_SECS}s"
  fi
}

check_cache_freshness() {
  M15_EUR_AGE_MIN=$(file_age_min "${CACHE}/indicators_EURUSD_M15.json")
  M15_GBP_AGE_MIN=$(file_age_min "${CACHE}/indicators_GBPUSD_M15.json")
  H1_EUR_AGE_MIN=$(file_age_min "${CACHE}/indicators_EURUSD_H1.json")
  H1_GBP_AGE_MIN=$(file_age_min "${CACHE}/indicators_GBPUSD_H1.json")

  if (( M15_EUR_AGE_MIN > MAX_M15_CACHE_AGE_MIN )); then
    FAILURES+=("eurusd_m15_stale:${M15_EUR_AGE_MIN}min")
    log "FAIL: EURUSD M15 cache stale ${M15_EUR_AGE_MIN}min"
  else
    log "OK: EURUSD M15 cache age=${M15_EUR_AGE_MIN}min"
  fi

  if (( M15_GBP_AGE_MIN > MAX_M15_CACHE_AGE_MIN )); then
    FAILURES+=("gbpusd_m15_stale:${M15_GBP_AGE_MIN}min")
    log "FAIL: GBPUSD M15 cache stale ${M15_GBP_AGE_MIN}min"
  else
    log "OK: GBPUSD M15 cache age=${M15_GBP_AGE_MIN}min"
  fi

  if (( H1_EUR_AGE_MIN > MAX_H1_CACHE_AGE_MIN )); then
    FAILURES+=("eurusd_h1_stale:${H1_EUR_AGE_MIN}min")
    log "FAIL: EURUSD H1 cache stale ${H1_EUR_AGE_MIN}min"
  else
    log "OK: EURUSD H1 cache age=${H1_EUR_AGE_MIN}min"
  fi

  if (( H1_GBP_AGE_MIN > MAX_H1_CACHE_AGE_MIN )); then
    FAILURES+=("gbpusd_h1_stale:${H1_GBP_AGE_MIN}min")
    log "FAIL: GBPUSD H1 cache stale ${H1_GBP_AGE_MIN}min"
  else
    log "OK: GBPUSD H1 cache age=${H1_GBP_AGE_MIN}min"
  fi
}

# ── Write runtime_health.json (never touches STATE.json) ──────────────────────
write_runtime_health() {
  local bot_mode="$1"
  local failure_str="$2"
  mkdir -p "${ROOT}/state"

  python3 - <<PY
import json, datetime, os

path = "${RUNTIME_HEALTH}"
now = datetime.datetime.utcnow().isoformat() + "Z"

health = {
    "schema_version": "1.0",
    "file_purpose": "live runtime health — updated every 5min by supervisor. NOT the canonical session snapshot.",
    "canonical_snapshot": "state/STATE.json",
    "bot_mode": "${bot_mode}",
    "last_supervisor_run_utc": now,
    "crond_pid": "${CROND_PID}" if "${CROND_PID}" else None,
    "lock_age_secs": int("${LOCK_AGE_SECS}" or 0),
    "watcher_log_age_min": int("${WATCHER_AGE_MIN}" or 0),
    "updater_log_age_min": int("${UPDATER_AGE_MIN}" or 0),
    "shadow_log_age_min": int("${SHADOW_AGE_MIN}" or 0),
    "eurusd_m15_cache_age_min": int("${M15_EUR_AGE_MIN}" or 0),
    "gbpusd_m15_cache_age_min": int("${M15_GBP_AGE_MIN}" or 0),
    "eurusd_h1_cache_age_min": int("${H1_EUR_AGE_MIN}" or 0),
    "gbpusd_h1_cache_age_min": int("${H1_GBP_AGE_MIN}" or 0),
    "failure_reasons": "${failure_str}" if "${failure_str}" else None,
}

if os.path.exists(path):
    try:
        old = json.load(open(path, "r", encoding="utf-8"))
        if "${bot_mode}" != "HEALTHY" and "last_healthy_utc" in old:
            health["last_healthy_utc"] = old["last_healthy_utc"]
        if "${bot_mode}" != "DEGRADED" and "last_degraded_utc" in old:
            health["last_degraded_utc"] = old["last_degraded_utc"]
            health["last_degraded_reason"] = old.get("last_degraded_reason")
    except Exception:
        pass

if "${bot_mode}" == "HEALTHY":
    health["last_healthy_utc"] = now
else:
    health["last_degraded_utc"] = now
    health["last_degraded_reason"] = "${failure_str}"

tmp = path + ".tmp"
with open(tmp, "w", encoding="utf-8") as f:
    json.dump(health, f, indent=2, ensure_ascii=True)
os.replace(tmp, path)
print("RUNTIME_HEALTH_WRITTEN")
PY
}

# ── Main ──────────────────────────────────────────────────────────────────────
log "=== SUPERVISOR START ==="
mkdir -p "${LOGS}/state"

check_crond
check_log_freshness
check_lock
check_cache_freshness

NOW_EPOCH=$(date +%s)
BOT_MODE="HEALTHY"
FAILURE_STR=""

if (( ${#FAILURES[@]} > 0 )); then
  BOT_MODE="DEGRADED"
  FAILURE_STR=$(IFS='|'; echo "${FAILURES[*]}")
  log "DEGRADED: ${FAILURE_STR}"

  if [[ ! -f "${DEGRADED_FLAG}" ]]; then
    send_telegram "[BotA DEGRADED] ${FAILURE_STR} — $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "${NOW_EPOCH}|${FAILURE_STR}" > "${DEGRADED_FLAG}"
    log "ACTION: Telegram DEGRADED alert sent"
  fi
else
  BOT_MODE="HEALTHY"
  log "HEALTHY: all checks passed"

  if [[ -f "${DEGRADED_FLAG}" ]]; then
    send_telegram "[BotA RECOVERY] All checks passing — $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    rm -f "${DEGRADED_FLAG}"
    log "ACTION: Telegram RECOVERY alert sent"
  fi
fi

write_runtime_health "${BOT_MODE}" "${FAILURE_STR}"
log "=== SUPERVISOR DONE: bot_mode=${BOT_MODE} ==="
