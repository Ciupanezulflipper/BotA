# BotA Runtime Error Log

Last updated: 2026-08-03 00:07 UTC

This is the canonical compact error and prevention index. Historical full text
remains in Git history, `ERRORS.md`, incident records, and GitHub issue #9.
Current evidence is in:

- `audits/PHONE_DEPLOYMENT_2026-08-02.md`
- `audits/P7_SUPERVISOR_WRAPPER_CLOSURE_2026-08-02.md`

## Current status

```text
PRODUCTION_VALIDATION=FAILED_HISTORICAL
PHONE_PRESERVATION=PASS
CORE_DEPLOYMENT=PASS
D1_TIMEFRAME_MAPPING=FIXED_AND_DEPLOYED
SUPERVISOR_CORE_ACCEPTANCE=PASS
SUPERVISOR_WRAPPER_ACCEPTANCE=PASS
CURRENT_CONTROL_PLANE=HEALTHY_7_OF_7
STATUS_FORMATTER_ACCEPTANCE=PASS
AUTOSTATUS_ACCEPTANCE=PASS
ACTIVE_SUPERVISOR_WRAPPER_AUTO_MUTATION=CLOSED
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

### E007 — Recursive scan entered runit FIFOs
A broad scan traversed `supervise` named pipes and hung.
Prevention: whitelist regular files and exclude supervise directories.

### E009 — `pipefail` converted zero matches into abort
Expected `pgrep`/`grep` zero results terminated packages.
Prevention: explicitly tolerate expected zero matches.

### E012 — Deadman stale while services appeared running
PID presence was mistaken for useful progress.
Prevention: health must prove monotonic forward progress.

### E015 — Active wall-clock dependencies
Cadence and health used Android/ship wall time.
Prevention: server UTC for market semantics; monotonic time for cadence/health.

### E017 — Inaccessible `/proc/uptime`
Android denied access.
Prevention: never depend on `/proc/uptime` on this device.

### E020 — Impossible deadman time ordering
A last-success timestamp was later than stated server UTC.
Prevention: one trusted source; reject negative/future ages.

### E021 — Continuity lagged runtime truth
Canonical files remained stale after material changes.
Prevention: update handoff/error/deployment records and issue #9 after each gate.

### E022 — Oversized package burdened Termux
Too many evidence domains were combined.
Prevention: bounded packages and smaller direct acceptance proofs.

### E027 — Control-plane regression after prior closure
One manager owned only part of the service set.
Prevention: ownership gate before deeper diagnosis.

### E031 — `supervise/pid` misidentified as `runsv`
Prevention: service PID -> PPID -> `runsv` -> manager chain.

### E032 — Manager existed while supervisors were orphans
Prevention: manager existence and service ownership are separate gates.

### E035 — Placeholder commits created directly on `main`
Prevention: branch -> content -> diff verification -> PR.

### E037 — PR #24 scope drift
A preservation PR became a divergent multi-concern branch.
Prevention: salvage one behavior at a time from current `main`.

### E039 — Continuous guard associated with repeated Termux restarts
Prevention: no continuous recovery without executable-path proof, locking,
backoff, kill switch, failure injection, and restart observation.

### E040 — D1 mismatch survived broad discovery
Status: closed. `tf_minutes("D1")` now returns 1440 on the phone.
Live D1 cache regeneration remains to be recorded later.

### E041 — PR creation attempted before branch content existed
Prevention: create branch, write content, verify diff, then open the PR.

### E042 — Phone deployment completed while canonical files stayed stale
Prevention: synchronize canonical truth immediately after acceptance.

### E043 — Supervisor wrapper contradicted disabled-recovery policy
Previous condition: the phone wrapper could start `runsvdir` when its process
regex found no match, and the active and repository wrapper paths were separate.

Status: **CLOSED by P7**.

Verified closure:

```text
ACTIVE_WRAPPER_UPDATED=YES
REPOSITORY_WRAPPER_UPDATED=YES
ACTIVE_EQUALS_REPOSITORY=YES
SUPERVISOR_WRAPPER_MUTATION_DISABLED=YES
manager_count=1
required=7
owned=7
running=7
orphaned=0
duplicate_service_rows=0
healthy=true
```

Prevention: track and test service wrappers, identify the exact active path, and
keep manager recovery out of scheduler wrappers.

### E044 — Active heartbeat path bypasses repaired GitHub controller
Status: **OPEN**.

The phone service invokes `bota_heartbeat_utc.sh`, while GitHub repairs target
`heartbeat.sh -> heartbeat_delivery.py`.

Effect: the active path has UTC bucketing and deadman/recovery behavior but does
not yet use the repaired controller's one lock and bounded monotonic retry
backoff.

Prevention: preserve UTC/deadman/recovery semantics while consolidating to one
active delivery controller and separate persisted delivery outcomes.

### E045 — Strict shell mode left active in interactive Termux
A direct `set -euo pipefail` in the parent shell caused Termux to exit after an
expected failed assertion.

Prevention: always begin interactive recovery packages with `set +e`, `set +u`,
and `set +o pipefail`, then execute strict mode only inside a bounded child
`bash` process.

### E046 — Active service path assumed to be a repository symlink
The active runit directory under `~/.config/bota-sv` was a separate physical
copy, not a link to `~/BotA/services`.

Prevention: compare `realpath`, mode, and checksum for active and repository
copies before deployment; update both when the architecture intentionally uses
separate copies.

## Current phone state

```text
PRESERVE_DIR=~/bota-phone-preserve-20260802T210517Z
PHONE_BRANCH=deploy/repaired-core-20260802T215531Z
PHONE_HEAD=dbdb1b1f9e2e1a6d66bb94b8eda4d1cf40617d20
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
services/bota-supervisor/run
```

Protected and unchanged through P7:

```text
tools/heartbeat.sh
tools/bota_heartbeat_utc.sh
services/bota-heartbeat/run
tools/pipeline_health.py
```

## Efficient protocol

1. Keep strict mode inside a child shell, never the interactive parent.
2. Read this file and the current deployment records.
3. State one narrow evidence domain and acceptance gate.
4. Preserve phone state before Git mutation.
5. Verify exact active and repository paths.
6. For mutation: preflight, backup, rollback, complete-file replacement,
   checksum, exact commit scope, and independent verification.
7. Keep strategy, Supabase, providers, Telegram, and topology changes separated.
8. Prefer a small direct proof over another giant copy-paste package.

## Exactly one next action

Reconcile heartbeat topology while preserving authoritative UTC bucketing,
deadman/recovery behavior, and adding one lock plus bounded monotonic retry
backoff. No other runtime or trading behavior belongs in that package.
