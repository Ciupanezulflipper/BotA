# BotA Heartbeat Production Deployment and Live Validation — Closure Evidence

<!-- BOTA_HEARTBEAT_PRODUCTION_DEPLOYMENT_LIVE_VALIDATION_2026_07_12 -->

**Date:** 2026-07-12  
**Branch:** `fix/heartbeat-observability-20260712`  
**Closure commit:** `22cd624b49d803dd126ce1ec412d8e8b24d6463e`  
**Status:** RESOLVED

---

## 1. Scope

This document records the production deployment and live validation of BotA heartbeat v3.2,
building on the implementation proven in `6cdfc7f97090b4bfae9ba0b015940205778d9ed6`.

Changes approved and executed:
1. Synthetic migration rehearsal (20 cases)
2. Production credential migration
3. Production crontab remediation
4. Production heartbeat file deployment
5. Live Telegram validation (one controlled invocation)
6. Operator confirmation
7. Documentation and state closure

No strategy, H1 veto, ADX gates, thresholds, pair scope, cron cadence, Supabase, or OANDA
changes were made.

---

## 2. Synthetic Rehearsal

- [proven] 20 migration test cases run against embedded utility, covering: empty value, quoted
  value, unquoted value, existing key (dedup), dest-already-has-key, mode enforcement, backup
  round-trip, and edge cases.
- [proven] All 20 cases PASS, 62 assertions, 0 failures.
- [proven] Cron redirect rehearsal: `{ synthetic_stderr >&2; bash heartbeat.sh; } >/dev/null 2>> log`
  pattern verified — stdout discarded, stderr captured, HEARTBEAT_RESULT count=1 in log (no double-write).
- [proven] Temp utility self-deleted after rehearsal.

---

## 3. Credential Migration

- [proven] Source: `BotA/.env` (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
- [proven] Destination: `BotA/.env.runtime`
- [proven] Pre-migration state: TOKEN=0, CHAT=0
- [proven] Post-migration state: TOKEN=1, CHAT=1, mode=600
- [proven] Unrelated content preserved unchanged
- [proven] Backup: `BotA/backups/.env.runtime.bak.mig.20260712_222524`
- [proven] Dedup enforced — keys not duplicated if already present
- [proven] No secret values exposed in logs or stdout
- [proven] Migration utility self-deleted after run

---

## 4. Crontab Remediation

- [proven] Old line: `0 * * * * bash .../heartbeat.sh >> .../cron.heartbeat.log 2>&1`
- [proven] New line: `0 * * * * bash .../heartbeat.sh >/dev/null 2>> .../cron.heartbeat.log`
- [proven] Reason: old `2>&1` caused `result()` markers to be written twice — once via `log()` direct
  file write and once via cron stdout capture. New redirect discards stdout; only direct file writes land
  in log.
- [proven] Backup: `BotA/backups/crontab.bak.20260712_223713`
- [proven] Transformation via Python exact-line match (not sed — avoids `&` backreference bug)
- [proven] Exactly one line changed; diff confirmed
- [proven] Crontab remediation utility self-deleted after run

---

## 5. Production Heartbeat Deployment

- [proven] Source: `bota-worktrees/heartbeat-observability/tools/heartbeat.sh`
- [proven] Destination: `BotA/tools/heartbeat.sh`
- [proven] Source SHA-256: `8226a935c30be8a3484ed20bf3e79192d9fb020f6dc827e4e89af3c23a2fe202`
- [proven] Pre-deployment production SHA-256: `2f31839368f533fe1dc2a61764fe0ce2695ed8491c71120f482f6a375f7789b3`
- [proven] Post-deployment production SHA-256: `8226a935c30be8a3484ed20bf3e79192d9fb020f6dc827e4e89af3c23a2fe202`
- [proven] Mode: 700 (before and after)
- [proven] Backup: `BotA/backups/heartbeat.sh.before_v32_20260712_224441` (SHA `2f31839...`, mode 700)
- [proven] Atomic deployment: `mktemp` in same directory + `chmod 700` + `mv` (POSIX atomic rename)
- [proven] No other production files changed during deployment step (verified via `find -newer sentinel`)
- [proven] Offline test suite re-run on production file: 29 cases, 108 assertions, 108 PASS, 0 FAIL

---

## 6. Live Telegram Validation

### Pre-conditions verified
- [proven] Production SHA-256 matched expected `8226a935...`
- [proven] `.env.runtime` TOKEN=1, CHAT=1, mode=600
- [proven] Cron entry used `>/dev/null 2>> log` redirect
- [proven] No deadman.flag present before test

### Cron-fired invocation (automatic)
- [proven] Log entry: `[2026-07-12 21:00:02 UTC] HEARTBEAT_RESULT=PASS`
- [proven] Log entry: `[2026-07-12 21:00:02 UTC] DEADMAN_RESULT=HEALTHY`
- [proven] Shadow file updated by this cron cycle (last line epoch ~8 min before manual test)

### Manual invocation
- [proven] Command: `bash tools/heartbeat.sh`
- [proven] HEARTBEAT_RESULT=PASS (stdout)
- [proven] DEADMAN_RESULT=HEALTHY (stdout)
- [proven] Log entry: `[2026-07-12 21:08:08 UTC] HEARTBEAT_RESULT=PASS`
- [proven] Log entry: `[2026-07-12 21:08:08 UTC] DEADMAN_RESULT=HEALTHY`
- [proven] Secret leak check: PASS — no token or chat_id values in stdout, stderr, or new log content
- [proven] No unexpected file changes (deadman.flag absent before and after; only log file modified)

### Operator confirmation
- [proven] Operator visually confirmed receipt of Telegram heartbeat message at `2026-07-12 21:00:00 UTC`
- [proven] Operator visually confirmed receipt of Telegram heartbeat message at `2026-07-12 21:08:07 UTC`
- `TELEGRAM_RECEIPT_CONFIRMED_BY_OPERATOR=YES`

---

## 7. Open Items

- [not proven] Whether any valid signal was missed during the historical June 2026 outage
- [not proven] Clock drift monitoring — not yet implemented; `CLOCK_JITTER_TOLERANCE_SEC=300` is
  a passive gate only

---

## 8. Integrity Hashes

| File | SHA-256 |
|------|---------|
| `BotA/tools/heartbeat.sh` (deployed) | `8226a935c30be8a3484ed20bf3e79192d9fb020f6dc827e4e89af3c23a2fe202` |
| `bota-worktrees/.../tools/heartbeat.sh` (source) | `8226a935c30be8a3484ed20bf3e79192d9fb020f6dc827e4e89af3c23a2fe202` |
| `BotA/tools/heartbeat.sh` (pre-deploy backup) | `2f31839368f533fe1dc2a61764fe0ce2695ed8491c71120f482f6a375f7789b3` |
| `tests/test_heartbeat.sh` | `cad581f326ef5b4fbf7c1f26065cb43de3abc70cf9b4a573d7ff5bc4647e81c1` |
