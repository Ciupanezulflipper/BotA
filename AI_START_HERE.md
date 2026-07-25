# BotA AI Start Here

Last updated: 2026-07-25

Read this before proposing BotA commands, code, cron, service, strategy, or deployment changes.

## Current scope

The active task is the final phone reconciliation to the native Termux `service-daemon` control plane. Strategy, thresholds, pairs, scoring, SL/TP, filters, PR #7, DeepSource, provider semantics, Telegram semantics, and Supabase signal semantics remain frozen.

Classify material claims as VERIFIED, ASSUMED, or UNKNOWN. Do not promote adjacent behavior into proof, and do not treat changed PIDs as failure when functional invariants pass.

## Mandatory Termux-package rules

Every package must:

1. display `$HOME/BotA/audits/ERROR_LOG.md`;
2. print `ERROR_LOG_REVIEWED=YES`;
3. print `CIRCULAR_ERROR_CHECK=PASS`;
4. preserve the parent interactive Termux session;
5. avoid interactive `set -e`, top-level `exit`, and blocking approval loops;
6. use compact active-path checks only;
7. avoid recursive scans of runit supervise trees/FIFOs;
8. separate staging, approval, mutation, rollback, and verification;
9. revalidate the exact source topology immediately before mutation;
10. end with exactly one next action.

Additional rules:

- never depend on `/proc/uptime` on this Android build;
- use provider/server UTC for market semantics and monotonic time for same-boot health;
- Android/ship wall time is display-only;
- `supervise/pid` is the service process PID, not the `runsv` supervisor PID;
- identify the supervisor from the service process parent, then verify supervisor PPID, state, command name, and service-directory cwd;
- never infer ownership from `sv status`, command-line substring matching, or `supervise/pid` alone;
- no broad kill commands;
- no phone mutation without exact preflight and rollback.

## Current phase state

1. Single execution source and cron hygiene — COMPLETE.
2. Runtime survival controls — COMPLETE.
3. Ship-time safety proof — COMPLETE.
4. Native migration implementation and tests — COMPLETE IN GITHUB.
5. Phone reconciliation and final acceptance — PENDING.

Completed: **4/5**. Remaining: **1/5**.

## Latest verified phone state

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

All seven required `runsv` supervisors are alive, in state `S`, associated with the correct service directories, and parented by PID 1. The services remain running, but the native manager currently owns none of them.

## Failed first native migration

The attempted migration stopped safely at preflight:

```text
preflight_native_pidfile_present:18537
```

No runtime mutation occurred. No service was stopped, no process was signalled, and no watchdog was started. File rollback passed.

Root cause: the migration supported only one detached legacy manager owning 7/7 or zero managers with seven PID-1 orphans. It did not support one already-running native manager plus seven PID-1 orphans.

## GitHub correction now merged

PR #17 added the exact source state `native_manager_orphans`.

```text
PR=17
HEAD=3e827403428516ac1e8892868b70fced64ea7eab
MERGE_COMMIT=507df7e8319bded4f34d9d80f9aa9d3ec7e501fe
SECURITY_SCAN=PASS
NATIVE_SERVICE_DAEMON_WATCHDOG=PASS
PHONE_MUTATION=NONE
```

For the exact verified state, the migration now:

- validates that the pidfile matches the sole native manager;
- requires exactly seven PID-1 orphan supervisors and no invalid/duplicate rows;
- keeps the existing manager alive;
- skips `service-daemon start`;
- reconciles the seven supervisors under that manager;
- verifies 7/7 ownership and running state;
- starts one watchdog only after successful reconciliation;
- verifies final health.

It remains fail-closed for mismatched pidfiles, multiple managers, missing services, invalid ownership, duplicates, existing watchdogs, or legacy guards.

## Required final acceptance

```text
MANAGERS=1
OWNED=7/7
RUNNING=7/7
ORPHANED=0
INVALID=0
DUPLICATES=0
WATCHDOGS=1
```

## Files to read

- `CONTINUITY_CURRENT.md`
- `ERRORS.md`
- `audits/ERROR_LOG.md`
- `CONTINUITY.md`
- draft PR #10
- issue #9

## Exactly one next action

Prepare and execute one bounded, hash-pinned Termux deployment package for merge commit `507df7e8319bded4f34d9d80f9aa9d3ec7e501fe`. It must revalidate the exact source topology before mutation, preserve rollback, perform reconciliation without restarting the existing native manager, and independently verify the required final acceptance state.