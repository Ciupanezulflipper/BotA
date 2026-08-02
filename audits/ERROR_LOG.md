# BotA Runtime Error Log

Last updated: 2026-08-02 23:31 UTC

This is the canonical compact error and prevention index. Historical full text
remains in Git history, `ERRORS.md`, incident records, and GitHub issue #9.
Current deployment evidence is in `audits/PHONE_DEPLOYMENT_2026-08-02.md`.

## Current status

```text
PRODUCTION_VALIDATION=FAILED
PHONE_PRESERVATION=PASS
FIVE_FILE_CORE_DEPLOYMENT=PASS
D1_TIMEFRAME_MAPPING=FIXED_AND_DEPLOYED
SUPERVISOR_CORE_ACCEPTANCE=PASS
STATUS_FORMATTER_ACCEPTANCE=PASS
AUTOSTATUS_ACCEPTANCE=PASS
FULL_CURRENT_CONTROL_PLANE=UNKNOWN
ACTIVE_SUPERVISOR_WRAPPER_AUTO_MUTATION=OPEN_RISK
HEARTBEAT_TOPOLOGY=OPEN_RISK
AUTOMATIC_RECOVERY_REENABLE_ALLOWED=NO
```

## Canonical error index

### E001 — Scope branching
Repository, runtime, documentation, deployment, and strategy work were mixed.
Prevention: one phase, evidence domain, and acceptance gate per package.

### E002 — Uncontained production commit
Operational work was committed on the production checkout before isolation.
Prevention: verify branch/HEAD and preserve the phone before mutation.

### E003 — Duplicate execution sources
Cron, runit, boot files, and wrappers could own the same component.
Prevention: prove one execution source for every component.

### E004 — Dead manager with orphaned supervisors
A manager died while child `runsv` processes survived under PID 1.
Prevention: verify manager, parentage, ownership, and restart capability together.

### E005 — Stale Android UID cron spool
An obsolete spool generated `WRONG FILE OWNER` warnings.
Prevention: verify UID and quarantine stale spool state.

### E006 — Multiple executable boot starters
More than one Termux:Boot file could start the same daemon.
Prevention: one canonical boot launcher and manager start path.

### E007 — Recursive scan entered runit FIFOs
A broad scan traversed `supervise` named pipes and hung.
Prevention: whitelist regular files and exclude supervise directories.

### E008 — Incorrect crond foreground assertion
A valid `crond -n -s` process was rejected because only `crond -f` was accepted.
Prevention: inspect the installed implementation and valid equivalents.

### E009 — `pipefail` converted zero matches into abort
Expected `pgrep`/`grep` zero results terminated packages.
Prevention: explicitly tolerate expected zero matches.

### E010 — Manager not revalidated before mutation
Child state was checked without immediately rechecking the manager.
Prevention: revalidate the exact source topology immediately before mutation.

### AUTO-20260717T110144Z — Boot consolidation controlled failure
A direct daemon starter remained after mutation began.
Prevention: enumerate active launchers before changing scheduler/manager state.

### E012 — Deadman stale while services appeared running
PID presence was mistaken for useful progress.
Prevention: health must prove monotonic forward progress.

### E014 — Broad audit included inactive historical trees
Archives and generated state obscured active paths.
Prevention: inspect whitelisted active files and logs only.

### E015 — Active wall-clock dependencies
Cadence and health used Android/ship wall time.
Prevention: server UTC for market semantics; monotonic time for cadence/health.

### E016 — Fixed-PID endurance criterion
Healthy restarts were treated as failure because PIDs changed.
Prevention: judge ownership, duplicates, orphans, and progress—not PID identity.

### E017 — Inaccessible `/proc/uptime`
Android denied access.
Prevention: never depend on `/proc/uptime` on this device.

### E018 — Current time misinterpreted
Conversation timing was preferred over direct timestamps.
Prevention: use explicit current evidence and exact timestamps.

### E019 — Transient crond absence escalated early
A momentary absence recovered under runit.
Prevention: distinguish recovering, persistently down, and structurally broken.

### E020 — Impossible deadman time ordering
A last-success timestamp was later than the stated server UTC.
Prevention: one trusted source; reject negative/future ages.

### E021 — Continuity lagged runtime truth
Canonical files remained stale after material changes.
Prevention: update all handoff/error/incident files and issue #9 after each gate.

### E022 — Oversized package crashed or burdened Termux
Too many evidence domains were combined.
Prevention: bounded packages and smaller direct acceptance proofs.

### E023 — Historical watcher log selected as current
Marker-rich old logs were mixed with current caches.
Prevention: identify active output and a trusted UTC boundary first.

### E024 — Generic regex parsed arbitrary tags as pair/timeframe
Prevention: match only configured pairs and timeframes.

### E025 — CSV schema assumed before inspection
Prevention: print and verify exact header/raw rows first.

### E026 — Historical Telegram counters reported as current
Prevention: count only inside a verified current-cycle boundary.

