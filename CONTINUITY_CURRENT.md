# BotA Current Continuity State

Last updated: 2026-07-20

This is the compact current handoff. Historical detail remains in `CONTINUITY.md`; the complete Phase 4 evidence is in `docs/RUNTIME_CHECKPOINT_2026-07-20.md` and GitHub issue #9.

## Operating rules

- Reliability work only; strategy, thresholds, pairs, scoring, SL/TP, filters, PR #7, DeepSource, and Supabase signal semantics are frozen.
- No direct push to `main`.
- Every Termux package displays `audits/ERROR_LOG.md`, prints `ERROR_LOG_REVIEWED=YES` and `CIRCULAR_ERROR_CHECK=PASS`, uses compact active-path checks, and ends with one next action.
- Mutating work must use separate staging, approval, and execution steps. No blocking interactive approval.

## Phase state

1. Single execution source and cron hygiene — COMPLETE.
2. Runtime survival controls — COMPLETE.
3. Ship-time safety proof — COMPLETE.
4. Reboot and endurance proof — IN PROGRESS.
5. Monday readiness/data collection — NOT STARTED.

Completed: 3/5. Remaining: 2/5.

## Current runtime facts

- Checkout: `/data/data/com.termux/files/home/BotA`.
- Verified boot ID: `ae204a40-c3ff-4c4e-abc2-39696b867781`.
- Service root: `$PREFIX/var/service`.
- Correct crond foreground form: `crond -n -s`.
- Ship wall time is display-only; trading and same-boot cadence use trusted UTC or monotonic time.

## Control plane

The earlier file-gated crond repair removed the detached crond and restored one supervised crond. Do not rerun that repair or its rollback.

Latest read-only snapshot:

- one standard manager, PID `4090`, PPID 1;
- all six BotA `runsv` supervisors remain under PID 1;
- `runsv crond` also remains under PID 1;
- all seven services report running;
- one live crond PID `28296`, PPID `29960`.

The manager exists but owns none of the seven services because the orphaned supervisors retain the supervise locks.

## V5 seven-service handoff

V5 was deterministically derived from the pinned V4 handoff logic. It preserves manager revalidation, idle-boundary checks, temporary down markers, orderly wrapper shutdown, orphan-supervisor exit, manager acquisition, final restart/verification, and automatic availability rollback.

V5 replaces V4's interactive approval with two mode-600, single-use, current-boot-bound approval files.

Artifacts:

- `RECONCILE_BOTA_RUNSV_V5_FILE_APPROVAL.py`
  - SHA-256: `ac67fa2b53f1d9a3034e417f5ddf940fc17cf9a09817354211d88aa9468c6e46`;
  - mode `700`.
- `ROLLBACK_RECONCILE_BOTA_RUNSV_V5.sh`
  - SHA-256: `518f8f8d2bbed4791a41821e87ea8576828a03ab43d97982c63753573566132c`;
  - mode `700`.

Validation status:

- V5 present: YES;
- rollback present: YES;
- Python syntax: PASS;
- rollback shell syntax: PASS;
- exact seven-service set: PASS;
- required handoff calls: PASS;
- required file-gated markers: PASS;
- interactive/secrets tokens: NONE;
- hard-coded UUID count: 0;
- semantic validation: PASS;
- V5 executed: NO;
- runtime mutation: NO.

The exact approval phrase and file names are pinned in the V5 source and detailed checkpoint. Approval files have not yet been created.

## RapidAPI quota mitigation

The calendar fallback leak was proven and the runtime-only key disable passed:

- one runtime declaration remains but is empty;
- `RAPIDAPI_RUNTIME_DISABLED=YES`;
- atomic edit and rollback backup verified;
- no service restart;
- no external API call by the package;
- `.env` source unchanged.

The durable watcher condition still requires a reviewed source fix with caching and call-budget controls. Twelve Data quota is separate.

## Other open findings

- canonical crontab verifier reports FAIL/hash mismatch;
- migrated core cron lines are commented and no duplicate active execution was proven;
- Telegram DEGRADED/RECOVERY messages are not authoritative alone;
- stale-reason suppression names do not match emitted reason names;
- standard-manager death root cause remains unknown.

## Ordered next steps

1. Create and verify the two current-boot V5 approval files without executing V5.
2. Execute V5 once and verify all seven supervisors are owned by the same standard manager.
3. Run bounded parentage/PID stability checks and continue the endurance gate.
4. Repair calendar invocation/caching, canonical cron verification, health truth, and Twelve Data budgeting as separate later packages.