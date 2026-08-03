# BotA Current Continuity State

Last updated: 2026-08-03 00:07 UTC

This is the compact authoritative handoff. Detailed deployment and control-plane
evidence is in:

- `audits/PHONE_DEPLOYMENT_2026-08-02.md`
- `audits/P7_SUPERVISOR_WRAPPER_CLOSURE_2026-08-02.md`
- `audits/INCIDENT_2026-08-01_VALIDATION_FAILURE.md`
- `audits/ERROR_LOG.md`
- `ERRORS.md`
- GitHub issue #9

## Scope lock

Current work is runtime reliability, ownership, repository/runtime convergence,
data integrity, provider-budget accounting, notification correctness, and
signal-lifecycle proof.

Do not change trading strategy, thresholds, configured pairs, scoring, ADX,
H1/D1 confirmation, volatility or macro filters, deduplication, SL/TP, PR #7,
or Supabase signal semantics to create more signals.

No direct push to `main`.

## Current repository and phone state

```text
GITHUB_MAIN=29ae5babd5a0d6fc5e65b64d3f4f2eea16eaef6d
PHONE_BRANCH=deploy/repaired-core-20260802T215531Z
PHONE_HEAD=dbdb1b1f9e2e1a6d66bb94b8eda4d1cf40617d20
PHONE_PARENT_HEAD=66fe241cc6afc8ec4fa21f805b5f52340dac3a32
PHONE_REMOTE_PUSHED=NO
```

Phone preservation root:

```text
~/bota-phone-preserve-20260802T210517Z
```

Preservation verified zero tracked/staged changes before reconciliation,
archived 519 untracked files, and backed up local configs, crontab, Git refs,
patches, and checksums.

## Historical production verdict

The August 1 one-week production validation remains **FAILED** historical
evidence. That failure included orphaned supervisors, temporary service-count
loss, phone/GitHub divergence, crontab verification failure, and invalid recovery
assumptions.

The current bounded control-plane state has since been repaired and verified,
but a new endurance validation has not yet been completed.

## Deployed repairs

The phone now contains repaired complete-file versions of:

```text
tools/supervisor_clock_status.py
tools/build_indicators.py
tools/format_status.py
tools/autostatus.sh
tools/bota_supervisor.sh
services/bota-supervisor/run
```

Local deployment commits:

```text
d5c765df6fee1241be21ce892fc53e9c4bdcfb8c
  deploy: apply repaired non-heartbeat runtime core

dbdb1b1f9e2e1a6d66bb94b8eda4d1cf40617d20
  deploy: activate non-mutating supervisor wrapper
```

## Acceptance status

```text
P6_TARGETED_RUNTIME_ACCEPTANCE=PASS
SUPERVISOR_ACCEPTANCE_SCENARIOS=6
D1_TIMEFRAME_ACCEPTANCE=PASS
FORMATTER_ACCEPTANCE=PASS
AUTOSTATUS_ACCEPTANCE=PASS
P7_SUPERVISOR_WRAPPER_DEPLOYMENT=PASS
PROTECTED_HEARTBEAT_FILES_UNCHANGED=YES
PIPELINE_HEALTH_UNCHANGED=YES
```

## D1 status

Root cause:

```text
tools/build_indicators.py::tf_minutes("D1") returned 0
```

Current deployed result:

```text
tf_minutes("D1")=1440
D1_TIMEFRAME_MAPPING=FIXED_AND_DEPLOYED
D1_LIVE_CACHE_REGENERATION=NOT_YET_RECORDED
```

The code defect is closed. A later live updater cycle must still regenerate and
verify the real D1 cache artifact.

## Supervisor-wrapper closure

GitHub tracks an executable non-mutating scheduler at:

```text
services/bota-supervisor/run
```

The phone has two physical copies:

```text
~/.config/bota-sv/bota-supervisor/run
~/BotA/services/bota-supervisor/run
```

P7 replaced both copies with the same GitHub version, restarted only
`bota-supervisor`, and verified:

```text
manager_count=1
required=7
owned=7
running=7
orphaned=0
duplicate_service_rows=0
healthy=true
control_plane_rc=0
```

The wrapper no longer creates or probes `runsvdir`, `runsv`, or individual
services. The earlier supervisor-wrapper automatic-recovery inconsistency is
closed.

Automatic recovery remains prohibited unless implemented in a separate,
explicitly authorized recovery tool with locking, rollback, backoff, and
failure-injection proof.

## Remaining heartbeat gap

Active phone path:

```text
services/bota-heartbeat/run -> tools/bota_heartbeat_utc.sh
```

GitHub repair path:

```text
tools/heartbeat.sh -> tools/heartbeat_delivery.py
```

The GitHub controller provides locking and bounded monotonic retry backoff. The
active phone UTC wrapper provides authoritative UTC bucketing plus deadman and
recovery behavior, but a failed send can be retried by the 60-second service
loop.

Reconciliation must preserve:

- authoritative UTC hour-bucket behavior;
- deadman alerting;
- recovery delivery;
- distinct delivery state;
- one lock and bounded monotonic retry backoff.

## Current status summary

```text
PRODUCTION_VALIDATION=FAILED_HISTORICAL
PHONE_PRESERVATION=PASS
CORE_DEPLOYMENT=PASS
D1_CODE_DEFECT=CLOSED
SUPERVISOR_CORE_ACCEPTANCE=PASS
SUPERVISOR_WRAPPER_ACCEPTANCE=PASS
CURRENT_CONTROL_PLANE=HEALTHY_7_OF_7
STATUS_FORMATTER_ACCEPTANCE=PASS
AUTOSTATUS_ACCEPTANCE=PASS
SUPERVISOR_WRAPPER_AUTO_MUTATION=CLOSED
HEARTBEAT_TOPOLOGY=OPEN_RISK
AUTOMATIC_RECOVERY_REENABLE_ALLOWED=NO
STRATEGY_MUTATION_ALLOWED=NO
```

## Exactly one next action

Unify heartbeat delivery so the active service preserves UTC bucketing,
deadman/recovery semantics, and gains one lock plus bounded monotonic retry
backoff. Do not change strategy, providers, Supabase semantics, crontab, or the
control-plane topology in that package.
