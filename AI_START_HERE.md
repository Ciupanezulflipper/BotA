# BotA AI Start Here

Last updated: 2026-07-20

This file prevents new AI sessions from guessing BotA runtime state. Read it before proposing commands, code, cron, service, strategy, or deployment changes.

## Mandatory evidence rule

Classify every material claim as:

- VERIFIED — proven by GitHub content, Termux output, Supabase query, provider response, or user-provided logs;
- ASSUMED — plausible but not proven;
- UNKNOWN — must be checked before acting.

Do not convert a failed acceptance criterion into a pass merely because some adjacent behavior worked.

## Mandatory Termux package protocol

Every operational package must:

1. display `$HOME/BotA/audits/ERROR_LOG.md` first;
2. print `ERROR_LOG_REVIEWED=YES`;
3. print `CIRCULAR_ERROR_CHECK=PASS`;
4. use active paths only;
5. avoid recursive scans through runit supervise FIFOs;
6. avoid top-level `exit` that closes the user's Termux shell;
7. avoid interactive approval waits;
8. separate staging, approval, and mutation execution;
9. keep output compact;
10. end with exactly one next action.

Read-only packages may be one paste. Mutating work must be staged first and executed separately after exact file-gated approval.

## Scope lock

During the current reliability incident, do not change:

- strategy;
- thresholds;
- pairs;
- scoring;
- SL/TP;
- filters;
- PR #7;
- DeepSource work;
- Supabase signal semantics;
- direct pushes to `main`;
- unrelated cleanup or broad refactors.

## Current phase state

1. Single execution source and cron hygiene — COMPLETE.
2. Runtime survival controls — COMPLETE.
3. Ship-time safety proof — COMPLETE.
4. Reboot and endurance proof — IN PROGRESS.
5. Monday readiness/data collection — NOT STARTED.

Completed: 3/5.
Remaining: 2/5.

Reboot recovery passed and is closed. The open Phase 4 blocker is control-plane ownership/endurance.

## Current verified runtime state

- Termux checkout: `/data/data/com.termux/files/home/BotA`.
- Shortcut: `~/BotA`.
- Current verified boot ID: `ae204a40-c3ff-4c4e-abc2-39696b867781`.
- Canonical service root: `$PREFIX/var/service`.
- Correct crond foreground form: `crond -n -s`.
- Ship-time wall clock is not authoritative for trading decisions or same-boot freshness.

### Control plane

A fresh new-boot audit originally showed one standard manager, six orphaned BotA supervisors, and a crond split-brain.

The V2 file-gated crond repair executed and:

- accepted exact approval;
- proved preflight state;
- stopped the old detached crond;
- initially timed out bringing supervised crond up;
- automatically recovered availability;
- restored one supervised crond PID 28296.

Do not rerun the crond repair or its rollback.

Latest forensic state:

- `STANDARD_MANAGER_COUNT=0`;
- all six BotA `runsv` supervisors are under PID 1;
- `runsv crond` is also under PID 1;
- one live supervised crond exists.

Next structural objective: restore exactly one standard Termux `runsvdir` manager and migrate all seven stable supervisors beneath it without duplicate wrappers or historical replay.

## RapidAPI calendar quota incident

The Global Economic Calendar API BASIC subscription reached 100% usage.

Verified cause:

```text
bota-watcher
  -> signal_watcher_pro.sh every 900 seconds
  -> calendar_guard.py for each pair path
  -> TradingEconomics guest access
  -> RapidAPI fallback when TradingEconomics returns no events
```

The watcher source says the calendar guard is disabled, but its shell condition is logically always true whenever `calendar_guard.py` exists.

Verified supporting evidence:

- non-empty `RAPIDAPI_CALENDAR_KEY` in `.env`;
- non-empty key in `.env.runtime`;
- recent EURUSD and GBPUSD RapidAPI fallback lines in `cron.signals.log`.

This is separate from Twelve Data usage, reported at 600/800 credits.

A reversible runtime-only key disable is staged at:

`audits/p4_rapidapi_runtime_disable_ae204a40`

Pinned hashes and full evidence are in `docs/RUNTIME_CHECKPOINT_2026-07-20.md`.

Evidence boundary: the approval command was supplied by the user, but returned output has not yet proven approval-file creation or disable execution. Do not claim the key is disabled until explicit output proves it.

## Crontab and health truth

Live crontab SHA-256:

`2fbbf08b8611ae22ecfc08f9d41a078a6a3437fe1ecfcd6ba931f2f1c99b9a68`

Daily Proof reported canonical verification failure and hash mismatch.

Migrated watcher/updater/shadow/closer/heartbeat/supervisor cron entries are commented with `#MIGRATED_TO_RUNIT`; no duplicate active execution was proven from them.

Telegram DEGRADED/DEADMAN/RECOVERY transitions are not authoritative by themselves. The current supervisor still relies partly on wall-clock/file-mtime freshness, and the stale-reason suppression names do not match emitted reason names.

## Ordered next work

1. Prove the RapidAPI-disable approval file exists.
2. Execute the staged runtime-only RapidAPI disable.
3. Verify the runtime key is empty without an API request.
4. Reconcile the standard manager and seven orphaned supervisors.
5. Continue bounded endurance verification.
6. Fix calendar invocation and add cache/call-budget controls on a reviewed branch.
7. Re-run canonical crontab verification.
8. Repair health-transition truth and stale-reason suppression separately.
9. Address Twelve Data budgeting separately.

## Files to read next

- `CONTINUITY_CURRENT.md`
- `docs/RUNTIME_CHECKPOINT_2026-07-20.md`
- `ERRORS.md`
- `docs/BOTA_RUNTIME_RELIABILITY_PATH.md`
- `docs/BOTA_CANONICAL_CRONTAB.md`
- GitHub issue #9

## Hosting spend gate

Do not recommend paid hosting as the immediate answer merely to escape the current defect. First complete the current runtime evidence and establish whether BotA produces useful live-market evidence. A VPS reduces Android lifecycle risk but does not remove provider quotas, network failures, strategy risk, or observability defects.

## Core diagnostic order

When signals stop, first verify:

1. control-plane manager and supervisor parentage;
2. crond and canonical crontab integrity;
3. watcher/updater/closer/shadow useful progress;
4. provider quotas and cache freshness;
5. active signal lifecycle state;
6. network and Telegram/Supabase connectivity.

Do not first blame H1 veto, thresholds, ADX, strategy weakness, or pair selection.
