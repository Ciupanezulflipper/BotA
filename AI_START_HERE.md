# BotA AI Start Here

Last updated: 2026-08-03 01:14 UTC

Read this before proposing BotA commands, code, cron, service, strategy,
notification, provider, Supabase, or deployment changes.

## Current authoritative truth

```text
HEARTBEAT_CODE_BASELINE=4b89d1e0c729b81472ca78d723316289dd4aebb1
PHONE_BRANCH=deploy/repaired-core-20260802T215531Z
PHONE_HEAD=011baaaad7071110e33bca06903047c842e7331a
PHONE_REMOTE_PUSHED=NO
PHONE_PRESERVATION_COMPLETE=YES
PHONE_UNTRACKED_FILES_PRESERVED=519
D1_TIMEFRAME_MAPPING=FIXED_AND_DEPLOYED
SUPERVISOR_CORE=FIXED_DEPLOYED_AND_ACCEPTED
SUPERVISOR_WRAPPER=NON_MUTATING_DEPLOYED_AND_ACCEPTED
CURRENT_CONTROL_PLANE=HEALTHY_7_OF_7
STATUS_FORMATTER=FIXED_DEPLOYED_AND_ACCEPTED
AUTOSTATUS=FIXED_DEPLOYED_AND_ACCEPTED
HEARTBEAT_TOPOLOGY=UNIFIED_DEPLOYED
HEARTBEAT_DELIVERY=PASS
DEADMAN_INPUT=MONOTONIC_PROGRESS_INVALID
AUTOMATIC_TOPOLOGY_RECOVERY_FROM_SUPERVISOR_WRAPPER=DISABLED
STRATEGY_MUTATION_ALLOWED=NO
```

## Evidence order

1. `CONTINUITY_CURRENT.md`
2. `audits/P8_HEARTBEAT_PHONE_DEPLOYMENT_2026-08-03.md`
3. `audits/PR39_HEARTBEAT_RECONCILIATION_2026-08-03.md`
4. `audits/P7_SUPERVISOR_WRAPPER_CLOSURE_2026-08-02.md`
5. `audits/PHONE_DEPLOYMENT_2026-08-02.md`
6. `audits/INCIDENT_2026-08-01_VALIDATION_FAILURE.md`
7. `audits/ERROR_LOG.md`
8. `ERRORS.md`
9. GitHub issue #9

The August 1 one-week production validation remains failed historical evidence.
The August 2–3 repairs prove bounded current behavior but do not yet constitute a
new endurance-validation pass.

## Verified phone state

The phone now contains the repaired core, non-mutating supervisor wrapper, and
unified heartbeat path:

```text
services/bota-heartbeat/run
  -> tools/heartbeat.sh
  -> tools/heartbeat_runtime.py
  -> tools/heartbeat_delivery.py
```

P8 verified:

```text
manager_count=1
required=7
owned=7
running=7
orphaned=0
duplicate_service_rows=0
healthy=true
only_heartbeat_pid_changed=true
HB_UTC_RESULT=PASS sources=3
DEADMAN_UTC_RESULT=MONOTONIC_PROGRESS_INVALID
```

Heartbeat delivery, authoritative UTC lookup, active-wrapper replacement, and
control-plane preservation passed. Deadman monitoring is not accepted because
its live monotonic progress input was invalid.

The legacy `tools/bota_heartbeat_utc.sh` remains preserved unchanged until the
new path has complete deadman acceptance.

## Scope lock

Do not change strategy, thresholds, pairs, scoring, ADX, H1/D1 confirmation,
volatility or macro filters, deduplication, SL/TP, PR #7, provider semantics, or
Supabase signal semantics during runtime-reliability work.

Never push directly to `main`. Two documentation-only direct-main exceptions
occurred while recording P8 and are documented in
`audits/P8_DIRECT_MAIN_DOC_EXCEPTION_2026-08-03.md`; do not repeat them.

## Evidence and time rules

- **VERIFIED** means current direct evidence proves the claim.
- **ASSUMED** means plausible but unproven.
- **UNKNOWN** means insufficient evidence and must not drive mutation.
- Trusted provider/server UTC controls market and candle semantics.
- Monotonic time controls same-boot cadence, cooldowns, backoff, and health.
- Android/ship wall time is display-only.
- Reject negative or future ages.
- Do not use `/proc/uptime` on this Android build.

## Exactly one next action

Inspect `state/shadow_progress.monotonic` and its producer read-only. Determine
whether the live defect is malformed content, incompatible field format,
future/negative monotonic age, boot-ID mismatch, or producer failure. Do not
change heartbeat code, strategy, providers, Supabase, crontab, or service
topology until the exact cause is proven.
