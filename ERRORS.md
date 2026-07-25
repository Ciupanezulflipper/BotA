# BotA Errors and Silent-Failure Register

Last updated: 2026-07-25

Purpose: record runtime failures, audit mistakes, and prevention rules that must not be rediscovered from scratch.

Historical entries remain documented in repository history, `CONTINUITY.md`, `audits/ERROR_LOG.md`, the runtime incident records, draft PR #10, and issue #9. This file prioritizes the currently relevant findings and mandatory prevention rules.

## E-001 — Closer lifecycle freeze

Status: structurally mitigated; continue monitoring.

Stale ACTIVE Supabase signals previously blocked new per-pair signals through dedup. Trusted-clock lifecycle handling and the live closer wrapper were added. Continue verifying useful progress and ACTIVE-to-final transitions.

## E-002 — Runtime crontab wipe and misleading proof

Status: previously restored; canonical ownership/hash work remains deferred.

Daily Proof survived while BotA runtime lines were absent, creating false confidence. Never use a proof job as evidence that the signal factory is scheduled. Verify intended cron/runit ownership, canonical hashes, and useful progress separately.

## E-003 — Mixed-clock stale classifications

Status: OPEN.

Wall-clock, server UTC, file mtimes, and future timestamps previously produced impossible stale arithmetic. Use provider/server UTC for market semantics, monotonic time for same-boot health, reject future/negative ages, and print exact age inputs.

## E-004 — Android/Termux control-plane fragility

Status: active runtime risk; migration implementation complete.

Android repeatedly allowed a manager to disappear or be replaced while `runsv` children survived under PID 1. `sv status` alone can look healthy even when ownership and restart authority are broken.

Prevention:

- require exactly one manager;
- verify each supervisor's actual PPID and service-directory cwd;
- verify all seven services running;
- reject duplicate or invalid supervisors;
- use one native `service-daemon` authority and one watchdog;
- treat changed PIDs as restart events, not automatic failures.

## E-005 — Provider and network degradation

Status: active.

Known risks include network/TLS interruptions, Telegram failures, Yahoo rate limiting, OANDA/cache gaps, calendar quota exhaustion, and incorrectly labelled provider accounting. Distinguish transport failures from strategy outcomes and maintain provider-specific budgets and ledgers.

## E-006 — Operational package failures

Status: process correction mandatory.

Observed failures included oversized packages, recursive scans touching runit FIFOs, zero-match pipelines failing under `pipefail`, top-level `exit` closing Termux, interactive approval loops, stale approval reuse, and repeated diagnostics based on wrong PID assumptions.

Mandatory prevention:

- display `audits/ERROR_LOG.md` first;
- print `ERROR_LOG_REVIEWED=YES` and `CIRCULAR_ERROR_CHECK=PASS`;
- preserve the parent Termux session;
- do not use interactive `set -e`;
- avoid broad process kills and recursive FIFO scans;
- use bounded active-path checks;
- stage, approve, mutate, rollback, and verify as separate gates;
- revalidate topology immediately before mutation;
- end with exactly one next action.

## E-007 — Fixed-PID endurance criterion

Status: corrected.

Healthy automatic reconstruction was previously classified as failure because exact PIDs changed. Judge functional invariants: one manager, seven owned supervisors, seven running services, zero orphans, one supervised crond, one watchdog, and useful progress.

## E-008 — `/proc/uptime` permission failure

Status: corrected.

This Android build denied `/proc/uptime`. Never depend on it. Use monotonic timing and readable targeted `/proc/<pid>` metadata only when necessary.

## E-009 — Current-date interpretation error

Status: corrected.

A stale conversational checkpoint was previously treated as current despite the user's explicit date. Reconcile explicit user time/date with runtime evidence and avoid conversational elapsed-time assumptions.

## E-010 — Documentation lag

Status: corrected through the 2026-07-25 checkpoint on the documentation branch.

Current-state files must be updated after every material runtime finding, failed deployment, root-cause correction, merged implementation, or final acceptance result.

## E-011 — Supervisor PID misidentification

Status: corrected.

Failure:

`supervise/pid` was incorrectly treated as the `runsv` supervisor PID.

Correct interpretation:

- `supervise/pid` is the supervised service process PID;
- the service process parent is the `runsv` supervisor;
- ownership must be verified from that supervisor's PPID;
- identity must also use process state, command name, and service-directory cwd.

Effect:

Earlier audits could misclassify ownership or repeatedly request diagnostics even when enough evidence was available.

Prevention:

Use the parent chain:

```text
service PID from supervise/pid -> parent runsv PID -> runsv PPID/comm/state/cwd
```

Never classify ownership from a command-line substring or `supervise/pid` alone.

## E-012 — Unsupported native-manager-plus-orphans source state

Status: fixed in GitHub; phone deployment pending.

Proven phone state:

```text
NATIVE_MANAGER_PID=18537
NATIVE_PIDFILE_VALUE=18537
OWNED=0/7
ORPHANED=7/7
INVALID=0
MISSING=0
NATIVE_WATCHDOG_COUNT=0
```

All seven supervisors were alive, correctly associated with their service directories, and parented by PID 1. The services remained running.

First migration failure:

```text
preflight_native_pidfile_present:18537
```

Root cause:

The migration accepted only:

1. one detached legacy manager owning all seven services; or
2. zero managers with exactly seven PID-1 orphan supervisors.

It did not accept one valid native manager plus exactly seven PID-1 orphans.

Safety result:

- preflight stopped before runtime mutation;
- no services were stopped;
- no processes were signalled;
- no watchdog was started;
- file rollback passed;
- the phone remained operational.

Correction:

PR #17 added source state `native_manager_orphans` and focused tests. It was merged as:

```text
PR=17
HEAD=3e827403428516ac1e8892868b70fced64ea7eab
MERGE_COMMIT=507df7e8319bded4f34d9d80f9aa9d3ec7e501fe
SECURITY_SCAN=PASS
NATIVE_SERVICE_DAEMON_WATCHDOG=PASS
```

The corrected migration:

- requires the pidfile to match the sole manager;
- requires the exact seven-orphan topology;
- does not stop or restart the existing native manager;
- skips `service-daemon start`;
- reconciles each orphan under the manager;
- verifies 7/7 ownership and running state;
- starts one watchdog only after successful reconciliation;
- remains fail-closed on mismatches, missing services, duplicates, invalid owners, existing watchdogs, or legacy guards.

## Efficient diagnostic order when signals stop

### Gate A — control plane

Verify one manager, seven manager-owned supervisors, seven running services, zero orphans, zero duplicates, one supervised crond, and one expected watchdog. If this passes, stop infrastructure diagnosis.

### Gate B — useful progress

Inspect only the failed component's current ledger/log/cache evidence. Do not combine broad historical scans with current-state diagnosis.

### Gate C — bounded recovery sample

When ownership is correct but one child is temporarily absent, take one compact recovery sample before mutation.

### Gate D — mutation

Require persistent failure, narrow cause, exact source-state proof, backup, rollback, explicit approval, bounded execution, and independent final verification.

## Current next action

Deploy merge commit `507df7e8319bded4f34d9d80f9aa9d3ec7e501fe` using a single hash-pinned package that revalidates the exact source topology immediately before mutation and accepts only the final state of one manager, 7/7 owned and running, zero orphans, zero invalid/duplicate supervisors, and one watchdog.