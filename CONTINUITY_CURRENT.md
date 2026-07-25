# BotA Current Continuity State

Last updated: 2026-07-25

This is the compact current handoff. Historical detail remains in `CONTINUITY.md`, `ERRORS.md`, `audits/ERROR_LOG.md`, the Phase 4/5 incident records, and issue #9.

## Operating rules

- Reliability and observability only. Strategy, thresholds, pairs, scoring, SL/TP, filters, PR #7, DeepSource, and Supabase signal semantics remain frozen.
- No direct push to `main`.
- Every Termux package displays `audits/ERROR_LOG.md`, prints `ERROR_LOG_REVIEWED=YES` and `CIRCULAR_ERROR_CHECK=PASS`, uses active paths only, and ends with exactly one next action.
- Read-only packages answer one narrow question.
- Mutating recovery requires staging, fresh explicit approval, execution, rollback availability, and independent verification.
- Never depend on `/proc/uptime` on this Android build.
- Trusted server/provider UTC controls market semantics; monotonic time controls same-boot cadence and health; Android/ship wall time is display-only.

## Current verified runtime topology

The corrected parent-chain audit proved the following exact state:

```text
NATIVE_MANAGER_COUNT=1
NATIVE_MANAGER_PID=18537
NATIVE_PIDFILE_MATCH=YES
OWNED=0/7
ORPHANED=7/7
INVALID=0
MISSING=0
NATIVE_WATCHDOG_COUNT=0
RUNTIME_MUTATION_PERFORMED=NO
```

Each service's `supervise/pid` identifies the supervised service process, not the `runsv` supervisor. The actual supervisor was resolved through the service process PPID, then validated by command, state, PPID, and cwd. All seven required `runsv` supervisors are alive under PID 1.

## Failed migration and root cause

The first native migration stopped safely with:

```text
preflight_native_pidfile_present:18537
```

The implementation supported only:

1. one detached manager owning all seven services; or
2. zero managers with exactly seven PID-1 orphan supervisors.

It did not support the verified third state: one valid native manager plus seven PID-1 orphan supervisors. The failure occurred before runtime mutation. No services were stopped, no supervisors were signalled, no watchdog was started, and file rollback remained available.

## GitHub correction

PR #17 added source state `native_manager_orphans` and merged successfully.

```text
PR_HEAD=3e827403428516ac1e8892868b70fced64ea7eab
MERGE_COMMIT=507df7e8319bded4f34d9d80f9aa9d3ec7e501fe
SECURITY_SCAN=PASS
NATIVE_SERVICE_DAEMON_WATCHDOG_CI=PASS
PHONE_MUTATION=NONE
```

The corrected migration now requires the manager to match the native pidfile, requires exactly seven unique PID-1 orphan supervisors, skips `service-daemon start`, preserves the existing native manager, reconciles the seven supervisors, verifies ownership, and only then starts the watchdog.

## Error-log checkpoint

`audits/ERROR_LOG.md` is current through E034 and records:

- E031 — `supervise/pid` was misidentified as the supervisor PID;
- E032 — native manager present with seven PID-1 orphan supervisors;
- E033 — migration rejected the real but unsupported source topology;
- E034 — PR #17 added the safe reconciliation path.

## Remaining runtime step

Deploy exact merge commit:

```text
507df7e8319bded4f34d9d80f9aa9d3ec7e501fe
```

The deployment must run as one bounded child script, display the current error log, revalidate the source topology immediately before mutation, preserve rollback, and independently verify:

```text
MANAGER_COUNT=1
OWNED=7/7
RUNNING=7/7
ORPHANED=0
INVALID=0
DUPLICATES=0
WATCHDOG_COUNT=1
```

## Exactly one next action

After this documentation checkpoint is merged, execute one hash-pinned Termux deployment package for merge commit `507df7e8319bded4f34d9d80f9aa9d3ec7e501fe`. Do not inspect strategy or Phase 5 data in that package.