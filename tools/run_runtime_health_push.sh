#!/usr/bin/env bash
# BotA Phase 5 runtime health push wrapper.
# Cron-safe wrapper around tools/push_runtime_health_supabase.py.
# Does not print secrets. Does not use privileged Supabase database keys.

set +e

CODE_ROOT="${BOTA_CODE_ROOT:-${BOTA_ROOT:-${HOME}/BotA}}"
MUTABLE_ROOT="${BOTA_MUTABLE_ROOT:-${CODE_ROOT}}"
ROOT="${CODE_ROOT}"
SCRIPT="$CODE_ROOT/tools/push_runtime_health_supabase.py"
SECRET_FILE="$CODE_ROOT/config/bota_health_ingest.env"
LOG="$MUTABLE_ROOT/logs/cron.runtime_health_push.log"
LOCK="$MUTABLE_ROOT/state/runtime_health_push.lock"

if [ "${BOTA_PATH_CONTRACT_CHECK:-0}" = "1" ]; then
  printf 'CODE_ROOT=%s\nMUTABLE_ROOT=%s\nSCRIPT=%s\nCONFIG=%s\nLOGS=%s\nSTATE=%s\nLOCK=%s\n' \
    "$CODE_ROOT" "$MUTABLE_ROOT" "$SCRIPT" "$SECRET_FILE" \
    "$MUTABLE_ROOT/logs" "$MUTABLE_ROOT/state" "$LOCK"
  exit 0
fi

mkdir -p "$MUTABLE_ROOT/logs" "$MUTABLE_ROOT/state"

ts_utc="$(date -u '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null)"

{
  echo "=== BotA runtime health push start: $ts_utc ==="
  echo "ROOT=$ROOT"
  echo "SCRIPT_PRESENT=$([ -f "$SCRIPT" ] && echo YES || echo NO)"
  echo "SECRET_FILE_PRESENT=$([ -f "$SECRET_FILE" ] && echo YES || echo NO)"
  echo "SECRET_VALUE_PRINTED=NO"
} >> "$LOG" 2>&1

if [ ! -f "$SCRIPT" ]; then
  echo "RESULT=FAIL_MISSING_SCRIPT" >> "$LOG" 2>&1
  echo "=== BotA runtime health push end ===" >> "$LOG" 2>&1
  exit 0
fi

# R5 is an observation-only VPS experiment. Build the normal payload locally,
# but do not read any ingest secret and never cross the Supabase write boundary.
if [ "${BOTA_R5_SHADOW:-0}" = "1" ]; then
  python3 "$SCRIPT" >> "$LOG" 2>&1
  rc=$?
  echo "RESULT=R5_SHADOW_LOCAL_ONLY rc=$rc" >> "$LOG" 2>&1
  echo "=== BotA runtime health push end ===" >> "$LOG" 2>&1
  exit 0
fi

if [ ! -f "$SECRET_FILE" ]; then
  echo "RESULT=FAIL_MISSING_SECRET_FILE" >> "$LOG" 2>&1
  echo "=== BotA runtime health push end ===" >> "$LOG" 2>&1
  exit 0
fi

# Avoid overlapping pushes if network stalls.
if [ -f "$LOCK" ]; then
  lock_age=$(( $(date +%s) - $(stat -c %Y "$LOCK" 2>/dev/null || echo 0) ))
  if [ "$lock_age" -lt 240 ]; then
    echo "RESULT=SKIP_LOCK_ACTIVE lock_age=${lock_age}s" >> "$LOG" 2>&1
    echo "=== BotA runtime health push end ===" >> "$LOG" 2>&1
    exit 0
  fi
fi

date -u '+%Y-%m-%dT%H:%M:%SZ' > "$LOCK"

set -a
. "$SECRET_FILE"
set +a

if [ -z "${BOTA_HEALTH_INGEST_SECRET:-}" ]; then
  rm -f "$LOCK"
  echo "RESULT=FAIL_SECRET_ENV_EMPTY" >> "$LOG" 2>&1
  echo "=== BotA runtime health push end ===" >> "$LOG" 2>&1
  exit 0
fi

if [ "${RUNTIME_HEALTH_PUSH_DRY_RUN:-0}" = "1" ]; then
  python3 "$SCRIPT" >> "$LOG" 2>&1
  rc=$?
  rm -f "$LOCK"
  echo "RESULT=DRY_RUN rc=$rc" >> "$LOG" 2>&1
  echo "=== BotA runtime health push end ===" >> "$LOG" 2>&1
  exit 0
fi

python3 "$SCRIPT" --send >> "$LOG" 2>&1
rc=$?

rm -f "$LOCK"

if [ "$rc" -eq 0 ]; then
  echo "RESULT=PASS rc=0" >> "$LOG" 2>&1
else
  echo "RESULT=FAIL rc=$rc" >> "$LOG" 2>&1
fi

echo "=== BotA runtime health push end ===" >> "$LOG" 2>&1
exit 0
