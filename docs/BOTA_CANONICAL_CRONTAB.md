# BotA Canonical Crontab

Last updated: 2026-07-08

Purpose: prevent BotA from failing silently because of crontab wipe, duplicate cron lines, timezone leakage, or restore from stale backups.

## Source of truth

- Canonical BotA block: `ops/bota_crontab.canonical`
- Verifier: `tools/verify_canonical_crontab.sh`
- Installer: `tools/install_canonical_crontab.sh`

## Rules

- Preserve Dividend Capture Scanner block from live crontab.
- Install BotA block from `ops/bota_crontab.canonical`.
- BotA block must use `CRON_TZ=UTC`.
- Dividend scanner timezone must not leak into BotA runtime.
- Required BotA runtime lines must appear exactly once.
- Live BotA block hash must match canonical BotA block hash.
- Do not change strategy, thresholds, H1 logic, pair selection, or Supabase signal semantics.

## Required BotA cron jobs

- watcher: `tools/signal_watcher_pro.sh`
- updater: `tools/indicators_updater.sh`
- shadow: `tools/run_shadow_manager.sh`
- closer: `tools/run_signal_closer_live.sh`
- daily proof: `tools/daily_summary_server_gate.sh`
- clock drift: `tools/clock_drift_check.sh`
- supervisor: `tools/bota_supervisor.sh`

## Acceptance

PASS only if:

- `PHASE2_VERIFY_PASS=YES`
- all required counts are exactly `1`
- `BOTA_BLOCK_HASH_MATCH=YES`
- no interactive `exit` commands are used
