# BotA Current Continuity State

Last updated: 2026-08-03 01:14 UTC

## Authoritative identifiers

```text
HEARTBEAT_CODE_BASELINE=4b89d1e0c729b81472ca78d723316289dd4aebb1
PHONE_BRANCH=deploy/repaired-core-20260802T215531Z
PHONE_HEAD=011baaaad7071110e33bca06903047c842e7331a
PHONE_REMOTE_PUSHED=NO
PHONE_PRESERVATION_ROOT=~/bota-phone-preserve-20260802T210517Z
PHONE_UNTRACKED_FILES_PRESERVED=519
P8_BACKUP=~/bota-phone-preserve-20260802T210517Z/p8-unified-heartbeat-20260803T001345Z
```

## Scope lock

Do not change strategy, thresholds, pairs, scoring, ADX, H1/D1 confirmation,
volatility or macro filters, deduplication, SL/TP, PR #7, provider semantics, or
Supabase signal semantics during runtime-reliability work.

## Deployed and accepted

```text
D1 mapping=1440
supervisor core=PASS
supervisor wrapper=non-mutating PASS
status formatter=PASS
autostatus=PASS
unified heartbeat topology=DEPLOYED
heartbeat delivery=PASS
manager_count=1
required=7
owned=7
running=7
orphaned=0
duplicate_service_rows=0
healthy=true
```

Phone deployment commits:

```text
d5c765df6fee1241be21ce892fc53e9c4bdcfb8c
  deploy: apply repaired non-heartbeat runtime core

dbdb1b1f9e2e1a6d66bb94b8eda4d1cf40617d20
  deploy: activate non-mutating supervisor wrapper

011baaaad7071110e33bca06903047c842e7331a
  deploy: activate unified heartbeat runtime
```

## P8 heartbeat deployment

The active path is now:

```text
services/bota-heartbeat/run
  -> tools/heartbeat.sh
  -> tools/heartbeat_runtime.py
  -> tools/heartbeat_delivery.py
```

P8 replaced the four repository files plus the separate active wrapper,
restarted only `bota-heartbeat`, and verified that only the heartbeat wrapper PID
changed. The legacy `tools/bota_heartbeat_utc.sh` was preserved unchanged.

Fresh markers:

```text
[RUNIT bota-heartbeat 2026-08-03T00:13:49Z] SERVICE_START pid=7453 interval_sec=60 mutation=disabled
[2026-08-03 00:13:59 UTC] HB_UTC_RESULT=PASS sources=3
[2026-08-03 00:13:59 UTC] DEADMAN_UTC_RESULT=MONOTONIC_PROGRESS_INVALID
```

Precise verdict:

```text
P8_UNIFIED_HEARTBEAT_DEPLOYMENT=PASS
HEARTBEAT_TOPOLOGY=DEPLOYED
HEARTBEAT_DELIVERY=PASS
AUTHORITATIVE_UTC=PASS_3_SOURCES
CONTROL_PLANE=HEALTHY_7_OF_7
DEADMAN_INPUT_ACCEPTANCE=FAIL
```

The deadman defect is now narrower than the original heartbeat topology issue.
The unified controller is active, but it rejected the current
`state/shadow_progress.monotonic` input. Do not describe deadman monitoring as
healthy until that input and its producer are proven valid.

## Historical status

The August 1 endurance validation remains failed historical evidence. A new
endurance-validation pass has not yet been completed.

Two documentation-only direct-main commits occurred while recording P8. They are
recorded in `audits/P8_DIRECT_MAIN_DOC_EXCEPTION_2026-08-03.md`. No runtime code
or phone state was changed by those documentation commits, but the process rule
was violated and must not be repeated.

## Evidence

- `audits/P8_HEARTBEAT_PHONE_DEPLOYMENT_2026-08-03.md`
- `audits/PR39_HEARTBEAT_RECONCILIATION_2026-08-03.md`
- `audits/P7_SUPERVISOR_WRAPPER_CLOSURE_2026-08-02.md`
- `audits/PHONE_DEPLOYMENT_2026-08-02.md`
- `audits/INCIDENT_2026-08-01_VALIDATION_FAILURE.md`
- `audits/ERROR_LOG.md`
- `ERRORS.md`
- GitHub issue #9

## Exactly one next action

Inspect the live monotonic progress file and its producer read-only. Prove the
exact cause of `MONOTONIC_PROGRESS_INVALID` before changing any file or service.
