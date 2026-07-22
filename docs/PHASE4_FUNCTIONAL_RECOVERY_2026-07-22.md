# BotA Phase 4 Functional Recovery Closure — 2026-07-22

## Status

Phase 4 — reboot and endurance/recovery proof: **COMPLETE**.

Completed phases: **4/5**.
Remaining phase: **1/5** — Monday-readiness and decision-data collection.

This record supersedes the earlier fixed-PID endurance interpretation. The accepted reliability criterion is functional recovery under one control plane, not indefinite preservation of a specific process ID.

## Final verified runtime state

Boot ID remained unchanged:

`ae204a40-c3ff-4c4e-abc2-39696b867781`

Final functional closure result:

`PHASE4_FUNCTIONAL_RECOVERY=PASS`

Verified invariants:

- exactly one standard Termux `runsvdir` manager;
- manager PID `31330`, PPID 1 at the final sample;
- all seven `runsv` supervisors owned by that manager;
- all seven services running;
- all seven supervised wrapper chains valid;
- zero orphaned supervisors;
- zero `down` markers;
- exactly one live `crond -n -s`;
- live crond supervised by the manager-owned crond `runsv`;
- `RAPIDAPI_CALENDAR_KEY` declared once and empty in `.env.runtime`;
- no V5 rerun required;
- no rollback required;
- no runtime mutation was performed by the closure audits.

Final summary marker:

```text
PHASE4_FUNCTIONAL_RECOVERY=PASS MANAGER_COUNT=1 MANAGER_PID=31330 OWNED=7/7 RUNNING=7/7 WRAPPER_CHAIN=7/7 ORPHANED=0 DOWN_MARKERS=0 LIVE_CROND_COUNT=1 CROND_SUPERVISED=YES RAPIDAPI_DISABLED=YES
```

## Recovery sequence

The same Android boot experienced more than one standard-manager replacement:

1. V5 ownership handoff initially passed under manager PID `4090`.
2. A later healthy sample showed manager PID `20630`, with all seven services reconstructed correctly.
3. The final audit found manager PID `31330`, again on the same boot.
4. During one snapshot, the manager-owned crond `runsv` existed but had no live crond child, producing a temporary `6/7` result.
5. A targeted follow-up proved runit automatically recreated crond without manual repair.

Targeted recovery evidence:

- standard manager PID `31330`;
- crond `runsv` PID `24619`, PPID `31330`;
- live crond PID `13521`, PPID `24619`;
- command `crond -n -s`;
- `sv status crond` returned `run`;
- `sv status crond/log` returned `run`;
- crond log service PID `23874` remained active;
- active spool file `u0_a414`, mode `600`, UID `10414`;
- no stale UID spool reappeared;
- no manual restart, V5 rerun, or rollback occurred.

Classification:

`TARGETED_CROND_AUDIT=CROND_RECOVERED_DURING_AUDIT`

## Correct acceptance model

Phase 4 does **not** require stable PIDs for 12 hours. PID replacement is expected when Android terminates and Termux/runit recreates processes.

Phase 4 requires these functional invariants:

1. one standard manager;
2. one supervisor per required service;
3. every supervisor owned by the manager, not PID 1;
4. every service wrapper running beneath its supervisor;
5. one supervised foreground crond;
6. no duplicate control plane;
7. no `down` markers;
8. protected API state preserved;
9. useful pipeline progress resumes after a transient process loss.

A transient child restart is an availability event to observe, not an automatic structural failure. Escalation is required only when recovery does not complete within a bounded grace period or when duplicate/orphan ownership appears.

## New error and finding register

### 1. Fixed-PID endurance criterion was invalid

The audit treated a changed manager, supervisor, or wrapper PID as a failure even when runit had recreated a correct and healthy service tree.

Correction: compare functional ownership and liveness invariants. Record PID changes as restart events, not failures by themselves.

### 2. `/proc/uptime` was inaccessible

A read-only package attempted to read `/proc/uptime` and failed with:

`PermissionError: [Errno 13] Permission denied: '/proc/uptime'`

