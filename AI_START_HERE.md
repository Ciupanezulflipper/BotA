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

Verified C2 liveness:

- `INPUT_TIMESTAMP_LOCAL=2026-07-08 14:45:51 CEST`
- `INPUT_TIMESTAMP_UTC=2026-07-08 12:45:51 UTC`
- `crond` running with PID `8633`.
- Required crontab line counts all equal `1`.
- Watcher, updater, closer, shadow, supervisor, API credits, and runtime health files are fresh.
- `state/runtime_health.json` reports `bot_mode=HEALTHY`.
- API credits moved to `used=60` for `2026-07-08`.

Verified Phase 2 canonical crontab:

- Commit `e58844f ops: add canonical BotA crontab verification` added:
  - `docs/BOTA_CANONICAL_CRONTAB.md`
  - `ops/bota_crontab.canonical`
  - `tools/install_canonical_crontab.sh`
  - `tools/verify_canonical_crontab.sh`
- Restore drill timestamp: `2026-07-08 15:25:21 CEST` / `2026-07-08 13:25:21 UTC`.
- Installer preserved Dividend Capture Scanner block.
- Installer preserved `CRON_TZ=America/New_York` for Dividend Capture Scanner.
- Installer installed BotA block with `CRON_TZ=UTC`.
- `INSTALL_RC=0`.
- `PHASE2_VERIFY_PASS=YES` after installer.
- `BOTA_BLOCK_HASH_MATCH=YES`.

## Current production-readiness verdict

Status: RESTORED, PARTIALLY HARDENED, NOT PRODUCTION-HARDENED.

Reliability score: 72/100.

Reason:

- Runtime cron was restored.
- C2 liveness passed.
- Watcher/updater/closer/shadow/supervisor/runtime_health are fresh.
- Canonical crontab source of truth, verifier, and installer are committed.
- Canonical restore drill passed.
- Daily Proof truth upgrade is complete. `tools/daily_summary.sh` now reports runtime health, supervisor freshness, watcher/updater/closer/shadow ages, canonical crontab verification, hash match, and failure reasons.
- `state/runtime_health.json` is local-only and not pushed to Supabase.
- ProfitLab has no BotA runtime health panel yet.
- Termux:Boot recovery and wake-lock behavior are not yet verified.

## Next mandatory step

Phase 3: Termux:Boot and wake-lock recovery.

Required:

- verify Termux:Boot package/app availability
- verify or create `~/.termux/boot/` script
- start `termux-wake-lock` during boot recovery
- start `crond` on boot
- run canonical crontab verifier or installer on boot recovery path
- write boot marker/log
- prove recovery after reboot later, when safe for the user

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
- `docs/BOTA_CANONICAL_CRONTAB.md`
- `BOOTLOG.md`

## Phase 4C Daily Proof truth upgrade — CLOSED

VERIFIED as of 2026-07-08 15:44:34 UTC.

- Commit: `5744802` — `tools: strengthen BotA daily proof runtime reporting`
- File changed: `tools/daily_summary.sh`
- Remote push: success, no force push.
- No crontab, boot, strategy, threshold, H1, Supabase, ProfitLab, or Telegram config changes.
- Dry-run output showed:
  - `Runtime: HEALTHY`
  - supervisor freshness
  - watcher/updater/closer/shadow ages
  - `Canonical crontab: PASS`
  - `Hash match: YES`
  - `Reasons: none`
- Failure-mode tests passed for missing, corrupt, stale `runtime_health.json`, verifier missing, and cron-like environment.
- Current next open phase: Phase 5 — push local `state/runtime_health.json` into Supabase runtime health storage.

<!-- PHASE5_RUNTIME_HEALTH_PUSH_CLOSURE_20260708 -->
## Current BotA State — Phase 5 Runtime Health Push Closed

Verified on 2026-07-08:

- Supabase table `public.bot_runtime_health` exists and receives BotA runtime health updates.
- Edge Function `bot-health-ingest` is deployed and accepts only the limited health-ingest secret.
- Termux does **not** store a Supabase service-role key.
- `tools/push_runtime_health_supabase.py` builds the sanitized runtime-health payload.
- `tools/run_runtime_health_push.sh` is the cron-safe wrapper.
- Canonical crontab includes one runtime-health push job every 5 minutes.
- Live crontab and `ops/bota_crontab.canonical` hash-match.
- Cron-fire proof passed: multiple real cron pushes returned HTTP 200 and Supabase row updated.
- Latest committed Phase 5 cron state:
  - `2f8d091 tools: add BotA runtime health push wrapper`
  - `b715729 ops: add BotA runtime health push cron`

Reliability score: **78/100**.

Still not fully production-hardened:
- reboot recovery proof remains open;
- ProfitLab Admin Health panel remains open;
- profitability/proof score remains separate from runtime reliability.
