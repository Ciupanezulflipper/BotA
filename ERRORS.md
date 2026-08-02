# BotA Errors and Silent-Failure Register

Last updated: 2026-08-02 23:31 UTC

Purpose: preserve verified failure classes, current open risks, and prevention
rules so they are not rediscovered through repeated broad audits.

Detailed current phone evidence:
`audits/PHONE_DEPLOYMENT_2026-08-02.md`.

## Current production verdict

```text
PRODUCTION_VALIDATION=FAILED
PHONE_PRESERVATION=PASS
FIVE_FILE_CORE_DEPLOYMENT=PASS
D1_CODE_DEFECT=CLOSED
CURRENT_FULL_CONTROL_PLANE=UNKNOWN
ACTIVE_SUPERVISOR_WRAPPER_AUTO_MUTATION=OPEN_RISK
HEARTBEAT_TOPOLOGY=OPEN_RISK
AUTOMATIC_RECOVERY_REENABLE_ALLOWED=NO
STRATEGY_MUTATION_ALLOWED=NO
```

The August 2 bounded phone deployment materially improved BotA but does not erase
the August 1 failed production validation or constitute a new endurance pass.

## Verified phone and repository convergence milestone

GitHub repair baseline:

```text
b4d961ea8e5d254c8578e2c022e1394cd134cd7e
```

Phone deployment state:

```text
branch=deploy/repaired-core-20260802T215531Z
head=d5c765df6fee1241be21ce892fc53e9c4bdcfb8c
remote_push=NO
```

Five files were deployed byte-for-byte from repaired GitHub `main`:

```text
tools/supervisor_clock_status.py
tools/build_indicators.py
tools/format_status.py
tools/autostatus.sh
tools/bota_supervisor.sh
```

Acceptance passed for D1 mapping, six supervisor scenarios, cache-only formatting,
and autostatus delivery isolation. Heartbeat, pipeline health, service wrappers,
crontab, strategy, provider state, Telegram, Supabase, and 519 untracked files
were preserved.

## Closed defect — D1 timeframe mapping

Previous invalid state:

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

The code defect is closed. The actual live D1 cache still needs regeneration and
artifact verification during a later updater cycle.

## Open risk — active supervisor wrapper can mutate topology

The phone-only file `services/bota-supervisor/run` is absent from GitHub `main`.
It does more than schedule the read-only supervisor: when its process match does
not find `runsvdir.*bota-sv`, it starts a manager itself.

This conflicts with the canonical statement that automatic topology recovery is
disabled.

P6 reported both:

```text
SUPERVISOR_SERVICE_STATUS=run
RUNSVDIR_PROCESS_SNAPSHOT=none
```

The second result may be a process-matching defect rather than actual manager
absence. A false negative could cause repeated manager-start attempts and
recreate duplicate or split control-plane conditions.

Prevention:

- active service wrappers must be tracked in GitHub;
- a supervisor scheduler must not create managers;
- exact manager command, PID, parentage, cwd, service ownership, and process
  matching must be verified together;
- manager creation belongs only in an explicitly authorized, bounded recovery
  tool with locking, rollback, and failure-injection proof.

## Open risk — heartbeat execution paths differ

Active phone path:

```text
services/bota-heartbeat/run -> tools/bota_heartbeat_utc.sh
```

GitHub repair path:

```text
tools/heartbeat.sh -> tools/heartbeat_delivery.py
```

The GitHub controller provides lock-based single execution and monotonic bounded
retry backoff. The phone UTC wrapper provides authoritative UTC bucketing and
also owns deadman/recovery notifications, but failed delivery may be retried by
the 60-second service loop.

Prevention:

- preserve deadman/recovery semantics;
- use one active heartbeat delivery controller;
- use one lock and one persisted monotonic backoff state;
- distinguish heartbeat, deadman alert, and recovery delivery state;
- verify the exact active service wrapper before replacing any script.

Topology reconciliation precedes heartbeat reconciliation.

## August 1 production-validation failures retained

Verified historical failures:

