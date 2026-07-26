# BotA Errors and Silent-Failure Register

Last updated: 2026-07-26

Purpose: record runtime failures, audit mistakes, and prevention rules that must not be rediscovered from scratch.

## Current highest-priority incident: closed

The native service-manager migration and watchdog finalization are complete.

Final verified phone state:

```text
MANAGER_COUNT=1
MANAGER_PID=22175
PIDFILE_VALUE=22175
OWNED=7/7
RUNNING=7/7
ORPHANED=0
INVALID=0
DUPLICATES=0
DOWN_SERVICES=NONE
WATCHDOG_COUNT=1
WATCHDOG_PID=8752
WATCHDOG_LOCK_HOLDERS=8752
BOOT_LEGACY_COUNT=0
BOOT_WATCHDOG_COUNT=1
ACTIVE_MIGRATION_JOURNAL=ABSENT
CONTROL_PLANE_GATE=PASS
STABILITY_CHECK=PASS
```

A later read-only check after normal service cycles confirmed the same healthy topology without mutation.

## Migration lessons preserved

- `supervise/pid` identifies the supervised service process, not the `runsv` supervisor.
- Correct ownership proof is service PID -> service PPID -> `runsv` supervisor -> supervisor PPID/cwd/state/command.
- Android may kill the Termux process during runtime mutation; migration steps must be journaled, resumable, bounded, and fail-closed.
- A transient split control plane may reconverge automatically. Record both failure and recovery evidence.
- The partial migration executor must not be used for an already fully owned native tree.
- A fully owned native manager with no watchdog must use the dedicated finalizer, which changes only approved files/boot launcher and starts one watchdog.
- `set -Eeuo pipefail` belongs only in a child script, never directly in the interactive Termux shell.
- Printed `MUTATION_STARTED=YES` must follow the first actual mutation, not merely preflight completion.

## Repository milestones

```text
PR #18 MERGED=ef94e4fd1c9a7a786f7514024828fbdfc1146143
PR #19 MERGED=12000f04137a000cb3d1c6bf7acb45da288907c9
PR #20 MERGED=87e43ce76d43d625e7e9c7a6715cabb59f4b65c9
PR #21 MERGED=09a1bd5b57e0bf3a39e79afc827d14e09e8b1031
PR #22 MERGED=0694e17c09c3c8663622dce745d8b449c3cd2405
```

PR #22 added the persistent migration journal and recovery gate. During deployment, the partial executor correctly rejected `OWNED=7/7; ORPHANED=0` and performed file rollback. The dedicated fully-owned finalizer then completed successfully.

## Current operational caution

The phone checkout remains on operational branch `ops/ship-time-independent-runtime-20260717`, HEAD `c9ab9996190025ab51202b1f6508a05f8fc148c3`, with a dirty worktree. Do not reset or overwrite it without first preserving and classifying all local changes.

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
- quiet/no-signal behavior must not be reported as infrastructure death;
- a rejected HOLD with complete current evidence is normal strategy behavior, not a missed signal by itself.

### Operational package failures

- broad scans can enter runit FIFOs or mix active and historical evidence;
- expected zero-match commands must not abort under `pipefail`;
- top-level `exit` can close the Termux session;
- oversized pasted scripts can crash Termux;
- read-only packages must answer one narrow question;
- mutation requires fresh topology validation, backup, rollback, explicit approval, and independent verification.

## Efficient diagnostic order when signals stop

### Gate A — control plane

Verify exactly one intended manager, seven owned/running supervisors, zero orphans/invalid/duplicates, one supervised crond, one watchdog holding its lock, correct boot launcher, and no active migration journal.

If Gate A fails, stop. Do not inspect strategy, watcher decisions, CSV, caches, or Telegram history.

### Gate B — current updater/watcher progress

After Gate A passes, prove fresh data and one current watcher cycle using active logs only.

### Gate C — decision integrity

Classify the cycle as valid HOLD/rejection, eligible signal, send failure, persistence failure, or infrastructure failure. Confirm the full decision record exists before dedup.

### Gate D — lifecycle proof

When the next signal becomes ACTIVE, verify Telegram/Supabase creation, closer execution, and correct CLOSED/CANCELLED transition with result pips.

### Gate E — mutation

Require persistent failure, narrow cause, exact expected source topology, backup, rollback, explicit approval, and independent post-change verification. Do not change strategy merely because no signal is emitted.