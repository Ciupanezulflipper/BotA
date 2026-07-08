# BotA AI Start Here

Last updated: 2026-07-08

This file exists to prevent new AI chats from guessing BotA runtime state.

## Mandatory operating rule

Before recommending code or cron changes, classify every claim as one of:

- VERIFIED: proven by GitHub file, Termux output, Supabase query, or user-provided log.
- ASSUMED: plausible but not yet proven.
- UNKNOWN: must be checked before acting.

Do not optimize trading strategy unless explicitly asked. Do not change thresholds, H1 logic, pair selection, risk logic, or Supabase signal semantics during runtime-reliability work.

## Timestamp rule for new inputs

Every major user-provided terminal/log input should be recorded with:

```text
INPUT_TIMESTAMP_LOCAL=<user/device local date time if visible>
INPUT_TIMESTAMP_UTC=<UTC date time if command output provides it, otherwise UNKNOWN>
SOURCE=<Termux|Supabase|GitHub|ProfitLab|Telegram|Lovable|Other>
SCOPE=<BotA|ProfitLab|DividendScanner|Other>
```

Reason: long ChatGPT conversations truncate. Timestamped inputs make it possible to reconstruct ordering without hallucinating. If the timestamp is not visible, mark it UNKNOWN instead of inventing it.

## Hosting spend gate

Do not recommend paid VPS/hosting as the next step until BOTH are true:

1. Reliability score is at least 60/100 and C2 liveness has passed.
2. Profitability/proof score is at least 60/100, based on verified BotA signal history and realistic ProfitLab path.

Reason: the user is already paying monthly AI subscriptions and has no income from BotA/ProfitLab yet. Reliability spend must be justified by evidence, not optimism.

## Current verified state as of 2026-07-08

BotA is a Termux Android production trading runtime that powers ProfitLab through Supabase `public.signals`.

Verified failure class:

- BotA runtime crontab was wiped/partially lost between 2026-06-22 and 2026-07-05.
- Daily Proof survived only because it was manually restored on 2026-07-05.
- Before restore, live crontab contained only:
  - dividend-capture-scanner block
  - BotA daily proof block
- Missing runtime lines were:
  - watcher
  - indicators updater
  - shadow manager
  - signal closer
  - supervisor
  - clock drift checker
- Runtime logs were frozen around 2026-06-22:
  - `logs/cron.signals.log`
  - `logs/cron.indicators.log`
  - `logs/cron.closer.log`
  - `logs/api_credits.json`

Verified restore:

- C1C cleaned and restored crontab with exactly one executable line each for:
  - dividend-capture-scanner
  - `tools/signal_watcher_pro.sh`
  - `tools/indicators_updater.sh`
  - `tools/run_shadow_manager.sh`
  - `tools/run_signal_closer_live.sh`
  - `tools/daily_summary_server_gate.sh`
  - `tools/clock_drift_check.sh`
  - `tools/bota_supervisor.sh`
- C1C did not change tracked app/code files.
- C2 liveness proof is still required before claiming restored runtime is live.

## Current production-readiness verdict

Status: PARTIALLY RESTORED, NOT PRODUCTION-HARDENED.

Production readiness score: 58/100.

Reason:

- Runtime cron was restored, but silent-failure hardening is incomplete.
- Daily Proof currently proves crond existence, not the full signal factory.
- `state/runtime_health.json` is local-only and not pushed to Supabase.
- ProfitLab has no BotA runtime health panel yet.
- Termux:Boot recovery and wake-lock behavior are not yet verified.

## Next mandatory step

Run C2 liveness after at least one updater/watcher/closer/supervisor cycle.

C2 must prove fresh mtimes and useful tails for:

- `logs/cron.signals.log`
- `logs/cron.indicators.log`
- `logs/cron.closer.log`
- `logs/cron.shadow.log`
- `logs/cron.supervisor.log`
- `logs/api_credits.json`
- `state/runtime_health.json`

Do not start implementation phases until C2 passes.

## Correct reliability direction

Minimum architecture:

```text
BotA Termux runtime
  -> tools/bota_supervisor.sh
  -> state/runtime_health.json
  -> Supabase bot_runtime_health table
  -> ProfitLab Admin Health Panel
  -> Telegram transition alerts only
```

The goal is not perfect uptime on Android. The goal is no silent failure.

## Cloud/VPS note

Moving BotA to a VPS such as Hetzner would reduce Android/ship-device failure modes: phone sleep, reboot, Termux session death, battery optimization, and mobile internet loss. It would not remove API/provider/network failure risk; it makes failures easier to monitor and recover.

Dividend Capture Scanner can run on the same small VPS if isolated by directory, env files, logs, and systemd timers/cron jobs. Do not mix secrets or schedules.

## Files to read next

- `CONTINUITY_CURRENT.md`
- `ERRORS.md`
- `docs/BOTA_RUNTIME_RELIABILITY_PATH.md`
- `docs/BOTA_PROFITLAB_HANDOFF.md`
- `BOOTLOG.md`
