# BotA Runtime Error Log

Last updated: 2026-08-02

This log must be displayed before every Termux execution package.

Historical evidence remains in Git history, `ERRORS.md`, incident records, and
issue #9. This file preserves the canonical failure IDs and prevention rules.
Unlisted numbers were never assigned.

## E001 — Scope branching

Repository work, runtime recovery, documentation, strategy, deployment, and
architecture were mixed in one execution path.

Prevention: one phase, one evidence domain, and one acceptance gate per package.

## E002 — Uncontained production commit

An operational heartbeat change was committed on the production checkout rather
than isolated first.

Prevention: verify branch and exact HEAD before mutation; never push directly to
`main`; preserve the phone worktree before Git operations.

## E003 — Duplicate execution sources

BotA components appeared in cron and runit while multiple boot/daemon paths
remained.

Prevention: prove exactly one execution source for every component.

## E004 — Dead manager with orphaned supervisors

A manager died while child `runsv` supervisors survived under PID 1. Missing
services could not be recreated.

Prevention: verify manager existence, service parentage, and restart capability
together.

## E005 — Stale Android UID cron spool

An obsolete spool file for a previous Android UID generated repeated
`WRONG FILE OWNER` warnings.

Prevention: verify current UID and preserve/quarantine stale spool state.

## E006 — Multiple executable boot starters

Several Termux:Boot files could independently start the same daemon.

Prevention: one canonical boot launcher and one manager start path.

## E007 — Recursive scan entered runit FIFOs

A recursive scan traversed `supervise` directories and waited on named pipes.

Prevention: scan regular files only and exclude runit supervise directories.

## E008 — Incorrect crond foreground assertion

A guard accepted only `crond -f`, while the installed valid service used
`crond -n -s`.

Prevention: inspect the installed implementation and accept documented
equivalents.

## E009 — `pipefail` converted a valid zero count into silent exit

`pgrep` returning no matches caused a pipeline or command substitution to abort.

Prevention: expected zero-match commands must explicitly tolerate no matches.
Strict shell options belong only inside a bounded child script.

## E010 — Parent manager not revalidated before mutation

Child supervisors were observed, but the manager was not rechecked immediately
before a daemon migration.

Prevention: revalidate exact manager count and child parentage immediately before
mutation.

## AUTO-20260717T110144Z — Boot consolidation controlled failure

A final verification found a direct daemon starter still present after mutation
had begun.

Prevention: enumerate exact active boot launchers before changing scheduler or
manager state.

## E012 — Dead-man stale while services reported running

External monitoring reported prolonged staleness while service/PID checks still
reported running.

Prevention: health must prove useful forward progress, not process presence.

## E014 — Broad audit included inactive historical trees

A source scan included archives, backups, generated state, tests, and old logs,
obscuring active paths.

Prevention: whitelist active files and logs. Read-only packages answer one narrow
question.

## E015 — Active wall-clock dependencies

Cadence, cooldown, freshness, and health depended on Android/ship wall time.

Prevention: trusted provider/server UTC controls market semantics; monotonic time
controls same-boot cadence and health; wall time is display-only.

## E016 — Fixed-PID endurance criterion

Healthy restart/recovery behavior was treated as failure solely because PIDs
changed.

Prevention: record PID changes as restart events. Judge ownership, running
chains, duplicates, orphans, supervised crond, and useful progress.

## E017 — Inaccessible `/proc/uptime`

The Android build denied access to `/proc/uptime`.

Prevention: never depend on `/proc/uptime`; use monotonic time where applicable.

## E018 — Current time was misinterpreted

Explicit user timing and previous sample timing were reconciled incorrectly,
causing an unnecessary wait/recheck.

Prevention: prefer direct timestamps and current runtime evidence over
conversational elapsed-time arithmetic.

## E019 — Transient crond absence escalated too early

One snapshot caught a child absent while ownership remained correct; runit
recreated it before a targeted resample.

Prevention: distinguish RECOVERING, PERSISTENTLY_DOWN, and
STRUCTURALLY_BROKEN with one bounded targeted recovery sample.

## E020 — Impossible time ordering in dead-man alert

An alert calculated staleness from a last-success timestamp later than its stated
server UTC.

Prevention: use one trusted time source, reject negative/future ages, and print
exact inputs.

## E021 — Continuity lagged runtime truth

Canonical handoff files remained stale after a material phase or topology change.

Prevention: update `CONTINUITY_CURRENT.md`, `AI_START_HERE.md`, `ERRORS.md`, this
log, the incident record, and issue #9 immediately after a material gate.

## E022 — Oversized package crashed Termux

One package combined process inspection, service inspection, log selection, CSV,
cache JSON, and Telegram counting.

Prevention: keep packages bounded, avoid multi-megabyte scans, and split evidence
domains.

## E023 — Historical watcher log selected as current evidence

A historical log was selected because it contained many markers, then mixed with
newer cache evidence.

Prevention: identify the active service output first and require a recent trusted
UTC boundary.

## E024 — Generic regex parsed log text as pair/timeframe

A generic capital-letter regex interpreted arbitrary log tags as trading
symbols/timeframes.

Prevention: match only configured pairs and timeframes explicitly.

## E025 — CSV schema assumed before inspection

A package parsed `alerts.csv` against an unverified schema and produced invalid
persistence conclusions.

Prevention: print the exact header and last raw rows before implementing a schema
parser.

## E026 — Historical Telegram counters used as current behavior

Unbounded historical counts were reported as present runtime behavior.

