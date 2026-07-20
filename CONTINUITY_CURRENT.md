# BotA Current Continuity State

Last updated: 2026-07-20

This is the compact current handoff. Historical detail remains in `CONTINUITY.md`; full evidence for this checkpoint is in `docs/RUNTIME_CHECKPOINT_2026-07-20.md` and GitHub issue #9.

## Mandatory operating mode

- Work one phase and one acceptance gate at a time.
- Display `audits/ERROR_LOG.md` before every Termux package.
- Print `ERROR_LOG_REVIEWED=YES` and `CIRCULAR_ERROR_CHECK=PASS`.
- Use compact, active-path-only checks.
- Do not use top-level `exit` that closes the user's Termux shell.
- Do not use interactive approval waits.
- Separate staging, approval, and mutation execution.
- End with exactly one next action.

## Scope lock

Do not change during runtime-reliability work:

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

## Five-phase state

1. Single execution source and cron hygiene — COMPLETE.
2. Runtime survival controls — COMPLETE.
3. Ship-time safety proof — COMPLETE.
4. Reboot and endurance proof — IN PROGRESS.
5. Monday readiness/data collection — NOT STARTED.

Completed: 3/5.
Remaining: 2/5.

Phase 4 details:

- reboot gate: PASS and closed;
- endurance/control-plane ownership: FAIL and unresolved.

## Current device/runtime facts

- Termux checkout: `/data/data/com.termux/files/home/BotA`.
- Shortcut: `~/BotA`.
- Current verified boot ID: `ae204a40-c3ff-4c4e-abc2-39696b867781`.
- Canonical service root: `$PREFIX/var/service`.
- Valid crond foreground form: `crond -n -s`.
- Ship-time wall clock is display-only; trading and same-boot cadence use trusted server UTC or monotonic time.

## Current control-plane state

### What the new-boot audit proved

The first fresh snapshot showed:

- one standard `runsvdir` manager, PID 25793;
- six BotA `runsv` supervisors orphaned under PID 1;
- manager-owned `runsv crond` unable to start a supervised daemon;
- one old detached `crond -n -s` under PID 1;
- stable runsv PID sets across samples.

### Crond repair result

The file-gated V2 repair did execute and consumed its approval file.

Verified log evidence:

- approval accepted;
- preflight passed with manager 25793, runsv 29960, old crond 29386;
- old crond reached an idle boundary and exited after SIGTERM;
- first `sv -w 30 up crond` timed out with rc 111;
- automatic availability recovery succeeded;
- supervised crond PID 28296 came up.

Do not rerun the crond split-brain repair or its rollback.

### Remaining structural blocker

The latest forensic snapshot showed:

- `STANDARD_MANAGER_COUNT=0`;
- all six BotA `runsv` supervisors under PID 1;
- `runsv crond` also under PID 1;
- one live supervised crond PID 28296.

The next structural task is to restore exactly one standard Termux `runsvdir` manager and migrate all seven stable supervisors beneath it without duplicate wrappers, historical replay, or service-state corruption.

## RapidAPI calendar quota incident

The Global Economic Calendar API BASIC subscription reached 100% usage.

This is separate from Twelve Data, which Telegram reported at 600/800 credits.

Verified active caller chain:

```text
bota-watcher runit service
  -> tools/signal_watcher_pro.sh every 900 seconds
  -> tools/calendar_guard.py for each pair path
  -> TradingEconomics guest access
  -> RapidAPI fallback whenever TradingEconomics returns no events
```

The watcher comment says the calendar guard is disabled, but the condition is always true when the file exists because of its second `|| [[ -f ... ]]` clause.

Proof:

- `.env` contains a non-empty `RAPIDAPI_CALENDAR_KEY`;
- `.env.runtime` contains a non-empty key;
- recent logs show RapidAPI fallback for EURUSD and GBPUSD;
- the active caller is runit, not a direct cron line.

### Staged runtime-only mitigation

Stage directory:

`audits/p4_rapidapi_runtime_disable_ae204a40`

Pinned artifacts:

- disable script SHA-256: `29fa5f954a1c4db3438753712d49dc355293c1991099bda713a090203fd67dbb`;
- rollback script SHA-256: `c4d3efbc90c92dc3866fd0ce8d95052ba34f2f75f6f41f74ebe61237fc0d0bb5`;
- expected `.env.runtime` SHA-256: `794b160586e670d08e6a2c9dd0756b57c08b0f7e719005f1d15918df8ac79f48`;
- expected mode: `600`.

Planned effect:

- blank only `RAPIDAPI_CALENDAR_KEY` in `.env.runtime`;
- preserve `.env`;
- create a mode-600 backup;
- replace atomically;
- make no API call;
- restart no service.

Evidence boundary:

The user supplied the approval-file creation command, but returned output has not yet proven approval-file creation or disable execution. Do not claim RapidAPI runtime use is disabled until explicit output proves it.

## Crontab state

Live crontab SHA-256:

`2fbbf08b8611ae22ecfc08f9d41a078a6a3437fe1ecfcd6ba931f2f1c99b9a68`

Daily Proof reported canonical verification failure and hash mismatch.

Observed structure:

- migrated watcher/updater/shadow/closer/heartbeat/supervisor cron lines are commented with `#MIGRATED_TO_RUNIT`;
- no duplicate active execution was proven from those lines;
- Daily Proof remains active;
- runtime-health push remains active every five minutes;
- dividend scanner remains active and separate.

Do not blindly reinstall canonical cron until intended runit/cron ownership is reconciled.

## Health and Telegram truth

Telegram showed alternating DEGRADED, DEADMAN, and RECOVERY transitions.

These are not sufficient proof of runtime health because the current supervisor still relies partly on wall-clock/file-mtime freshness. Quiet successful cycles can look stale, and restart log touches can look like recovery.

Deferred suppression defect:

- emitted reasons use names such as `watcher_stale`, `updater_stale`, and `shadow_stale`;
- the suppression regex expects names such as `watcher_log_stale`;
- intended suppression is ineffective.

## Ordered next steps

1. Prove the RapidAPI-disable approval file exists.
2. Execute the already-staged runtime-only RapidAPI disable.
3. Verify the runtime key is empty without making an API request.
4. Reconcile the missing standard manager and all seven orphaned supervisors.
5. Run bounded parentage/PID stability checks and continue the endurance gate.
6. Fix calendar invocation logic and add cache/call-budget controls on a reviewed branch.
7. Re-run canonical crontab verification.
8. Repair health-transition truth and stale-reason suppression separately.
9. Address Twelve Data call budgeting separately.

## Deferred findings

- root cause of repeated standard-manager death;
- seven-service manager reconciliation;
- calendar caching and daily call budget;
- calendar 429/quota observability;
- canonical crontab mismatch;
- monotonic useful-progress health model;
- stale-reason suppression mismatch;
- Twelve Data quota budgeting;
- external independent dead-man monitor.
