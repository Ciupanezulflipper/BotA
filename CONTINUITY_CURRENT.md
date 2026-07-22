# BotA Current Continuity State

Last updated: 2026-07-22

This is the compact current handoff. Historical detail remains in `CONTINUITY.md`, `ERRORS.md`, `audits/ERROR_LOG.md`, `docs/PHASE4_FUNCTIONAL_RECOVERY_2026-07-22.md`, `docs/PHASE5_WATCHER_ROUTING_2026-07-22.md`, `docs/PHASE4_PERSISTENT_MANAGER_LOSS_2026-07-22.md`, and issue #9.

## Operating rules

- Reliability and observability only. Strategy, thresholds, pairs, scoring, SL/TP, filters, PR #7, DeepSource, and Supabase signal semantics remain frozen.
- No direct push to `main`.
- Every Termux package displays `audits/ERROR_LOG.md`, prints `ERROR_LOG_REVIEWED=YES` and `CIRCULAR_ERROR_CHECK=PASS`, uses active paths only, and ends with exactly one next action.
- Read-only packages answer one narrow question and remain compact enough to inspect before execution.
- Never combine infrastructure, watcher-log, CSV, cache, Telegram-history, and strategy analysis in one package.
- Never depend on `/proc/uptime` on this Android build.
- Trusted server/provider UTC controls market semantics; monotonic time controls same-boot cadence and health; Android/ship wall time is display-only.
- Mutating recovery must be staged first, separately approved, then independently verified.

## Phase state

1. Single execution source and cron hygiene — COMPLETE.
2. Runtime survival controls — COMPLETE.
3. Ship-time safety proof — COMPLETE.
4. Reboot and functional recovery proof — **REOPENED BY REPEATED MANAGER LOSS**.
5. Monday readiness and decision-data collection — **BLOCKED**.

Completed: **3/5**. Remaining: **2/5**.

## Control-plane sequence

The first Phase 5 baseline captured a split:

```text
MANAGER_COUNT=1
MANAGER_PID=12712
OWNED=1/7
RUNNING=7/7
ORPHANED=6
```

A later compact snapshot proved same-boot reconvergence:

```text
MANAGER_COUNT=1
MANAGER_PID=24052
OWNED=7/7
RUNNING=7/7
ORPHANED=0
```

The next Gate A check then found the manager absent and crond down. A separate compact resample confirmed persistence:

```text
BOOT_ID=ae204a40-c3ff-4c4e-abc2-39696b867781
STANDARD_MANAGER_COUNT=0
STANDARD_MANAGER_PID=NONE
CONTROL_PLANE_RESAMPLE=MANAGER_ABSENT
OWNED=0/7
RUNNING=6/7
ORPHANED=6
MISSING_OR_DOWN=crond
```

Exact persistent state at that resample:

- updater runsv `24057`, PPID 1, running;
- watcher runsv `24058`, PPID 1, running;
- closer runsv `24059`, PPID 1, running;
- shadow runsv `24060`, PPID 1, running;
- heartbeat runsv `24065`, PPID 1, running;
- supervisor runsv `24066`, PPID 1, running;
- crond runsv absent and service down.

This sequence is tracked as:

- **E029 — standard manager disappeared after 7/7 reconvergence**;
- **E030 — manager absence persisted and crond became unavailable**.

## V5 recovery artifact preflight — PASS

The existing validated reconciliation and rollback artifacts were reverified:

```text
V5_SCRIPT_HASH_MATCH=YES
V5_ROLLBACK_HASH_MATCH=YES
V5_SCRIPT_SYNTAX=PASS
V5_ARTIFACT_PREFLIGHT=PASS
APPROVAL_FILE_CREATED=NO
V5_EXECUTED=NO
```

Pinned hashes:

- reconciliation: `ac67fa2b53f1d9a3034e417f5ddf940fc17cf9a09817354211d88aa9468c6e46`;
- rollback: `518f8f8d2bbed4791a41821e87ea8576828a03ab43d97982c63753573566132c`.

The exact typed approval was received and recorded, but approval-file creation remained a separate package.

## Approval staging safety abort — CURRENT

Before creating the two boot-bound approval files, the package revalidated the live topology. The topology had changed again:

```text
APPROVAL_STAGE_MANAGER_COUNT=1
APPROVAL_STAGE_ORPHANED=5/6
APPROVAL_STAGE_INVALID_SERVICE_ROWS=1
APPROVAL_STAGE_CROND_RUNSV_COUNT=1
APPROVAL_STAGE_CROND_STATUS=down: ... normally up, want up; run: log: ...
V5_APPROVAL_STAGE=ABORTED_STATE_CHANGED
APPROVAL_FILES_CREATED=NO
V5_EXECUTED=NO
RUNTIME_MUTATION_PERFORMED=NO
```

Interpretation:

- a standard manager and a crond runsv reappeared automatically after the prior persistent-failure sample;
- five of the six BotA supervisors were still orphaned;
- one BotA service row had changed ownership or identity, but the staging package intentionally did not identify which one;
- crond had a runsv again but its main service was still down while its log service was running;
- this is a partial automatic recovery or handoff state, not a verified healthy topology;
- the fail-closed approval gate worked correctly and prevented V5 from running against stale assumptions;
- no approval files exist and the previously typed approval has not authorized any mutation.

Do not rerun V5 or recreate approval files until one compact topology snapshot names the current manager, every service runsv PID/PPID/owner, and current crond main/log state.

This safety abort is not a new runtime error. It is evidence that the state-revalidation guard prevented an unsafe mutation.

## Watcher output routing — VERIFIED BEFORE THE REGRESSION

The watcher run script explicitly appends service evidence to:

`$HOME/BotA/logs/cron.signals.log`

Current log reading remains blocked until Gate A passes.

## Local error-log state

- GitHub continuity: through E030 plus the approval-stage safety abort;
- GitHub `audits/ERROR_LOG.md`: through E030;
- phone-local `audits/ERROR_LOG.md`: through E028;
- local error-log synchronization remains deferred and separate.

## Deferred findings

- durable cause and bounded recovery time for repeated manager replacement/orphaning;
- why Android repeatedly removes and recreates the standard manager while children survive;
- current identity of the one non-orphan BotA service during partial recovery;
- crond main-service recovery status;
- dead-man time-source and future/negative-age protection;
- stale-reason suppression mismatch;
- canonical crontab verifier/hash mismatch;
- durable calendar guard fix, caching, and call budget;
- Twelve Data budgeting;
- external independent monitoring;
- strategy review only after clean Phase 5 evidence.

## Exactly one next action

Run one compact read-only current-topology snapshot. Identify the current manager PID, all seven required runsv PID/PPID/owner states, wrapper status, and crond main/log state. Do not create approval files, execute V5, read watcher logs, or inspect CSV/caches.
