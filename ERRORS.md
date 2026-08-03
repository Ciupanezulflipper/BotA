# BotA Errors and Silent-Failure Register

Last updated: 2026-08-03 00:07 UTC

Purpose: preserve verified failure classes, current open risks, and prevention
rules without repeating broad audits. Detailed current evidence is in:

- `audits/PHONE_DEPLOYMENT_2026-08-02.md`
- `audits/P7_SUPERVISOR_WRAPPER_CLOSURE_2026-08-02.md`
- `audits/INCIDENT_2026-08-01_VALIDATION_FAILURE.md`
- `audits/ERROR_LOG.md`

## Current verdict

```text
PRODUCTION_VALIDATION=FAILED_HISTORICAL
PHONE_PRESERVATION=PASS
CORE_DEPLOYMENT=PASS
D1_CODE_DEFECT=CLOSED
SUPERVISOR_CORE_ACCEPTANCE=PASS
SUPERVISOR_WRAPPER_ACCEPTANCE=PASS
CURRENT_CONTROL_PLANE=HEALTHY_7_OF_7
ACTIVE_SUPERVISOR_WRAPPER_AUTO_MUTATION=CLOSED
HEARTBEAT_TOPOLOGY=OPEN_RISK
AUTOMATIC_RECOVERY_REENABLE_ALLOWED=NO
STRATEGY_MUTATION_ALLOWED=NO
```

The August 1 endurance validation remains failed historical evidence. The
August 2–3 repairs establish a verified current bounded state but do not yet
constitute a new endurance pass.

## Current repository and phone state

```text
GITHUB_MAIN=29ae5babd5a0d6fc5e65b64d3f4f2eea16eaef6d
PHONE_BRANCH=deploy/repaired-core-20260802T215531Z
PHONE_HEAD=dbdb1b1f9e2e1a6d66bb94b8eda4d1cf40617d20
PHONE_REMOTE_PUSHED=NO
UNTRACKED_FILES_PRESERVED=519
```

## Closed defect — D1 timeframe mapping

Previous state:

```text
cache/indicators_EURUSD_D1.json
error=tf_mismatch
tf_ok=false
tf_actual_min=0.0
```

Root cause:

```text
tools/build_indicators.py::tf_minutes("D1") returned 0
```

Current deployed mapping:

```text
tf_minutes("D1")=1440
```

The code defect is closed. Live D1 cache regeneration and artifact verification
remain a later operational check.

## Closed risk — supervisor wrapper could mutate topology

Previous active behavior:

```text
if runsvdir.*bota-sv is not found:
    runsvdir -P "$HOME/.config/bota-sv" &
```

The active runit wrapper and repository copy were separate physical files, and
both differed from the reviewed GitHub version.

P7 replaced both copies with the tracked executable non-mutating scheduler and
restarted only `bota-supervisor`.

Current proof:

```text
ACTIVE_EQUALS_REPOSITORY=YES
SUPERVISOR_WRAPPER_MUTATION_DISABLED=YES
manager_count=1
required=7
owned=7
running=7
orphaned=0
duplicate_service_rows=0
healthy=true
control_plane_rc=0
```

Prevention:

- service wrappers are executable architecture and must be tracked and tested;
- scheduler wrappers must not create managers or restart services;
- active service paths and repository paths must both be identified;
- strict process ownership must be verified by parentage, not broad regex;
- recovery belongs only in a separately authorized tool with locking, rollback,
  bounded backoff, and failure-injection proof.

## Open risk — heartbeat execution paths differ

Active phone path:

```text
services/bota-heartbeat/run -> tools/bota_heartbeat_utc.sh
```

GitHub repair path:

```text
tools/heartbeat.sh -> tools/heartbeat_delivery.py
```

The GitHub controller provides lock-based single execution and bounded monotonic
retry backoff. The phone UTC wrapper provides authoritative UTC bucketing plus
deadman and recovery notifications, but the 60-second service loop may retry a
failed delivery every minute.

Required prevention and acceptance:

- preserve UTC hour-bucket semantics;
- preserve deadman and recovery notifications;
- consolidate to one active delivery controller;
- use one lock and bounded monotonic retry backoff;
- persist heartbeat, deadman, and recovery delivery outcomes separately;
- do not alter strategy, providers, Supabase semantics, crontab, or control-plane
  topology.

## Historical August 1 failures retained

- control-plane regression to `owned=0/7`, `running=7/7`, `orphaned=7`;
- temporary required-service counts below seven;
- canonical crontab verification failure;
- phone/GitHub divergence;
- watchdog documentation not matching the phone;
- configured service-daemon executable unavailable;
- repeated Termux restarts while a continuous guard was active.

The later P7 control-plane proof does not erase these failure records; it proves
the current repaired state.

## Repository contamination retained

PR #24 remains a historical preservation artifact, not a repair or deployment
source. Behaviors must be salvaged only through focused branches from current
`main`.

Never push directly to `main`.

## Runtime and ownership lessons

- Manager existence does not prove service ownership.
- `supervise/pid` identifies the service process, not `runsv`.
- Prove service PID -> `runsv` -> intended manager parentage.
- `sv status` alone does not prove ownership or restart safety.
- PID-1 orphan supervisors can survive manager death.
- Starting another manager while orphans remain can create duplicates.
- A process regex can be wrong even when a component is running.
- Active service and repository directories may contain separate files.
- Crontab and runit must not both own the same recurring component.

## Time, health, data, and delivery rules

- Trusted provider/server UTC controls market semantics.
- Monotonic time controls same-boot cadence, cooldowns, backoff, and health.
- Android/ship wall time is display-only.
- Never depend on `/proc/uptime` on this device.
- Service presence is not useful progress.
- Reject negative and future ages.
- Invalid cache data must fail closed.
- Status context is not an executable trade signal.
- Telegram delivery, Supabase persistence, provider failure, runtime failure,
  valid HOLD, and dedup suppression are distinct outcomes.
- Write the full decision record before dedup.

## Operational package rules

- Keep strict shell settings inside a bounded child shell; never leave them in
  the interactive Termux parent.
- Preserve phone state before Git operations.
- One package, one evidence domain, one acceptance gate.
- Avoid recursive scans through runit FIFOs.
- Expected zero matches must not abort under `pipefail`.
- Use complete-file replacements and checksum verification.
- Define rollback before mutation.
- Prefer a small direct proof over a giant copy-paste package.
- Update canonical documentation and issue #9 after each material gate.

## Repository milestones

```text
PR #24 CLOSED_SUPERSEDED
PR #26 MERGED=78d9...
PR #28 MERGED=e09662...
PR #30 MERGED=2e7e02...
PR #31 MERGED=bfd6f26...
PR #32 MERGED=32de...
PR #33 MERGED=ee332796...
PR #34 MERGED=b4d961ea8e5d254c8578e2c022e1394cd134cd7e
PR #35 MERGED=2c4a2008a2f8e740bab3d3d166d90e73d6624def
PR #36 MERGED=4f03a1f272a260bb793909c07198b22c26d2c87f
PR #37 MERGED=29ae5babd5a0d6fc5e65b64d3f4f2eea16eaef6d
```

## Exactly one next repair

Unify heartbeat delivery while preserving authoritative UTC bucketing,
deadman/recovery behavior, and adding one lock plus bounded monotonic retry
backoff. No other runtime or trading behavior belongs in that package.