### E027 — Control-plane regression after prior closure
One manager owned only part of the service set.
Prevention: ownership Gate A before deeper diagnosis.

### E028 — Split control plane automatically reconverged
A later snapshot recovered without manual mutation.
Prevention: preserve failure and recovery evidence without erasing either.

### E029 — Manager disappeared after reconvergence
Prevention: stop deeper work and take one compact control-plane resample.

### E030 — Manager absence persisted and crond became unavailable
Prevention: do not start a second manager while orphans remain.

### E031 — `supervise/pid` misidentified as `runsv`
Prevention: service PID -> PPID -> `runsv` -> manager chain.

### E032 — Manager existed while supervisors were orphans
Prevention: manager existence and service ownership are separate gates.

### E033 — Migration rejected a real source topology
One manager plus seven PID-1 orphans was unclassified.
Prevention: enumerate every supported source topology before mutation.

### E034 — Native-manager-plus-orphans reconciliation added
One-shot repair existed but did not justify continuous recovery.
Prevention: exact topology, rollback, locking, and independent verification.

### E035 — Placeholder commits created directly on `main`
Temporary `x` files polluted history.
Prevention: create and verify a branch before file writes.

### E036 — July closure remained canonical after August regression
Prevention: later evidence supersedes readiness verdicts while retaining history.

### E037 — PR #24 scope drift
A preservation PR became a divergent multi-concern integration branch.
Prevention: salvage one behavior at a time from current `main`.

### E038 — Incident record ended inside an unfinished heredoc
Prevention: validate documentation as a standalone final artifact.

### E039 — Continuous guard associated with repeated Termux restarts
Prevention: no continuous recovery without executable-path proof, locking,
backoff, kill switch, failure injection, and restart observation.

### E040 — Broad discovery completed while D1 mismatch remained
The explicit D1 invalid state required focused reproduction, not more discovery.
Status: root cause fixed; deployed mapping now returns 1440 minutes.

### E041 — PR creation attempted before branch content existed
GitHub correctly rejected the PR because there were no commits. This recurred
once during the August 2 documentation synchronization; no PR or content mutation
resulted from the rejected call.
Prevention: branch -> file commits -> diff verification -> PR creation.

### E042 — Phone deployment completed while canonical files stayed stale
The D1 fix and five-file phone deployment passed, but handoff files still said D1
was unresolved and the phone was entirely unknown.
Prevention: synchronize canonical truth immediately after deployment acceptance.

### E043 — Active phone supervisor wrapper contradicts disabled-recovery policy
`services/bota-supervisor/run` is phone-only, absent from GitHub `main`, and can
start `runsvdir` automatically when its regex finds no match. P6 showed the
supervisor service running while a separate regex snapshot returned no match.
Effect: possible repeated manager-start attempts, duplicate manager risk, and
repository/runtime divergence.
Prevention: track service wrappers; make the supervisor scheduler non-mutating;
verify exact command/parentage instead of relying on a regex.

### E044 — Active heartbeat path bypasses repaired GitHub controller
The phone service invokes `bota_heartbeat_utc.sh`, while GitHub repairs target
`heartbeat.sh -> heartbeat_delivery.py`.
Effect: active retry backoff is not reconciled; deadman/recovery behavior exists
only in the phone wrapper.
Prevention: preserve deadman semantics while consolidating to one locked,
monotonic delivery controller.

## Current phone preservation and deployment

```text
PRESERVE_DIR=~/bota-phone-preserve-20260802T210517Z
PHONE_BRANCH=deploy/repaired-core-20260802T215531Z
PHONE_HEAD=d5c765df6fee1241be21ce892fc53e9c4bdcfb8c
UNTRACKED_FILES_PRESERVED=519
REMOTE_PUSH_PERFORMED=NO
```

Deployed and accepted:

```text
tools/supervisor_clock_status.py
tools/build_indicators.py
tools/format_status.py
tools/autostatus.sh
tools/bota_supervisor.sh
```

Protected and unchanged:

```text
tools/heartbeat.sh
tools/bota_heartbeat_utc.sh
services/bota-heartbeat/run
tools/pipeline_health.py
```

## Current efficient protocol

1. Read this file and `audits/PHONE_DEPLOYMENT_2026-08-02.md`.
2. State one narrow evidence domain and acceptance gate.
3. Preserve phone state before Git mutation.
4. Verify exact paths, commands, and parentage—not broad regex assumptions.
5. For mutation: preflight, backup, rollback, complete-file replacement,
   checksum, exact commit scope, independent verification.
6. Keep strategy, Supabase semantics, providers, Telegram, and topology changes
   separated.
7. Prefer a small direct proof over another giant copy-paste package.

## Exactly one next action

Replace the active phone-only `services/bota-supervisor/run` with a tracked,
non-mutating scheduler and verify one intended manager, seven owned/running
required services, zero orphans/duplicates, and no automatic manager creation.
Heartbeat reconciliation follows only after that gate passes.
