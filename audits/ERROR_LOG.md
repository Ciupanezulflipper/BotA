# BotA Runtime Error Log

This log must be displayed before every Termux execution package.

## E001 — Scope branching
Repository work, runtime recovery, documentation, strategy, deployment, and
architecture were previously mixed in the same execution path.

Prevention: one phase and one acceptance gate per package.

## E002 — Uncontained production commit
An unpushed operational heartbeat change was committed on the production
checkout rather than being isolated first.

Prevention: verify branch and exact HEAD before mutation; no direct push to main.

## E003 — Duplicate execution sources
BotA components were represented in cron and runit while multiple daemon-start
paths remained.

Prevention: prove exactly one execution source for every component.

## E004 — Dead custom manager with orphaned supervisors
The custom BotA runsvdir died while child runsv supervisors remained under
PID 1. Heartbeat and supervisor were not recreated.

Prevention: verify manager existence and child parentage together.

## E005 — Stale Android UID cron spool
The obsolete u0_a425 cron file remained inside the current u0_a414 installation
and generated WRONG FILE OWNER every minute.

Prevention: verify current UID and preserve/quarantine stale spool state.

## E006 — Multiple executable boot starters
Several Termux:Boot files could independently start crond.

Prevention: one canonical boot script and one service-manager start path.

## E007 — Recursive scan entered runit FIFOs
Recursive grep traversed runit supervise directories and waited on named pipes.

Prevention: scan only regular files and exclude supervise directories.

## E008 — Incorrect foreground-mode assertion
The repair guard accepted only crond -f, while the installed valid service uses
the equivalent crond -n -s.

Prevention: inspect installed implementation and accept documented equivalents.

## E009 — pipefail converted a valid zero count into silent exit
With set -Eeuo pipefail, pgrep returning no matches caused
pgrep | wc -l command substitutions to abort before controlled failure handling.

Prevention: all expected-no-match counts must use:
{ pgrep ... || true; } | wc -l

## E010 — Parent manager was not revalidated before daemon migration
Child BotA runsv processes were observed, but the parent standard runsvdir was
not rechecked immediately before the detached crond was stopped.

Prevention: manager count and child parentage must pass immediately before any
daemon migration.

## AUTO-20260717T110144Z
- Phase: Phase 1
- Package: boot consolidation and final verification
- Step: final_verification
- Mutation started: YES
- Detail: CONTROLLED_FAILURE: direct daemon starter remains in active boot directory

## E012 — Dead-man stale while service tree reports running
External monitoring reported the pipeline stale for 362 minutes while runit
reported the shadow service and its supervisor as running.

Prevention: runtime health must prove fresh useful output and forward progress,
not only service or PID presence.

## E014 — Broad audit included inactive historical trees
A Phase 3 source scan included archive and backup trees, producing extensive
irrelevant output and obscuring the active runtime paths.

Prevention: future runtime audits must whitelist active files or explicitly
exclude archive, backups, logs, tests, generated state, and historical snapshots.

## E015 — Active ship-time wall-clock dependencies
Active runit cadence, watcher Telegram cooldown, shadow dead-man freshness, and
supervisor health classification depended on Android wall time.

Prevention: recurring intervals and same-boot cooldowns use monotonic elapsed
time; ship time is display-only; local dead-man freshness uses monotonic
successful progress.

## E016 — Fixed-PID endurance criterion
A healthy runit recovery was treated as failure because manager, supervisor, and
wrapper PIDs changed during the same Android boot.

Prevention: judge one-manager ownership, seven running supervisor/wrapper chains,
zero orphans, one supervised crond, API protection, and useful progress. Record
PID changes as restart events, not failures by themselves.

## E017 — Inaccessible /proc/uptime
A read-only final audit stopped with:

PermissionError: [Errno 13] Permission denied: '/proc/uptime'

Prevention: never depend on /proc/uptime on this Android build. Use
`time.monotonic()` for package-relative timing and avoid age gates when
functional state is sufficient.

## E018 — Current date/time was misinterpreted
The user stated the audit was being run after more than 12 hours, but the
workflow treated it as a fresh 22-minute sample and instructed another wait.

Prevention: reconcile explicit user date/time with the prior sample date and
prefer direct runtime evidence over conversational elapsed-time arithmetic.

## E019 — Transient crond absence escalated before recovery grace
One snapshot captured a manager-owned crond runsv without a child and immediately
classified Phase 4 as failed. A targeted follow-up proved runit had already
recreated crond without manual repair.

Prevention: when ownership remains correct and only one child is absent, take one
compact targeted recovery sample before mutation. Distinguish RECOVERING,
PERSISTENTLY_DOWN, and STRUCTURALLY_BROKEN.

