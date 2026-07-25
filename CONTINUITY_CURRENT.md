# BotA Current Continuity State

Last updated: 2026-07-25

This is the compact current handoff. Historical detail remains in `CONTINUITY.md`, `ERRORS.md`, `audits/ERROR_LOG.md`, the runtime incident records, draft PR #10, and issue #9.

## Operating rules

- Reliability and observability only. Strategy, thresholds, pairs, scoring, SL/TP, filters, PR #7, DeepSource, and Supabase signal semantics remain frozen.
- No direct push to `main`.
- Every Termux package must display `audits/ERROR_LOG.md`, print `ERROR_LOG_REVIEWED=YES` and `CIRCULAR_ERROR_CHECK=PASS`, preserve the parent Termux session, avoid interactive `set -e`, use active paths only, and end with exactly one next action.
- Read-only packages answer one narrow question.
- Runtime mutation requires fresh topology proof, backup, rollback, explicit approval, bounded execution, and independent verification.
- Never depend on `/proc/uptime` on this Android build.
- Trusted server/provider UTC controls market semantics; monotonic time controls same-boot cadence and health; Android/ship wall time is display-only.

## Current project phase

1. Single execution source and cron hygiene — COMPLETE.
2. Runtime survival controls — COMPLETE.
3. Ship-time safety proof — COMPLETE.
4. Native service-manager migration implementation — COMPLETE IN GITHUB.
5. Phone reconciliation and final runtime acceptance — PENDING.

Completed: **4/5**. Remaining: **1/5**.

## Proven phone topology before final deployment

The latest bounded parent-chain audit proved:

```text
NATIVE_MANAGER_COUNT=1
NATIVE_MANAGER_PID=18537
NATIVE_PIDFILE_VALUE=18537
OWNED=0/7
ORPHANED=7/7
INVALID=0
MISSING=0
NATIVE_WATCHDOG_COUNT=0
RUNTIME_MUTATION_PERFORMED=NO
```

All seven required `runsv` supervisors are alive, in state `S`, supervise the correct service directories, and have PPID 1. The seven services remain running, but none is currently owned by the native manager.

## Diagnostic corrections

Two earlier assumptions were corrected:

1. `supervise/pid` contains the service process PID, not the `runsv` supervisor PID.
2. The phone already has a valid native `service-daemon` manager; migration must not require starting a second manager.

The correct supervisor identity is obtained from the parent of the service process, then verified using PPID, process state, command name, and service-directory cwd.

## Failed migration and root cause

The first native migration attempt stopped safely before runtime mutation with:

```text
preflight_native_pidfile_present:18537
```

The implementation supported only:

- one detached legacy manager owning 7/7; or
- zero managers with exactly seven PID-1 orphans.

It did not support the observed source state:

```text
one valid native manager + seven PID-1 orphan supervisors + zero watchdogs
```

File rollback passed and the phone runtime remained unchanged.

## GitHub correction

PR #17, `fix: reconcile native manager with seven orphan supervisors`, was merged after focused tests and both required GitHub Actions workflows passed.

```text
PR=17
PR_HEAD=3e827403428516ac1e8892868b70fced64ea7eab
MERGE_COMMIT=507df7e8319bded4f34d9d80f9aa9d3ec7e501fe
SECURITY_SCAN=PASS
NATIVE_SERVICE_DAEMON_WATCHDOG=PASS
PHONE_MUTATION=NONE
```

The migration now recognizes source state `native_manager_orphans`, verifies that the pidfile matches the sole manager, requires the exact seven-orphan topology, keeps the existing manager, skips `service-daemon start`, reconciles the seven supervisors, verifies 7/7 native ownership, starts one watchdog, and performs final acceptance verification.

It remains fail-closed for pidfile mismatch, multiple managers, missing services, invalid ownership, duplicate supervisors, an existing watchdog, or an active legacy guard.

## Required final transition

Before:

```text
MANAGERS=1
OWNED=0/7
ORPHANED=7
WATCHDOGS=0
```

Required after deployment:

```text
MANAGERS=1
OWNED=7/7
RUNNING=7/7
ORPHANED=0
INVALID=0
DUPLICATES=0
WATCHDOGS=1
```

## Runtime safety boundary

No service was stopped, no process was signalled, no watchdog was started, and no phone mutation was performed while diagnosing or implementing PR #17.

## Exactly one next action

Deploy merge commit `507df7e8319bded4f34d9d80f9aa9d3ec7e501fe` using one hash-pinned, bounded Termux package that revalidates the exact source topology immediately before mutation, preserves rollback, reconciles the seven orphan supervisors under the existing native manager, and independently verifies the required final topology.