Correction: never depend on `/proc/uptime` on this Android build. Use `time.monotonic()` for package-relative evidence and `/proc/<pid>/stat` only for process start metadata when readable.

### 3. User-provided current date/time was misinterpreted

The workflow incorrectly scheduled another wait after the user stated that the sample was already being run more than 12 hours later.

Correction: reconcile explicit user date/time with the prior sample date before issuing a waiting instruction. Prefer direct current monotonic/runtime evidence over conversational arithmetic.

### 4. Temporary crond absence was escalated before recovery grace

One snapshot captured a manager-owned crond supervisor with no child and classified Phase 4 as failed. The next targeted audit showed crond had already recovered automatically.

Correction: for runit-managed services, perform one compact targeted resample after a short bounded grace interval before proposing mutation. Do not rerun the full control-plane repair when ownership remains correct.

### 5. Dead-man alert contained impossible time ordering

Telegram reported:

- server UTC `2026-07-22 14:13`;
- last shadow `2026-07-22T15:10:09+00:00`;
- claimed stale duration `198min`.

The alleged last-shadow timestamp was approximately 57 minutes in the future relative to the stated server UTC, so the stale duration is not trustworthy.

A later recovery alert reported last shadow `2026-07-22T15:25:12+00:00`, proving progress resumed but not validating the earlier stale arithmetic.

Correction: health alerts must use one trusted UTC source or same-boot monotonic progress markers. Reject negative/future age calculations and include the computed age inputs in diagnostics.

### 6. Documentation lagged runtime truth

Continuity still described manager PID `4090` and Phase 4 as pending after later recovery evidence existed.

Correction: update issue, continuity, error register, and AI handoff immediately after every phase gate or material correction.

## Pattern audit

Repeated inefficiency came from four patterns:

1. **Implementation-detail gates instead of outcome gates** — exact PIDs and long waits replaced functional recovery checks.
2. **Full-package repetition** — broad seven-service audits were reused when only crond had failed.
3. **Mutation bias** — temporary unavailability was close to triggering another repair even though runit ownership was correct and automatic recovery was active.
4. **Mixed time domains** — ship wall time, server UTC, file timestamps, conversation timestamps, and monotonic time were compared without an explicit trust hierarchy.

## Efficient operating protocol from Phase 5 onward

### Gate A — one-line functional snapshot

Check only:

- manager count;
- seven manager-owned supervisors;
- seven running wrappers;
- orphan count;
- one supervised crond;
- API protection;
- useful-progress markers.

If all pass, stop. Do not run deeper diagnostics.

### Gate B — targeted diagnostic only

When one invariant fails, inspect only that service or data path. Do not rescan archives, backups, unrelated services, strategy, or GitHub history.

### Gate C — bounded recovery resample

When ownership is correct but a child is absent, allow one short bounded recovery sample. Classify:

- recovered automatically;
- persistently unavailable;
- duplicate/orphaned control plane.

Only the second or third condition may proceed to a staged repair.

### Gate D — mutation

Mutation requires:

- persistent failure;
- exact cause or narrowly bounded hypothesis;
- backup and rollback;
- staged file only;
- separate typed approval;
- independent post-verification.

### Time hierarchy

1. trusted server/provider UTC for market semantics;
2. same-boot monotonic time for cadence, cooldowns, and local health;
3. Android/ship wall time for display only;
4. file mtime only as secondary evidence.

## Phase 5 handoff

Do not lower thresholds or manufacture signals.

The next objective is to prove that every scheduled market cycle produces one of two auditable outcomes:

1. a complete gate-by-gate decision recorded in `logs/alerts.csv`; or
2. an explicit pre-fusion skip reason in active runtime logs.

This will distinguish a valid quiet market from a broken scan path or an over-restrictive strategy.

Deferred work remains separate:

- root cause of repeated standard-manager replacement;
- dead-man time-source and stale-duration correction;
- calendar guard source-condition fix and caching;
- canonical crontab mismatch;
- Twelve Data call budgeting;
- external independent dead-man monitoring;
- strategy and threshold review only after clean decision-data collection.