Prevention: count only inside a verified current-cycle boundary.

## E027 — Control-plane regression after prior closure

A later snapshot found one manager owning only one of seven supervisors while all
seven wrappers still appeared running.

Prevention: Gate A ownership must pass before data or strategy analysis.

## E028 — Split control plane automatically reconverged

A later snapshot found one manager owning all seven supervisors without manual
mutation.

Prevention: preserve both failure and recovery evidence. Do not erase recurrence,
but do not call a recovered topology failed solely because PIDs changed.

## E029 — Manager disappeared after reconvergence

A later Gate A check found no manager and surviving PID-1 orphan supervisors.

Prevention: stop deeper diagnostics and take one compact control-plane resample.

## E030 — Manager absence persisted and crond became unavailable

The resample confirmed no manager, six orphaned BotA supervisors, and crond down.

Prevention: do not start a second manager while orphans remain. Use only a
validated, approval-gated reconciliation with rollback.

## E031 — `supervise/pid` misidentified as `runsv`

Ownership audits treated the service PID file as the supervisor PID.

Prevention: resolve service PID -> PPID -> `runsv` and validate PPID, cwd, state,
and command.

## E032 — Manager existed while all supervisors were orphans

A valid manager/pidfile existed, but all seven `runsv` supervisors remained under
PID 1.

Prevention: manager existence and service ownership are separate gates.

## E033 — Migration rejected a real unsupported topology

A fail-closed migration accepted only two source states and rejected the verified
third state: one valid manager plus seven PID-1 orphan supervisors.

Prevention: preflight must explicitly classify every supported source topology
and reject all others before process mutation.

## E034 — Native-manager-plus-orphans reconciliation added

PR #17 added a reconciliation path for one manager plus seven orphans and merged
as `507df7e8319bded4f34d9d80f9aa9d3ec7e501fe`.

Prevention: deployment still requires exact source topology, bounded execution,
rollback, and independent verification.

## E035 — Placeholder commits created directly on `main`

Three temporary placeholder files containing only `x` were created and deleted
directly on `main` while attempting to establish a branch.

Effect: no phone/runtime state changed, but repository history was polluted and
the no-direct-main rule was violated.

Prevention: create and verify the branch before any file write. Never probe branch
creation with placeholder files.

## E036 — July closure remained canonical after August regression

The July 26 handoff continued to state that migration/watchdog work was closed
after the August 1 validation proved later control-plane, recovery, scheduling,
and repository regressions.

Prevention: later verified evidence supersedes earlier production-readiness
verdicts while preserving historical timestamps.

## E037 — PR #24 scope drift and divergent integration branch

PR #24 described a three-file preservation change but expanded to seven commits
and thirty-two changed files across unrelated runtime, provider, documentation,
notification, and test concerns. It diverged heavily from current `main` and
became non-mergeable.

Prevention: preservation branches are historical artifacts, not integration
branches. Reapply one behavior at a time from current `main`; close contaminated
PRs as superseded.

## E038 — Incident record ended inside an unfinished heredoc

The first August 1 incident file ended with a literal
`cat >"$INCIDENT_FILE" <<'EOF'` inside an unclosed code block and omitted the
incident conclusion and acceptance failures.

Prevention: validate documentation as a complete standalone file before commit.
Do not paste shell-construction scaffolding into the final artifact.

## E039 — Continuous guard associated with repeated Termux restarts

The configured native service-daemon path was unavailable. A continuous
`runsvdir` guard was started, and repeated Termux restarts occurred while it was
active. The guard and watchdog were stopped; automatic recovery was disabled.

Interpretation: rollback was required. The exact restart mechanism remains
unproven.

Prevention: no continuous recovery loop without executable-path verification,
locking, bounded cadence, backoff, kill switch, failure-injection tests, and
Termux restart observation.

## E040 — Broad data discovery completed but explicit D1 mismatch remained

The August 2 discovery ended with:

```text
LOCAL_STATUS_DATA_DISCOVERY_COMPLETE=YES
RUNTIME_MUTATION_PERFORMED=NO
GIT_CHANGED=NO
```

The evidence still showed `cache/indicators_EURUSD_D1.json` with
`error=tf_mismatch`, `tf_ok=false`, `tf_actual_min=0.0`, and zero indicators.

Prevention: do not repeat broad discovery. Reproduce one pair/timeframe through
the exact provider fetch, cache writer, and indicator builder.

## E041 — PR creation attempted before repair branch existed

During the August 2 repository-truth repair, PR creation was attempted before the
new repair branch existed. GitHub rejected each attempt with validation errors;
no PR, file, branch, or runtime mutation resulted.

Prevention: operation order is branch creation -> branch verification -> complete
file writes -> diff verification -> PR creation.

## Current efficient package protocol

1. Display this file.
2. State the single evidence domain and acceptance gate.
3. For phone Git work, preserve and classify every local modification first.
4. For runtime work, run one compact ownership/control-plane snapshot only when
   current evidence is necessary.
5. Stop if control-plane ownership fails; do not inspect strategy or mixed data.
6. For data work, reproduce one pair/timeframe through exact provider, cache, and
   indicator paths.
7. For mutation, revalidate targets, back up, define rollback, mutate narrowly,
   and verify independently.
8. End with exactly one next action.

## Current next action

From current `main`, create one focused code-repair branch that reproduces and
fixes the EURUSD D1 `tf_mismatch`. Do not touch strategy, automatic recovery,
Telegram, Supabase signal semantics, or the production phone checkout in the
same package.