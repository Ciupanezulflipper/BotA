#!/data/data/com.termux/files/usr/bin/bash
set -u

AUDIT_ROOT="${AUDIT_ROOT:-/data/data/com.termux/files/home/bota-worktrees/historical-replay}"
PRODUCTION_ROOT="${PRODUCTION_ROOT:-/data/data/com.termux/files/home/BotA}"
CAPTURE_ID="${CAPTURE_ID:-termux-runtime-$(date -u +%Y%m%dT%H%M%SZ)}"
OUT_ROOT="${AUDIT_ROOT}/audit/historical_replay_20260601_20260710/evidence/runtime_captures/${CAPTURE_ID}"
FILES_ROOT="${OUT_ROOT}/files"
META_ROOT="${OUT_ROOT}/metadata"

mkdir -p "${FILES_ROOT}" "${META_ROOT}"

printf '%s\n' "CAPTURE_ID=${CAPTURE_ID}"
printf '%s\n' "PRODUCTION_ROOT=${PRODUCTION_ROOT}"
printf '%s\n' "OUT_ROOT=${OUT_ROOT}"

redact_stream() {
  sed -E \
    -e 's/(Authorization:[[:space:]]*Bearer[[:space:]]+)[^[:space:]]+/\1[REDACTED]/Ig' \
    -e 's/(Bearer[[:space:]]+)[A-Za-z0-9._-]+/\1[REDACTED]/g' \
    -e 's/(TELEGRAM(_BOT)?_TOKEN[[:space:]]*=[[:space:]]*)[^[:space:]]+/\1[REDACTED]/Ig' \
    -e 's/(OANDA_API_TOKEN[[:space:]]*=[[:space:]]*)[^[:space:]]+/\1[REDACTED]/Ig' \
    -e 's/(SUPABASE_(SERVICE_)?KEY[[:space:]]*=[[:space:]]*)[^[:space:]]+/\1[REDACTED]/Ig' \
    -e 's/([0-9]{8,10}:[A-Za-z0-9_-]{30,})/[REDACTED_TELEGRAM_TOKEN]/g'
}

capture_command() {
  local name="$1"
  shift
  {
    printf 'COMMAND='
    printf '%q ' "$@"
    printf '\n'
    printf 'CAPTURED_AT_UTC=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    "$@" 2>&1
    printf 'COMMAND_RC=%s\n' "$?"
  } | redact_stream > "${META_ROOT}/${name}.txt"
}

copy_candidate() {
  local source="$1"
  local rel="$2"
  local target="${FILES_ROOT}/${rel}"
  if [ -f "$source" ]; then
    mkdir -p "$(dirname "$target")"
    redact_stream < "$source" > "$target"
    printf '%s\n' "$rel" >> "${META_ROOT}/copied_files.list"
  fi
}

: > "${META_ROOT}/copied_files.list"

capture_command git_production_head git -C "${PRODUCTION_ROOT}" rev-parse HEAD
capture_command git_production_status git -C "${PRODUCTION_ROOT}" status --short --branch
capture_command git_audit_head git -C "${AUDIT_ROOT}" rev-parse HEAD
capture_command git_audit_status git -C "${AUDIT_ROOT}" status --short --branch
capture_command crontab crontab -l
capture_command processes ps -ef
capture_command crond pgrep -af crond
capture_command termux_info termux-info
capture_command uptime uptime
capture_command date_utc date -u +%Y-%m-%dT%H:%M:%SZ
capture_command timezone getprop persist.sys.timezone

for rel in \
  logs/run.log \
  logs/cron.signals.log \
  logs/cron.watcher.log \
  logs/cron.updater.log \
  logs/cron.heartbeat.log \
  logs/cron.closer.log \
  logs/telecontroller.log \
  logs/error.log \
  logs/fusion.debug.log \
  logs/alerts.csv \
  logs/shadow_adx_scoring.jsonl \
  logs/state/deadman.flag \
  logs/state/network_fail_count.txt \
  state/pause \
  config/strategy.env \
  tools/signal_watcher_pro.sh \
  tools/indicators_updater.sh \
  tools/data_fetch_candles.sh \
  tools/m15_h1_fusion.sh \
  tools/heartbeat.sh \
  tools/run_signal_closer_live.sh
 do
  copy_candidate "${PRODUCTION_ROOT}/${rel}" "$rel"
 done

find "${PRODUCTION_ROOT}/logs" -maxdepth 2 -type f \
  \( -iname '*watcher*' -o -iname '*cron*' -o -iname '*heartbeat*' -o -iname '*boot*' -o -iname '*run*.log' \) \
  -print 2>/dev/null | sort | while IFS= read -r source; do
    rel="${source#${PRODUCTION_ROOT}/}"
    case "$rel" in
      *.gz|*.zip|*.png|*.jpg|*.jpeg) continue ;;
    esac
    copy_candidate "$source" "$rel"
  done

python3 - "${OUT_ROOT}" "${PRODUCTION_ROOT}" "${AUDIT_ROOT}" "${CAPTURE_ID}" <<'PY'
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

out_root = Path(sys.argv[1])
production_root = Path(sys.argv[2])
audit_root = Path(sys.argv[3])
capture_id = sys.argv[4]

records = []
for path in sorted(p for p in out_root.rglob('*') if p.is_file() and p.name != 'manifest.json'):
    data = path.read_bytes()
    records.append({
        'path': path.relative_to(out_root).as_posix(),
        'bytes': len(data),
        'sha256': hashlib.sha256(data).hexdigest(),
    })

manifest = {
    'schema_version': 1,
    'capture_id': capture_id,
    'captured_at_utc': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
    'production_root': str(production_root),
    'audit_root': str(audit_root),
    'network_requests_executed': False,
    'production_files_modified': False,
    'secret_files_copied': False,
    'redaction_applied': True,
    'artifact_count': len(records),
    'artifacts': records,
}
manifest_path = out_root / 'manifest.json'
manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n', encoding='utf-8')
print(f'MANIFEST_PATH={manifest_path}')
print(f'ARTIFACT_COUNT={len(records)}')
print(f'MANIFEST_SHA256={hashlib.sha256(manifest_path.read_bytes()).hexdigest()}')
PY

collector_rc=$?

printf '%s\n' "COLLECTOR_EXIT_CODE=${collector_rc}"
printf '%s\n' "NETWORK_REQUEST_EXECUTED=NO"
printf '%s\n' "PRODUCTION_FILES_MODIFIED=NO"
printf '%s\n' "SECRET_FILES_COPIED=NO"
printf '%s\n' "SHELL_WILL_REMAIN_OPEN=YES"
printf '%s\n' "CURRENT_DIRECTORY=$(pwd)"
