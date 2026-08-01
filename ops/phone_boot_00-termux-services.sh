#!/data/data/com.termux/files/usr/bin/bash
# Start the standard Termux runit service tree.
# BotA topology recovery guard is intentionally disabled pending validation.

set -u

PREFIX="/data/data/com.termux/files/usr"
LOG="$HOME/termux_boot_services.log"

{
  echo
  echo "===== TERMUX SERVICES BOOT $(date) ====="
  date -u '+BOOT_UTC=%Y-%m-%dT%H:%M:%SZ'

  if termux-wake-lock >/dev/null 2>&1; then
    echo "WAKE_LOCK_RESULT=PASS"
  else
    echo "WAKE_LOCK_RESULT=UNAVAILABLE_OR_FAILED"
  fi

  START_SERVICES="$PREFIX/etc/profile.d/start-services.sh"

  if [[ -f "$START_SERVICES" ]]; then
    set +u
    . "$START_SERVICES"
    set -u
    echo "START_SERVICES_RESULT=REQUESTED"
  else
    echo "START_SERVICES_RESULT=FAIL_MISSING_SCRIPT:$START_SERVICES"
    exit 1
  fi

  sleep 8

  pgrep -af "runsvdir.*$PREFIX/var/service" || true

  for name in \
    crond \
    bota-updater \
    bota-watcher \
    bota-closer \
    bota-shadow \
    bota-heartbeat \
    bota-supervisor
  do
    sv status "$PREFIX/var/service/$name" 2>&1 || true
  done

  echo "RUNSVDIR_GUARD_START=DISABLED"
  echo "===== TERMUX SERVICES BOOT COMPLETE ====="
} >>"$LOG" 2>&1