- control-plane regression to `owned=0/7`, `running=7/7`, `orphaned=7`;
- temporary required-service counts below seven;
- canonical crontab verification failure;
- phone/GitHub divergence;
- documented watchdog topology not matching the phone;
- configured service-daemon executable unavailable;
- repeated Termux restarts while a continuous guard was active.

Final rollback evidence at the recorded timestamp:

```text
manager_count=1
owned=7/7
running=7/7
orphaned=0
control_plane_rc=0
automatic_recovery=disabled
```

That snapshot is historical and does not prove current ownership.

## Repository contamination retained

PR #24 is a historical preservation artifact, not a valid repair branch. It must
not be merged or deployed. Its behaviors were salvaged only through focused
branches from current `main`.

No direct push to `main`.

## Runtime ownership and scheduler lessons

- Manager existence does not prove service ownership.
- `supervise/pid` identifies the service process, not `runsv`.
- Prove service PID -> PPID -> `runsv` -> manager parent/cwd/command.
- `sv status` alone does not prove parentage or restart capability.
- PID-1 orphan supervisors can survive manager death.
- Starting another manager while orphans remain can create duplicates.
- A process regex can be wrong even when a component is running.
- Service wrappers and boot launchers are executable architecture and must be
  tracked, reviewed, and tested like application code.
- Crontab and runit must not both own the same recurring component.

## Time, health, and data rules

- Trusted provider/server UTC controls market semantics.
- Monotonic time controls same-boot cadence, cooldowns, backoff, and health.
- Android/ship wall time is display-only.
- Never depend on `/proc/uptime` on this Android build.
- Service presence is not useful progress.
- Reject negative and future ages.
- Validate pair, timeframe, granularity, ordering, timestamps, row count, and
  closed-candle semantics before indicators.
- Invalid cache data must fail closed and must not be treated as neutral.

## Provider, notification, and persistence rules

- Track budgets per actual provider and endpoint.
- Status formatting must not hide provider calls.
- Status context is not an executable trade signal.
- Telegram delivery, Supabase persistence, provider failure, runtime failure,
  valid HOLD/rejection, and dedup suppression are distinct outcomes.
- Write the full decision record before dedup.
- Count events only inside a verified current-cycle boundary.

## Operational package rules

- Preserve phone state before Git operations.
- One package, one evidence domain, one acceptance gate.
- Avoid recursive scans through runit FIFOs.
- Expected zero matches must not abort under `pipefail`.
- Strict shell settings belong in bounded child scripts.
- Use complete-file replacements with checksum verification.
- Define rollback before mutation.
- Do not repeat broad discovery when narrow evidence already exists.
- Do not turn every acceptance check into a multi-page Termux procedure when a
  smaller direct proof is sufficient.

## Repository milestones

```text
PR #18 MERGED=ef94e4fd1c9a7a786f7514024828fbdfc1146143
PR #19 MERGED=12000f04137a000cb3d1c6bf7acb45da288907c9
PR #20 MERGED=87e43ce76d43d625e7e9c7a6715cabb59f4b65c9
PR #21 MERGED=09a1bd5b57e0bf3a39e79afc827d14e09e8b1031
PR #22 MERGED=0694e17c09c3c8663622dce745d8b449c3cd2405
PR #23 MERGED=95c54beff7741b32da086bcbd5e87f1c9d132cb5
PR #25 MERGED=2f50904644d86c5564e3d6ae9d3cc777a5a29278
PR #26 MERGED=78d9...
PR #28 MERGED=e09662...
PR #30 MERGED=2e7e02...
PR #31 MERGED=bfd6f26...
PR #32 MERGED=32de...
PR #33 MERGED=ee332796...
PR #34 MERGED=b4d961ea8e5d254c8578e2c022e1394cd134cd7e
```

## Exactly one next repair

Replace the active phone-only `services/bota-supervisor/run` with a tracked,
non-mutating scheduler, then verify one intended manager, seven owned/running
required services, zero orphans/duplicates, and no automatic manager creation.
Only after that passes should heartbeat topology be unified.
