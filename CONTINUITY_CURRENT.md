# BotA Current Continuity State

Last updated: 2026-07-08

This file is the compact current handoff. It does not replace the historical `CONTINUITY.md`; it prevents new AI sessions from relying on stale assumptions.

## Scope lock

Reliability work only.

Do not change:

- trading strategy
- thresholds
- H1 confirmation/veto logic
- pair selection
- risk/reward logic
- ProfitLab subscription/billing/RLS
- Supabase `signals` semantics

## Verified current incident

### Incident name

BotA runtime crontab wipe / silent signal-factory stop.

### Evidence from Termux output

Before repair, live crontab contained only:

- dividend-capture-scanner block
- BotA Daily Proof block

The following BotA runtime lines were missing:

- watcher: `tools/signal_watcher_pro.sh`
- updater: `tools/indicators_updater.sh`
- shadow: `tools/run_shadow_manager.sh`
- closer: `tools/run_signal_closer_live.sh`
- supervisor: `tools/bota_supervisor.sh`
- clock drift checker: `tools/clock_drift_check.sh`

Runtime log mtimes proved the stop:

- `logs/cron.signals.log` frozen around 2026-06-22 19:30 local
- `logs/cron.indicators.log` frozen around 2026-06-22 19:28 local
- `logs/cron.closer.log` frozen around 2026-06-22 19:30 local
- `logs/api_credits.json` frozen around 2026-06-22 19:28 local

Daily Proof continued running because it was restored separately on 2026-07-05, which masked the failure by reporting `Cron: running` while the signal factory was not scheduled.

## Verified repair

### C1-SAFE-V2

- Installed runtime cron from `logs/crontab.backup.before_closer_20260603_085158.txt`.
- Aborted earlier when optional `tools/logrotate.sh` was missing.
- V2 skipped old logrotate line and restored core runtime.

### C1C cleanup

C1C removed the accidental duplicate dividend scanner line inside the BotA block and restored timezone separation.

Installed crontab passed required counts:

- dividend scanner: 1
- watcher: 1
- updater: 1
- shadow: 1
- closer: 1
- daily proof: 1
- clock drift: 1
- supervisor: 1

Tracked file changes from Termux: none.

### C2 liveness proof — PASS

Input metadata:

- `INPUT_TIMESTAMP_LOCAL=2026-07-08 14:45:51 CEST`
- `INPUT_TIMESTAMP_UTC=2026-07-08 12:45:51 UTC`
- `SOURCE=Termux`
- `SCOPE=BotA`

Verified:

- `crond` running with PID `8633`.
- Required BotA crontab line counts all equal `1`:
  - watcher
  - updater
  - shadow
  - closer
  - daily proof
  - clock drift
  - supervisor
- Fresh log/state ages:
  - `logs/cron.signals.log AGE_MIN=0`
  - `logs/cron.indicators.log AGE_MIN=2`
  - `logs/cron.closer.log AGE_MIN=0`
  - `logs/cron.shadow.log AGE_MIN=0`
  - `logs/cron.supervisor.log AGE_MIN=0`
  - `logs/api_credits.json AGE_MIN=2`
  - `state/runtime_health.json AGE_MIN=0`
- Watcher reached live scan on 2026-07-08 and rejected/no-sent due to live gates, not runtime failure.
- Updater fetched and built EURUSD, GBPUSD, and USDJPY M15/H1/H4/D1 with `fetch_fail_count=0 build_fail_count=0`.
- Closer ran live and found `0 ACTIVE` signals.
- Shadow manager ran and found `0 active signals`.
- Supervisor wrote `state/runtime_health.json` and reported `bot_mode=HEALTHY`.
- API credits moved to `used=60` for `2026-07-08`.

Known non-blocking observation:

- `logs/cron.shadow.log` still contains older network-unreachable traceback from before recovery, but current runs after restore are successful.

### Phase 2 canonical crontab — PASS

Input metadata:

- `INPUT_TIMESTAMP_LOCAL=2026-07-08 15:20:17 CEST` for commit/push.
- `INPUT_TIMESTAMP_UTC=2026-07-08 13:20:17 UTC` for commit/push.
- `INPUT_TIMESTAMP_LOCAL=2026-07-08 15:25:21 CEST` for restore drill.
- `INPUT_TIMESTAMP_UTC=2026-07-08 13:25:21 UTC` for restore drill.
- `SOURCE=Termux`
- `SCOPE=BotA`

Verified files committed and pushed:

- `docs/BOTA_CANONICAL_CRONTAB.md`
- `ops/bota_crontab.canonical`
- `tools/install_canonical_crontab.sh`
- `tools/verify_canonical_crontab.sh`

Commit:

- `e58844f ops: add canonical BotA crontab verification`

Verifier result:

- `PHASE2_VERIFY_PASS=YES`
- all required live line counts equal `1`
- `CANONICAL_HASH=b9e00a191dc5c719fd86ca981a7e78563271c6b523325aa41e289a2586104889`
- `LIVE_BOTA_BLOCK_HASH=b9e00a191dc5c719fd86ca981a7e78563271c6b523325aa41e289a2586104889`
- `BOTA_BLOCK_HASH_MATCH=YES`

Restore drill result:

- installer preserved Dividend Capture Scanner block
- installer preserved `CRON_TZ=America/New_York` for Dividend Capture Scanner
- installer installed BotA canonical block with `CRON_TZ=UTC`
- `INSTALL_RC=0`
- post-install verifier returned `PHASE2_VERIFY_PASS=YES`
- backup created at `logs/crontab.backup.before_canonical_install_20260708_132521.txt`

## Still not verified

Do not claim these are solved until evidence proves them:

- Termux:Boot installed and configured
- wake lock active
- Daily Proof upgraded to prove watcher/updater/closer/supervisor freshness
- runtime health pushed to Supabase
- ProfitLab Admin Health Panel displaying BotA health
- reboot recovery proof

## Next mandatory phase

Phase 3: Termux:Boot and wake-lock recovery.

Required:

- verify Termux:Boot package/app availability
- verify or create `~/.termux/boot/` script
- start `termux-wake-lock` during boot recovery
- start `crond` on boot
- run canonical crontab verifier or installer on boot recovery path
- write boot marker/log
- prove recovery after reboot later, when safe for the user

## Reliability conclusion

BotA's confirmed risk was silent runtime failure, not strategy weakness.

C2 proves the restored Termux runtime is alive again.

Phase 2 proves the crontab can now be verified and restored from committed source of truth.

The minimum safe architecture remains:

```text
BotA runtime
  -> supervisor
  -> runtime_health.json
  -> Supabase runtime health row
  -> ProfitLab Admin Health Panel
  -> Telegram DEGRADED/RECOVERY transition alerts
```

## ProfitLab impact

ProfitLab signal ingestion is not the immediate defect. ProfitLab correctly shows no active signals when no signals are published.

ProfitLab must add runtime-health visibility so it can distinguish:

- no signal because market/setup is quiet
- no signal because BotA is dead/offline

## Production readiness

Current reliability score: 68/100.

Reason for increase from 64:

- canonical crontab source of truth committed
- verifier committed
- installer committed
- restore drill passed
- Dividend Capture Scanner preservation confirmed
- BotA UTC timezone separation confirmed

Still below production-hardened because boot recovery, Daily Proof truth upgrade, Supabase runtime health, and ProfitLab health panel remain open.

Target after minimal reliability roadmap: 85/100.

A phone-based Termux runtime should not be scored above 90 unless an independent cloud watchdog or VPS deployment exists.
