# BotA AI Start Here

Last updated: 2026-08-03 00:55 UTC

Read this before proposing BotA commands, code, cron, service, strategy,
notification, provider, Supabase, or deployment changes.

## Current authoritative truth

```text
GITHUB_MAIN=4b89d1e0c729b81472ca78d723316289dd4aebb1
PHONE_BRANCH=deploy/repaired-core-20260802T215531Z
PHONE_HEAD=dbdb1b1f9e2e1a6d66bb94b8eda4d1cf40617d20
PHONE_REMOTE_PUSHED=NO
PHONE_PRESERVATION_COMPLETE=YES
PHONE_UNTRACKED_FILES_PRESERVED=519
D1_TIMEFRAME_MAPPING=FIXED_AND_DEPLOYED
SUPERVISOR_CORE=FIXED_DEPLOYED_AND_ACCEPTED
SUPERVISOR_WRAPPER=NON_MUTATING_DEPLOYED_AND_ACCEPTED
CURRENT_CONTROL_PLANE=HEALTHY_7_OF_7
STATUS_FORMATTER=FIXED_DEPLOYED_AND_ACCEPTED
AUTOSTATUS=FIXED_DEPLOYED_AND_ACCEPTED
HEARTBEAT_GITHUB=UNIFIED_MERGED_AND_TESTED
HEARTBEAT_PHONE=NOT_YET_DEPLOYED
AUTOMATIC_TOPOLOGY_RECOVERY_FROM_SUPERVISOR_WRAPPER=DISABLED
STRATEGY_MUTATION_ALLOWED=NO
```

Read these in order:

1. `CONTINUITY_CURRENT.md`
2. `audits/PHONE_DEPLOYMENT_2026-08-02.md`
3. `audits/P7_SUPERVISOR_WRAPPER_CLOSURE_2026-08-02.md`
4. `audits/PR39_HEARTBEAT_RECONCILIATION_2026-08-03.md`
5. `audits/INCIDENT_2026-08-01_VALIDATION_FAILURE.md`
6. `audits/ERROR_LOG.md`
7. `ERRORS.md`
8. GitHub issue #9

The August 1 one-week production validation remains failed historical evidence.
The August 2–3 repairs prove bounded current behavior but do not yet constitute a
new endurance-validation pass.

## Verified phone state

The phone currently contains repaired versions of:

```text
tools/supervisor_clock_status.py
tools/build_indicators.py
tools/format_status.py
tools/autostatus.sh
tools/bota_supervisor.sh
services/bota-supervisor/run
```

P7 verified:

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

The active supervisor wrapper is executable, identical in both physical phone
locations, and cannot start `runsvdir`, restart services, or alter topology.

## Heartbeat state

GitHub PR #39 merged as:

```text
4b89d1e0c729b81472ca78d723316289dd4aebb1
```

The merged architecture is:

```text
services/bota-heartbeat/run
  -> tools/heartbeat.sh
  -> tools/heartbeat_runtime.py
  -> tools/heartbeat_delivery.py
```

It preserves authoritative UTC hour buckets, monotonic deadman and recovery
semantics, one execution lock, atomic state, bounded transport, and separate
bounded retry state for heartbeat, deadman, and recovery delivery.

Review and test evidence:

```text
DeepSource Python=PASS
DeepSource Shell=PASS
DeepSource Secrets=PASS
CodeRabbit production implementation review=PASS
Existing heartbeat delivery tests=18 PASS
Unified heartbeat runtime tests=8 PASS
Phone runtime mutation during tests=NO
```

The phone still runs the legacy path:

```text
services/bota-heartbeat/run
  -> tools/bota_heartbeat_utc.sh
```

Do not describe heartbeat reconciliation as deployed until the four-file phone
package is committed, the active wrapper copy is replaced, only
`bota-heartbeat` is restarted, and control-plane plus heartbeat markers pass.

## Scope lock

Do not change strategy, thresholds, pairs, scoring, ADX, H1/D1 confirmation,
volatility or macro filters, deduplication, SL/TP, PR #7, or Supabase signal
semantics to manufacture signals.

Never push directly to `main`.

## Evidence and time rules

- **VERIFIED** means current direct evidence proves the claim.
- **ASSUMED** means plausible but unproven.
- **UNKNOWN** means insufficient evidence and must not drive mutation.
- Trusted provider/server UTC controls market and candle semantics.
- Monotonic time controls same-boot cadence, cooldowns, backoff, and health.
- Android/ship wall time is display-only.
- Reject negative or future ages.
- Do not use `/proc/uptime` on this Android build.

## Phone safety rules

Before phone Git mutation:

1. verify branch and exact HEAD;
2. preserve intended target files and active service copies;
3. use complete-file replacements;
4. define rollback before mutation;
5. stage and commit only the intended files;
6. keep strict shell options inside a bounded child shell;
7. do not pull, reset, or overwrite unknown local work;
8. do not push directly to `main`.

Current preservation root:

```text
~/bota-phone-preserve-20260802T210517Z
```

## Exactly one next action

Deploy the four merged heartbeat files from GitHub main to the phone, replace the
separate active runit wrapper copy, restart only `bota-heartbeat`, and verify the
control plane remains 7/7 with authoritative UTC and deadman markers present.
No strategy, provider, Supabase, crontab, or other service change belongs in that
package.
