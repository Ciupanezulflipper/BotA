# BotA Current Continuity State

Last updated: 2026-07-22

This is the compact current handoff. Historical detail remains in `CONTINUITY.md`, `ERRORS.md`, `audits/ERROR_LOG.md`, the Phase 4/5 incident records, and issue #9.

## Operating rules

- Reliability and observability only. Strategy, thresholds, pairs, scoring, SL/TP, filters, PR #7, DeepSource, and Supabase signal semantics remain frozen.
- No direct push to `main`.
- Every Termux package displays `audits/ERROR_LOG.md`, prints `ERROR_LOG_REVIEWED=YES` and `CIRCULAR_ERROR_CHECK=PASS`, uses active paths only, and ends with exactly one next action.
- Read-only packages answer one narrow question.
- Mutating recovery requires staging, fresh explicit approval, execution, rollback availability, and independent verification.
- Never depend on `/proc/uptime` on this Android build.
- Trusted server/provider UTC controls market semantics; monotonic time controls same-boot cadence and health; Android/ship wall time is display-only.

## Phase state

1. Single execution source and cron hygiene — COMPLETE.
2. Runtime survival controls — COMPLETE.
3. Ship-time safety proof — COMPLETE.
4. Reboot and functional recovery proof — **REOPENED BY REPEATED MANAGER LOSS**.
5. Monday readiness and decision-data collection — **BLOCKED**.

Completed: **3/5**. Remaining: **2/5**.

## Control-plane sequence

The runtime moved through these same-boot states:

1. split: manager `12712`, owned `1/7`, running `7/7`, orphans `6`;
2. automatic reconvergence: manager `24052`, owned `7/7`, running `7/7`, orphans `0`;
3. manager absent: owned `0/7`, running `6/7`, orphans `6`, crond down;
4. partial automatic recovery: a new manager appeared before V5 approval staging, causing the fail-closed staging guard to abort safely.

This sequence is tracked as:

- **E029 — standard manager disappeared after 7/7 reconvergence**;
- **E030 — manager absence persisted and crond became unavailable**.

## V5 artifact state

The existing validated reconciliation and rollback artifacts remain intact:

```text
V5_SCRIPT_HASH_MATCH=YES
V5_ROLLBACK_HASH_MATCH=YES
V5_SCRIPT_SYNTAX=PASS
V5_ARTIFACT_PREFLIGHT=PASS
```

Pinned hashes:

- reconciliation: `ac67fa2b53f1d9a3034e417f5ddf940fc17cf9a09817354211d88aa9468c6e46`;
- rollback: `518f8f8d2bbed4791a41821e87ea8576828a03ab43d97982c63753573566132c`.

A typed V5 approval was received, but it became stale when the topology changed. Approval-file staging aborted with no files created and no execution. The approval must not be reused.

## Exact current topology — latest snapshot

```text
BOOT_ID=ae204a40-c3ff-4c4e-abc2-39696b867781
STANDARD_MANAGER_COUNT=1
STANDARD_MANAGER_PID=25759
CURRENT_TOPOLOGY=SPLIT_CONTROL_PLANE
OWNED=2/7
RUNNING=6/7
WRAPPERS_ALIVE=6/7
ORPHANED=5
V5_APPROVAL_FILES_PRESENT=0/2
V5_EXECUTED=NO
RUNTIME_MUTATION_PERFORMED=NO
```

Service ownership:

- `bota-updater`: runsv `6595`, PPID `25759`, manager-owned, wrapper `6601`, running;
- `bota-watcher`: runsv `24058`, PPID 1, orphan, wrapper `24075`, running;
- `bota-closer`: runsv `24059`, PPID 1, orphan, wrapper `24071`, running;
- `bota-shadow`: runsv `24060`, PPID 1, orphan, wrapper `24074`, running;
- `bota-heartbeat`: runsv `24065`, PPID 1, orphan, wrapper `24073`, running;
- `bota-supervisor`: runsv `24066`, PPID 1, orphan, wrapper `24069`, running;
- `crond`: runsv `25763`, PPID `25759`, manager-owned, main service reported down, no current wrapper PID in `supervise/pid`.

Crond detail:

```text
CROND_LOG_STATUS=run
LIVE_CROND_COUNT=1
LIVE_CROND_PIDS=24068
```

Interpretation:

- this is a confirmed split control plane, not a transient parser result;
- only updater and crond runsv are owned by the current manager;
- five BotA runsv supervisors remain orphaned under PID 1;
- one live `crond -n -s` process exists as PID `24068`, while the current manager-owned crond service still reports down;
- the live crond parentage and the V5 script's acceptance of this exact split state must be checked before any new approval staging;
- do not create approval files or execute V5 until that compatibility check passes;
- Phase 5 log, CSV, cache, Telegram, and strategy analysis remains blocked.

## Watcher output routing

The watcher run script explicitly appends service evidence to:

`$HOME/BotA/logs/cron.signals.log`

Current log reading remains blocked until Gate A passes.

## Local error-log state

- GitHub continuity: through E030 and the exact current split topology;
- GitHub `audits/ERROR_LOG.md`: through E030;
- phone-local `audits/ERROR_LOG.md`: through E028;
- local E029–E030 synchronization remains deferred and separate.

## Deferred findings

- durable cause and bounded recovery time for repeated manager replacement/orphaning;
- why Android repeatedly removes and recreates the standard manager while children survive;
- parentage and provenance of live crond PID `24068`;
- dead-man time-source and future/negative-age protection;
- stale-reason suppression mismatch;
- canonical crontab verifier/hash mismatch;
- durable calendar guard fix, caching, and call budget;
- Twelve Data budgeting;
- external independent monitoring;
- strategy review only after clean Phase 5 evidence.

## Exactly one next action

Run one compact read-only V5 compatibility audit against the exact current split topology. Inspect only the reconciliation script's preflight/decision logic and live crond PID `24068` parentage. Do not create approval files, execute V5, or inspect Phase 5 data.
