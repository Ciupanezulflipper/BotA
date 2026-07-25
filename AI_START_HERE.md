# BotA AI Start Here

Last updated: 2026-07-25

Read this before proposing BotA commands, code, cron, service, strategy, or deployment changes.

## Evidence and scope rules

Classify material claims as VERIFIED, ASSUMED, or UNKNOWN. Do not promote a failed acceptance criterion because adjacent behavior worked, and do not fail a healthy recovery because process IDs changed.

Current work is native service-manager reconciliation only. Do not change strategy, thresholds, pairs, scoring, SL/TP, filters, PR #7, DeepSource, Supabase signal semantics, or `main` directly.

Every Termux package must:

1. display `$HOME/BotA/audits/ERROR_LOG.md`;
2. print `ERROR_LOG_REVIEWED=YES`;
3. print `CIRCULAR_ERROR_CHECK=PASS`;
4. use compact active-path checks;
5. avoid supervise FIFOs and broad historical scans;
6. avoid top-level exits that close Termux;
7. avoid blocking interactive approval;
8. separate staging, approval, mutation, rollback, and verification;
9. end with exactly one next action.

Additional mandatory rules:

- do not use `/proc/uptime` on this Android build;
- changed PIDs are restart events, not failures by themselves;
- use trusted server/provider UTC for market semantics;
- use monotonic time for same-boot cadence and health;
- Android/ship wall time is display-only;
- read-only packages must answer one narrow question and remain compact enough to inspect visually;
- never combine infrastructure, watcher logs, CSV, cache JSON, Telegram history, and strategy conclusions in one Termux package;
- `supervise/pid` identifies the supervised service process, not the `runsv` supervisor;
- resolve ownership through service PID -> PPID -> runsv, then validate command, state, PPID, and cwd;
- revalidate the full source topology immediately before any runtime mutation.

## Current verified control plane

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

All seven required `runsv` supervisors are alive under PID 1. The native manager exists but owns none of them.

## Failed migration

The first native migration stopped safely with:

```text
preflight_native_pidfile_present:18537
```

The implementation did not support one existing native manager plus seven PID-1 orphan supervisors. The abort happened before process mutation. No services were stopped, no supervisors were signalled, and no watchdog was started.

## Corrected implementation

PR #17 added source state `native_manager_orphans` and merged as:

```text
507df7e8319bded4f34d9d80f9aa9d3ec7e501fe
```

Verified CI:

```text
Security Scan: PASS
Native service-daemon watchdog: PASS
```

The migration now preserves the existing native manager, skips `service-daemon start`, reconciles the exact seven orphan supervisors, verifies ownership, and starts the watchdog only after successful reconciliation.

## Error-log state

`audits/ERROR_LOG.md` is current through E034. It records the supervisor-PID diagnostic mistake, the exact native-manager/seven-orphan topology, the fail-closed migration error, and the PR #17 correction.

## Required deployment acceptance

The next runtime package must be pinned to merge commit `507df7e8319bded4f34d9d80f9aa9d3ec7e501fe` and must independently prove:

```text
MANAGER_COUNT=1
OWNED=7/7
RUNNING=7/7
ORPHANED=0
INVALID=0
DUPLICATES=0
WATCHDOG_COUNT=1
```

Failure to match the expected source topology before mutation must stop the package without signalling services.

## Files to read

- `CONTINUITY_CURRENT.md`
- `audits/ERROR_LOG.md`
- `ERRORS.md`
- GitHub PR #17
- GitHub issue #9
- documentation PR #10

## Exactly one next action

Merge the documentation checkpoint after all checks pass, then run one bounded hash-pinned Termux deployment package. Do not inspect Phase 5 data or strategy in that package.