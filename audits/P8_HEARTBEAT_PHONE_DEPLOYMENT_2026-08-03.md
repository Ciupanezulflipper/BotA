# P8 Unified Heartbeat Phone Deployment — 2026-08-03

Recorded: 2026-08-03 01:14 UTC

## Immutable identifiers

```text
HEARTBEAT_CODE_BASELINE=4b89d1e0c729b81472ca78d723316289dd4aebb1
PHONE_BRANCH=deploy/repaired-core-20260802T215531Z
PHONE_PRE_DEPLOY_HEAD=dbdb1b1f9e2e1a6d66bb94b8eda4d1cf40617d20
PHONE_POST_DEPLOY_HEAD=011baaaad7071110e33bca06903047c842e7331a
PHONE_REMOTE_PUSHED=NO
BACKUP=~/bota-phone-preserve-20260802T210517Z/p8-unified-heartbeat-20260803T001345Z
```

## Deployed files

```text
services/bota-heartbeat/run
tools/heartbeat.sh
tools/heartbeat_runtime.py
tools/heartbeat_delivery.py
```

The separate active wrapper was also replaced:

```text
~/.config/bota-sv/bota-heartbeat/run
```

The repository and active wrapper copies were byte-identical after deployment.
The legacy `tools/bota_heartbeat_utc.sh` was preserved unchanged.

## Service and control-plane acceptance

Only `bota-heartbeat` was restarted.

```text
manager_count=1
required=7
owned=7
running=7
orphaned=0
duplicate_service_rows=0
healthy=true
only_heartbeat_pid_changed=true
```

No crontab, strategy, Supabase, provider, or other service mutation occurred.

## Fresh runtime markers

```text
[RUNIT bota-heartbeat 2026-08-03T00:13:49Z] SERVICE_START pid=7453 interval_sec=60 mutation=disabled
[2026-08-03 00:13:59 UTC] HB_UTC_RESULT=PASS sources=3
[2026-08-03 00:13:59 UTC] DEADMAN_UTC_RESULT=MONOTONIC_PROGRESS_INVALID
```

## Precise verdict

```text
P8_UNIFIED_HEARTBEAT_DEPLOYMENT=PASS
HEARTBEAT_DELIVERY=PASS
AUTHORITATIVE_UTC_SOURCES=3
CONTROL_PLANE=HEALTHY_7_OF_7
DEADMAN_INPUT_ACCEPTANCE=FAIL
```

The heartbeat topology and bounded delivery/backoff path are now deployed.
However, deadman monitoring is not accepted because the live monotonic progress
input was rejected as invalid. This is a separate, narrower runtime-data defect;
it must not be hidden by the overall P8 deployment pass.

## Exactly one next action

Inspect the live `state/shadow_progress.monotonic` producer and file contents
read-only. Determine whether the defect is malformed content, incompatible
format, future/negative monotonic age, boot-ID mismatch, or producer failure.
Do not change heartbeat code, strategy, providers, Supabase, crontab, or service
topology until that evidence identifies the exact cause.
