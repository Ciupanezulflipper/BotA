# BotA AI Start Here

Last updated: 2026-07-20

Read this before proposing BotA commands, code, cron, service, strategy, or deployment changes.

## Evidence and scope rules

Classify material claims as VERIFIED, ASSUMED, or UNKNOWN. Do not promote a failed acceptance criterion because adjacent behavior worked.

Current work is reliability-only. Do not change strategy, thresholds, pairs, scoring, SL/TP, filters, PR #7, DeepSource, Supabase signal semantics, or `main` directly.

Every Termux package must:

1. display `$HOME/BotA/audits/ERROR_LOG.md`;
2. print `ERROR_LOG_REVIEWED=YES`;
3. print `CIRCULAR_ERROR_CHECK=PASS`;
4. use compact active-path checks;
5. avoid supervise FIFOs and broad historical scans;
6. avoid top-level exits that close Termux;
7. avoid blocking interactive approval;
8. separate staging, approval, and mutation;
9. end with exactly one next action.

## Phase state

1. Single execution source and cron hygiene — COMPLETE.
2. Runtime survival controls — COMPLETE.
3. Ship-time safety proof — COMPLETE.
4. Reboot and endurance proof — IN PROGRESS.
5. Monday readiness/data collection — NOT STARTED.

Completed: 3/5. Remaining: 2/5.

Phase 4 has passed reboot recovery, crond repair, and seven-service ownership reconciliation. Only bounded endurance proof remains.

## Current verified runtime state

- Checkout: `/data/data/com.termux/files/home/BotA`.
- Boot ID: `ae204a40-c3ff-4c4e-abc2-39696b867781`.
- Service root: `$PREFIX/var/service`.
- Valid crond command: `crond -n -s`.
- Ship wall time is not authoritative for trading or same-boot freshness.

The earlier V2 crond repair removed the detached crond and restored one supervised crond. Do not rerun it.

The approved V5 control-plane handoff completed successfully.

Current ownership:

- one standard manager PID `4090`;
- updater runsv PID `26864`, PPID `4090`;
- watcher runsv PID `26917`, PPID `4090`;
- closer runsv PID `26978`, PPID `4090`;
- shadow runsv PID `27166`, PPID `4090`;
- heartbeat runsv PID `27195`, PPID `4090`;
- supervisor runsv PID `27217`, PPID `4090`;
- crond runsv PID `27331`, PPID `4090`;
- one supervised crond PID `27569`, PPID `27331`;
- all seven services running.

Three independent post-handoff samples passed. Manager and supervisor PID sets remained stable, the boot remained unchanged, and RapidAPI runtime protection remained active.

Markers:

- `V5_EXIT_CODE=0`;
- `V5_INDEPENDENT_POST_VERIFY=PASS`;
- `PHASE4_CONTROL_PLANE_HANDOFF=PASS`.

Do not rerun V5 or its rollback while the current state remains healthy.

Full result:

`docs/RUNTIME_HANDOFF_V5_RESULT_2026-07-20.md`

## RapidAPI incident

The calendar guard fallback leak remains blocked at runtime:

- `RAPIDAPI_CALENDAR_KEY` is declared once and empty in `.env.runtime`;
- future watcher cycles cannot use the RapidAPI fallback;
- the persistent `.env` source is unchanged.

The durable source condition, caching, and daily call budget remain deferred. Twelve Data quota is separate.

## Other open findings

- bounded Phase 4 endurance evidence;
- root cause of prior standard-manager death;
- canonical crontab verification FAIL/hash mismatch;
- Telegram health-transition truth;
- stale-reason suppression mismatch;
- Twelve Data budgeting;
- external independent dead-man monitoring.

## Ordered work

1. Capture a compact endurance baseline without restarting services.
2. Compare a later bounded sample for ownership, PID stability, service progress, one supervised crond, resource use, and quota protection.
3. Close Phase 4 only after stable endurance evidence.
4. Begin Phase 5 Monday-readiness checks.
5. Handle deferred source, cron, health, and quota fixes separately.

## Files to read

- `CONTINUITY_CURRENT.md`
- `docs/RUNTIME_HANDOFF_V5_RESULT_2026-07-20.md`
- `docs/RUNTIME_CHECKPOINT_2026-07-20.md`
- `ERRORS.md`
- GitHub issue #9
- draft PR #10