## E020 — Dead-man alert contained impossible time ordering
A Telegram alert stated server UTC 2026-07-22 14:13, last shadow
2026-07-22T15:10:09+00:00, and stale duration 198 minutes. The alleged last
shadow was in the future relative to the stated server time.

Prevention: use one trusted UTC source or same-boot monotonic progress markers,
reject future/negative ages, and print the exact age inputs in diagnostics.

## E021 — Continuity lagged runtime truth
Current-state files still named manager PID 4090 and Phase 4 as pending after
later manager recovery and final Phase 4 closure evidence.

Prevention: update issue #9, detailed incident record, CONTINUITY_CURRENT.md,
ERRORS.md, AI_START_HERE.md, and this log immediately after a phase gate or
material correction.

## E022 — Oversized Phase 5 package crashed Termux
The Phase 5 baseline combined process inspection, service inspection, log-source
selection, cycle parsing, CSV parsing, cache JSON parsing, and Telegram counting
inside one very large pasted Python package. Termux crashed during execution.

Prevention: read-only packages must answer one narrow question, target roughly
80 shell lines or fewer, avoid scanning multi-megabyte logs and 1,000 CSV rows in
one process, and split infrastructure, watcher logs, CSV, and cache checks into
separate packages.

## E023 — Historical watcher log selected as current evidence
The Phase 5 baseline selected `logs/cron.signals.log` and parsed server epochs
from 2026-07-14 while current cache candles were from 2026-07-22.

Effect: current and historical evidence were mixed, producing impossible negative
cache ages and invalid current-cycle conclusions.

Prevention: identify the active watcher service output first. Require a recent
trusted-server timestamp before using any log as current evidence. Never select a
log merely because it contains the most marker strings.

## E024 — Generic pair/timeframe regex parsed log tags as symbols
The Phase 5 parser interpreted text such as `FILTER 2026` as pair/timeframe
`FILTER/2026`, so every expected EURUSD/M15 and GBPUSD/M15 cycle appeared absent.

Prevention: match only configured pairs and timeframes explicitly. Never infer a
trading symbol from a generic six-capital-letter regex over arbitrary log text.

## E025 — alerts.csv schema assumption was not validated first
The package assumed a specific current header and row alignment, then reported
`ALERTS_COLUMNS_OK=NO` and persistence `0/12`. Displayed rows had blank timestamp
and rejection fields, proving the assumption did not match the existing file.

Prevention: first print only the exact header and last three raw CSV lines. Define
schema/version handling only after direct inspection. Do not combine CSV schema
discovery with persistence reconciliation.

## E026 — Historical Telegram counters mixed into a current baseline
The Phase 5 package counted historical watcher log events such as `dedup:1683`
and `sent:16` without a current-cycle boundary.

Prevention: count only lines after a verified recent server-UTC marker or use a
bounded current service log. Historical totals may not be presented as present
runtime behavior.

## E027 — Phase 4 control-plane regression after closure
The Phase 5 baseline found one standard manager PID 12712 but only one of seven
supervisors owned by it. Six live supervisors were orphaned under PID 1 while all
seven wrappers still reported running.

Evidence:
- OWNED=1/7
- RUNNING=7/7
- WRAPPER_CHAIN=7/7
- ORPHANED=6
- crond remained live and supervised by an orphaned runsv

Prevention: stop Phase 5 data analysis whenever ownership is split. Run one
compact ownership snapshot before deeper diagnostics. Do not trust `sv status`
alone and do not rerun a broad repair without proving persistent failure.

## E028 — Split control plane automatically reconverged
A later compact snapshot on the same boot found a new standard manager PID 24052
owning all seven supervisors:

- OWNED=7/7
- RUNNING=7/7
- ORPHANED=0
- updater runsv 24057
- watcher runsv 24058
- closer runsv 24059
- shadow runsv 24060
- heartbeat runsv 24065
- supervisor runsv 24066
- crond runsv 24056

No runtime mutation, V5 rerun, or rollback was performed.

Interpretation: the 1/7 split was real but temporary, and the service manager
later converged automatically. Phase 5 may continue only while Gate A ownership
passes. Durable root cause and recovery-latency instrumentation remain open.

Prevention: record both the failure snapshot and recovery snapshot. Do not erase
the recurrence, but do not keep Phase 5 blocked after verified one-manager 7/7
reconvergence.

## Efficient package protocol

1. Functional snapshot only: boot, one manager, seven runsv PID/PPID pairs,
   seven `sv status` results, orphan count.
2. If ownership fails, stop. Do not parse logs, CSV, caches, or strategy data.
3. Inspect only the failed ownership/recovery mechanism.
4. If ownership is correct but one child is absent, take one bounded recovery
   sample before proposing mutation.
5. Mutate only for persistent failure, with backup, rollback, separate typed
   approval, and independent verification.
6. End every package with exactly one next action.
