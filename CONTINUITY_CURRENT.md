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

## Still not verified

Do not claim these are solved until evidence proves them:

- Termux:Boot installed and configured
- wake lock active
- canonical crontab template committed and used for restore
- crontab hash/drift detection
- Daily Proof upgraded to prove watcher/updater/closer/supervisor freshness
- runtime health pushed to Supabase
- ProfitLab Admin Health Panel displaying BotA health
- reboot recovery proof

## Next mandatory phase

Phase 2: committed canonical crontab.

Required:

- canonical crontab template under version control
- verify/install script
- required line count checks
- crontab hash generation
- restore path preserving Dividend Capture Scanner block
- no interactive `exit` behavior that closes the user's Termux session during debugging

## Reliability conclusion

BotA's confirmed risk was silent runtime failure, not strategy weakness.

C2 proves the restored Termux runtime is alive again.

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

Current reliability score: 64/100.

Reason for increase from 58:

- C2 liveness passed.
- Watcher/updater/closer/shadow/supervisor/runtime_health are fresh.
- Runtime has recovered from the crontab wipe.

Still below production-hardened because boot recovery, canonical crontab, Daily Proof truth upgrade, Supabase runtime health, and ProfitLab health panel remain open.

Target after minimal reliability roadmap: 85/100.

A phone-based Termux runtime should not be scored above 90 unless an independent cloud watchdog or VPS deployment exists.
