# BotA Current Continuity State

Last updated: 2026-08-02 23:31 UTC

This is the compact authoritative handoff. Detailed phone-deployment evidence is
in `audits/PHONE_DEPLOYMENT_2026-08-02.md`. Historical failure detail remains in
`audits/INCIDENT_2026-08-01_VALIDATION_FAILURE.md`, `audits/ERROR_LOG.md`,
`ERRORS.md`, and GitHub issue #9.

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
GITHUB_MAIN=b4d961ea8e5d254c8578e2c022e1394cd134cd7e
PHONE_BRANCH=deploy/repaired-core-20260802T215531Z
PHONE_HEAD=d5c765df6fee1241be21ce892fc53e9c4bdcfb8c
PHONE_PARENT_HEAD=66fe241cc6afc8ec4fa21f805b5f52340dac3a32
PHONE_REMOTE_PUSHED=NO
```

Before reconciliation, the phone checkout was preserved at:

```text
~/bota-phone-preserve-20260802T210517Z
```

Preservation verified zero tracked/staged changes, archived 519 untracked files,
backed up eight local config files, active crontab, all Git refs, patches, and
checksums.

## August 1 production validation

The one-week production validation remains **FAILED**.

Verified historical failures included:

- `owned=0/7`, `running=7/7`, `orphaned=7`;
- temporary required-service counts below seven;
- phone/GitHub divergence;
- canonical crontab verification failure;
- watchdog documentation not matching the phone;
- unavailable configured service-daemon executable;
- repeated Termux restarts while a continuous guard was active.

Recorded rollback at that timestamp:

```text
manager_count=1
owned=7/7
running=7/7
orphaned=0
control_plane_rc=0
automatic_recovery=disabled
```

That rollback snapshot remains historical evidence only. It is not current
7/7 ownership proof.

## August 2 repository repairs

GitHub `main` now contains focused repairs for:

- D1 timeframe mapping and validation;
- cache-only status formatting;
- market-gated autostatus delivery;
- monotonic heartbeat delivery control;
- supervisor clock observability separated from process/runtime failure.

PR #24 remains contaminated, superseded, and prohibited as a merge/deployment
source.

## August 2 phone deployment

Five complete repaired files were copied byte-for-byte from GitHub baseline
`b4d961e` and committed locally on the phone:

```text
tools/supervisor_clock_status.py
tools/build_indicators.py
tools/format_status.py
tools/autostatus.sh
tools/bota_supervisor.sh
```

Phone deployment commit:

```text
d5c765df6fee1241be21ce892fc53e9c4bdcfb8c
```

No heartbeat file, pipeline-health file, service wrapper, crontab entry, strategy,
provider, Telegram, Supabase, or remote branch was changed by that deployment.

## Acceptance status

```text
P6_TARGETED_RUNTIME_ACCEPTANCE=PASS
SUPERVISOR_ACCEPTANCE_SCENARIOS=6
D1_TIMEFRAME_ACCEPTANCE=PASS
FORMATTER_ACCEPTANCE=PASS
AUTOSTATUS_ACCEPTANCE=PASS
PROTECTED_HEARTBEAT_FILES_UNCHANGED=YES
PIPELINE_HEALTH_UNCHANGED=YES
```

The deployed supervisor passed healthy/open, healthy/closed,
clock-unavailable, gate-error, control-failure, and pipeline-failure scenarios in
an isolated `BOTA_ROOT` without Telegram, provider, service, or crontab mutation.

## D1 defect status

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
verify the actual D1 cache artifact.

## Active supervisor status

Verified during P6:

```text
SUPERVISOR_SERVICE_STATUS=run
SUPERVISOR_SERVICE_PID=10711
ACTIVE_WRAPPER_TARGETS_DEPLOYED_SUPERVISOR=YES
```

This proves the deployed supervisor script is on the active path. It does not
prove the complete current 7/7 ownership chain.

## Critical current topology inconsistency

The active phone-only file `services/bota-supervisor/run` is absent from GitHub
`main` and contains automatic mutation:

```text
if runsvdir.*bota-sv is not found:
    runsvdir -P "$HOME/.config/bota-sv" &
```

This conflicts with the earlier claim that automatic topology recovery is
disabled. P6 also printed `RUNSVDIR_PROCESS_SNAPSHOT=none`; this may reflect a
bad process match rather than true absence, creating a duplicate-manager risk.

Current status:

```text
AUTOMATIC_TOPOLOGY_RECOVERY=INCONSISTENT_WITH_ACTIVE_PHONE_WRAPPER
FULL_CURRENT_7_OF_7_OWNERSHIP=UNKNOWN
SUPERVISOR_WRAPPER_REPAIR_REQUIRED=YES
```

## Heartbeat gap

Active phone path:

```text
services/bota-heartbeat/run -> tools/bota_heartbeat_utc.sh
```

GitHub path:

```text
tools/heartbeat.sh -> tools/heartbeat_delivery.py
```

The GitHub controller provides locking and bounded retry backoff. The phone UTC
wrapper owns deadman/recovery behavior but may retry failed Telegram delivery
every 60 seconds. Replacement must preserve deadman semantics.

Heartbeat work is second priority, after supervisor-wrapper topology is made
non-mutating and verified.

## Current status summary

```text
PRODUCTION_VALIDATION=FAILED
PHONE_PRESERVATION=PASS
FIVE_FILE_CORE_DEPLOYMENT=PASS
D1_CODE_DEFECT=CLOSED
SUPERVISOR_CORE_ACCEPTANCE=PASS
STATUS_FORMATTER_ACCEPTANCE=PASS
AUTOSTATUS_ACCEPTANCE=PASS
CURRENT_FULL_CONTROL_PLANE=UNKNOWN
ACTIVE_SUPERVISOR_WRAPPER_AUTO_MUTATION=OPEN_RISK
HEARTBEAT_TOPOLOGY=OPEN_RISK
AUTOMATIC_RECOVERY_REENABLE_ALLOWED=NO
STRATEGY_MUTATION_ALLOWED=NO
```

## Exactly one next action

Replace `services/bota-supervisor/run` with a non-mutating scheduler that only
invokes `tools/bota_supervisor.sh`, then verify exactly one intended `runsvdir`,
seven owned/running required services, zero orphans/duplicates, and no automatic
manager creation. Heartbeat reconciliation follows after this gate passes.
