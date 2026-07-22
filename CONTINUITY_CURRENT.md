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
4. Reboot and functional recovery proof — **REOPENED BY PERSISTENT MANAGER LOSS**.
5. Monday readiness and decision-data collection — **BLOCKED**.

Completed: **3/5**. Remaining: **2/5**.

## Persistent control-plane failure

The first Phase 5 baseline captured a temporary split:

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

The next Gate A check found the standard manager absent and one service down. A separate compact resample confirmed the failure persisted:

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

Exact current service state at that resample:

- updater runsv `24057`, PPID 1, wrapper `24070`, running;
- watcher runsv `24058`, PPID 1, wrapper `24075`, running;
- closer runsv `24059`, PPID 1, wrapper `24071`, running;
- shadow runsv `24060`, PPID 1, wrapper `24074`, running;
- heartbeat runsv `24065`, PPID 1, wrapper `24073`, running;
- supervisor runsv `24066`, PPID 1, wrapper `24069`, running;
- crond runsv absent, stale supervise PID `24068`, service down.

Interpretation:

- this is not a transient sample or parser defect;
- the standard `runsvdir $PREFIX/var/service` manager remains absent;
- all six surviving BotA supervisors are orphaned under PID 1;
- crond has no runsv supervisor and is down;
- cron-based support jobs are unavailable;
- Phase 5 must remain blocked;
- a recovery mutation is now justified, but only after verifying the already validated V5 reconciliation artifact and its approval/rollback contract;
- do not start a new manager directly while six orphaned runsv processes remain, because that can create duplicate supervisors.

This sequence is tracked as:

- **E029 — standard manager disappeared after 7/7 reconvergence**;
- **E030 — manager absence persisted and crond became definitively unavailable**.

## Watcher output routing — VERIFIED BEFORE THE REGRESSION

Before manager loss, the watcher was manager-owned and running. Its wrapper stdout/stderr route to `/dev/null`, while the run script explicitly appends service evidence to:

`$HOME/BotA/logs/cron.signals.log`

That routing fact remains valid. Current log reading is blocked until the control plane is repaired and Gate A passes.

## Local error-log state

The phone and GitHub copies were previously synchronized through E028:

```text
LOCAL_ERROR_LOG_SYNC=PASS
LOCAL_ERROR_LOG_INDEPENDENT_VERIFY=PASS
LOCAL_ERROR_LOG_BLOB=a64143e153511bf43d19607f3521073f693ee0cc
ERROR_RANGE_PRESENT=E022_THROUGH_E028
```

Current state:

- GitHub continuity: through E030;
- GitHub `audits/ERROR_LOG.md`: through E030;
- phone-local `audits/ERROR_LOG.md`: through E028;
- local error-log synchronization remains deferred until control-plane recovery and must use a separate staged mutation.

## Rejected Phase 5 package conclusions

The oversized Phase 5 package crashed Termux and mixed historical/current evidence. Its log, CSV, cache-age, Telegram-count, and strategy conclusions remain invalid.

## Deferred findings

- durable cause and bounded recovery time for repeated manager replacement/orphaning;
- why Android repeatedly removes the standard manager while leaving children alive;
- dead-man time-source and future/negative-age protection;
- stale-reason suppression mismatch;
- canonical crontab verifier/hash mismatch;
- durable calendar guard fix, caching, and call budget;
- Twelve Data budgeting;
- external independent monitoring;
- strategy review only after clean Phase 5 evidence.

## Exactly one next action

Run one compact read-only preflight of the existing validated V5 reconciliation script and rollback artifact: verify exact paths and hashes, confirm the script is intact, and extract only its approval-file contract. Do not execute or create approval files in the same package.
