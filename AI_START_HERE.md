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

## Current runtime state

- Checkout: `/data/data/com.termux/files/home/BotA`.
- Verified boot ID: `ae204a40-c3ff-4c4e-abc2-39696b867781`.
- Service root: `$PREFIX/var/service`.
- Valid crond command: `crond -n -s`.
- Ship wall time is not authoritative for trading or same-boot freshness.

The earlier V2 crond repair removed the detached crond and restored one supervised crond. Do not rerun it.

Latest snapshot:

- one standard `runsvdir` manager, PID `4090`, PPID 1;
- all six BotA `runsv` supervisors remain under PID 1;
- `runsv crond` also remains under PID 1;
- all seven services report running;
- one live crond PID `28296`, PPID `29960`.

The manager exists but owns none of the services because the orphaned supervisors retain the supervise locks.

## V5 reconciliation state

V5 was derived from the pinned V4 handoff implementation and replaces only its interactive approval boundary with exact, single-use, current-boot-bound approval files.

Pinned artifacts:

- V5 SHA-256: `ac67fa2b53f1d9a3034e417f5ddf940fc17cf9a09817354211d88aa9468c6e46`;
- V5 rollback SHA-256: `518f8f8d2bbed4791a41821e87ea8576828a03ab43d97982c63753573566132c`;
- both mode `700`.

Semantic validation passed:

- exact seven-service set;
- manager revalidation and idle-boundary calls;
- manager-acquisition and final-verification calls;
- recovery rollback call;
- required file-gated markers;
- no `secrets` import, random challenge, or `input()`;
- no hard-coded boot UUID;
- V5 executed: NO;
- runtime mutation: NO.

The exact approval phrase and filenames are pinned in V5 and `docs/RUNTIME_CHECKPOINT_2026-07-20.md`. The next action is approval-file creation only, not execution.

## RapidAPI incident

The calendar guard was being called for every pair cycle and fell back to RapidAPI whenever TradingEconomics returned no events. The supposed disabled condition was logically always true when the file existed.

The runtime-only mitigation passed:

- `RAPIDAPI_CALENDAR_KEY` remains declared once in `.env.runtime` but is empty;
- `RAPIDAPI_RUNTIME_DISABLED=YES`;
- rollback backup verified;
- no service restart or external call by the package;
- `.env` source unchanged.

The durable source condition, caching, and daily call budget remain deferred. Twelve Data quota is a separate issue.

## Other open findings

- canonical crontab verification FAIL/hash mismatch;
- no duplicate active execution proven from commented migrated cron lines;
- Telegram DEGRADED/RECOVERY transitions are not authoritative alone;
- stale-reason suppression pattern does not match emitted names;
- standard-manager death root cause remains unknown.

## Ordered work

1. Create and verify V5 current-boot approval files without executing V5.
2. Execute V5 once and verify exact seven-service ownership under one manager.
3. Continue bounded endurance proof.
4. Address calendar source logic/caching, canonical cron, health truth, and Twelve Data budgeting separately.

## Files to read

- `CONTINUITY_CURRENT.md`
- `docs/RUNTIME_CHECKPOINT_2026-07-20.md`
- `ERRORS.md`
- GitHub issue #9
- draft PR #10