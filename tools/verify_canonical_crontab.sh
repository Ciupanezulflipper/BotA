#!/data/data/com.termux/files/usr/bin/bash
set +e

ROOT="${BOTA_ROOT:-/data/data/com.termux/files/home/BotA}"
CANON="${ROOT}/ops/bota_crontab.canonical"
TMPDIR="${ROOT}/logs/tmp"
mkdir -p "$TMPDIR"

echo "=== VERIFY CANONICAL BOTA CRONTAB ==="
echo "INPUT_TIMESTAMP_LOCAL=$(date '+%Y-%m-%d %H:%M:%S %Z' 2>/dev/null)"
echo "INPUT_TIMESTAMP_UTC=$(date -u '+%Y-%m-%d %H:%M:%S UTC' 2>/dev/null)"
echo "SOURCE=Termux"
echo "SCOPE=BotA"
echo "FILES_REPLACED=NO"
echo "CRONTAB_CHANGED=NO"
echo "TELEGRAM_SEND=NO"
echo "NO_EXIT_COMMANDS=YES"

FAIL=0
CUR="${TMPDIR}/crontab.current.verify.$$"
BLOCK="${TMPDIR}/crontab.current_bota_block.verify.$$"

crontab -l > "$CUR" 2>/dev/null
echo "CRONTAB_READ_RC=$?"

if [ -s "$CANON" ]; then
  echo "CANONICAL_FILE_OK=$CANON"
else
  echo "CANONICAL_FILE_MISSING_OR_EMPTY=$CANON"
  FAIL=1
fi

awk '
  $0 == "# BotA runtime BEGIN" {flag=1}
  flag {print}
  $0 == "# BotA runtime END" {flag=0}
' "$CUR" > "$BLOCK" 2>/dev/null

echo
echo "=== REQUIRED LIVE LINE COUNTS ==="
for pattern in \
  "dividend-capture-scanner/run_bot.sh" \
  "signal_watcher_pro.sh" \
  "indicators_updater.sh" \
  "run_shadow_manager.sh" \
  "run_signal_closer_live.sh" \
  "daily_summary_server_gate.sh" \
  "clock_drift_check.sh" \
  "bota_supervisor.sh"
do
  count="$(grep -v '^[[:space:]]*#' "$CUR" 2>/dev/null | grep -F "$pattern" | wc -l | tr -d ' ')"
  echo "$pattern COUNT=$count"
  if [ "$count" != "1" ]; then
    FAIL=1
  fi
done

echo
echo "=== HASH CHECK ==="
CANON_HASH="$(sha256sum "$CANON" 2>/dev/null | awk '{print $1}')"
LIVE_HASH="$(sha256sum "$BLOCK" 2>/dev/null | awk '{print $1}')"

[ -n "$CANON_HASH" ] || CANON_HASH="MISSING"
[ -n "$LIVE_HASH" ] || LIVE_HASH="MISSING"

echo "CANONICAL_HASH=$CANON_HASH"
echo "LIVE_BOTA_BLOCK_HASH=$LIVE_HASH"

if [ "$CANON_HASH" = "$LIVE_HASH" ] && [ "$CANON_HASH" != "MISSING" ]; then
  echo "BOTA_BLOCK_HASH_MATCH=YES"
else
  echo "BOTA_BLOCK_HASH_MATCH=NO"
  FAIL=1
fi

echo
echo "=== RESULT ==="
if [ "$FAIL" = "0" ]; then
  echo "PHASE2_VERIFY_PASS=YES"
else
  echo "PHASE2_VERIFY_PASS=NO"
fi

rm -f "$CUR" "$BLOCK"
