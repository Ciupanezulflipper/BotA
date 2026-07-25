# BotA Errors and Silent-Failure Register

Last updated: 2026-07-25

Purpose: record runtime failures, audit mistakes, and prevention rules that must not be rediscovered from scratch.

## Current highest-priority incident

Verified phone state:

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

All seven services are alive, but all seven `runsv` supervisors are parented by PID 1 rather than the native manager.

The first migration stopped safely with:

```text
preflight_native_pidfile_present:18537
```

Root cause: the implementation supported one detached manager owning 7/7 or zero managers with seven orphans, but not one existing native manager plus seven orphans.

PR #17 added source state `native_manager_orphans`, passed Security Scan and Native service-daemon watchdog CI, and merged as:

```text
507df7e8319bded4f34d9d80f9aa9d3ec7e501fe
```

No phone mutation occurred during diagnosis, patching, CI, or merge.

## Critical diagnostic correction

`supervise/pid` identifies the supervised service process. It is not the `runsv` supervisor PID.

Correct ownership chain:

```text
supervise/pid service PID
-> service PPID
-> runsv supervisor PID
-> supervisor PPID and cwd
```

Every future ownership audit must validate supervisor command, state, PPID, and cwd together.

## Current prevention and deployment rule

The next package must:

- display `audits/ERROR_LOG.md`, current through E034;
- be pinned to merge commit `507df7e8319bded4f34d9d80f9aa9d3ec7e501fe`;
- run as a bounded child process so failure cannot close the parent Termux session;
- revalidate the exact source topology immediately before mutation;
- stop without signalling services if the source topology differs;
- preserve rollback;
- independently verify one manager, 7/7 owned and running, zero orphans, zero invalid/duplicates, and one watchdog.

## Historical error classes still applicable

### Runtime ownership and scheduler integrity

- stale or wiped crontab can leave Daily Proof alive while the signal factory is unscheduled;
- `sv status` alone cannot prove healthy ownership or restart capability;
- Android can replace a manager while child supervisors survive;
- detached crond and runit crond can create split-brain behavior;
- ownership must be proven through manager, supervisor, wrapper, and service parentage.

### Health and time semantics

- service presence is not useful progress;
- future or negative stale ages must be rejected;
- use trusted provider/server UTC for market semantics;
- use monotonic time for same-boot health and cadence;
- never depend on `/proc/uptime` on this Android build;
- PID changes are restart events, not failures by themselves.

### Provider and observability risks

- provider quotas must be tracked per provider rather than by generic successful fetches;
- RapidAPI calendar fallback must remain disabled until its source condition, caching, and budget are corrected;
- Telegram, Supabase, network, provider, and runtime failures must be distinguished;
- quiet/no-signal behavior must not be reported as infrastructure death.

### Operational package failures

- broad scans can enter runit FIFOs or mix active and historical evidence;
- expected zero-match commands must not be allowed to abort under `pipefail`;
- top-level `exit` can close the Termux session;
- oversized pasted scripts can crash Termux;
- read-only packages must answer one narrow question;
- mutation requires fresh topology validation, backup, rollback, explicit approval, and independent verification.

## Efficient diagnostic order when signals stop

### Gate A — control plane

Verify:

1. exactly one intended manager;
2. seven manager-owned supervisors;
3. seven running service/wrapper chains;
4. zero orphaned supervisors;
5. one supervised crond;
6. no duplicates or invalid rows;
7. the intended watchdog state.

If Gate A fails, stop. Do not inspect strategy, watcher decisions, CSV, caches, or Telegram history.

### Gate B — targeted runtime path

After Gate A passes, inspect only the failing component or evidence path.

### Gate C — bounded recovery sample

When ownership is correct but one child is briefly absent, allow one compact recovery resample before mutation.

### Gate D — mutation

Require a persistent failure, narrow cause, exact expected source topology, backup, rollback, explicit approval, and independent post-change verification.