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

## Verified repair so far

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

## Not yet verified

Do not claim these are working until logs prove it:

- watcher liveness after restore
- updater liveness after restore
- closer liveness after restore
- shadow manager liveness after restore
- supervisor liveness after restore
- `api_credits.json` movement after restore
- `state/runtime_health.json` current status
- Termux:Boot installed and configured
- wake lock active
- canonical crontab restore after reboot

## Next mandatory proof

C2 liveness check after at least one runtime cycle.

Must check:

- `logs/cron.signals.log`
- `logs/cron.indicators.log`
- `logs/cron.closer.log`
- `logs/cron.shadow.log`
- `logs/cron.supervisor.log`
- `logs/cron.daily.log`
- `logs/api_credits.json`
- `state/runtime_health.json`
- required crontab line counts still equal 1

If C2 fails, do not proceed to implementation. Diagnose the failed component first.

## Reliability conclusion

BotA's confirmed risk is silent runtime failure, not strategy weakness.

The minimum safe architecture is:

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

Current score: 58/100.

Target after minimal reliability roadmap: 85/100.

A phone-based Termux runtime should not be scored above 90 unless an independent cloud watchdog or VPS deployment exists.
