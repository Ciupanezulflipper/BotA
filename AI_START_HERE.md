# BotA AI Start Here

Last updated: 2026-08-03 00:07 UTC

Read this before proposing BotA commands, code, cron, service, strategy,
notification, provider, Supabase, or deployment changes.

## Current authoritative truth

```text
GITHUB_MAIN=29ae5babd5a0d6fc5e65b64d3f4f2eea16eaef6d
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
HEARTBEAT_ACTIVE_PATH=NOT_RECONCILED
AUTOMATIC_TOPOLOGY_RECOVERY_FROM_SUPERVISOR_WRAPPER=DISABLED
STRATEGY_MUTATION_ALLOWED=NO
```

Read these in order:

1. `CONTINUITY_CURRENT.md`
2. `audits/PHONE_DEPLOYMENT_2026-08-02.md`
3. `audits/P7_SUPERVISOR_WRAPPER_CLOSURE_2026-08-02.md`
4. `audits/INCIDENT_2026-08-01_VALIDATION_FAILURE.md`
5. `audits/ERROR_LOG.md`
6. `ERRORS.md`
7. GitHub issue #9

The August 1 one-week production validation remains failed historical evidence.
The August 2–3 repairs prove the current bounded state described below; they do
not yet constitute a new endurance validation.

## What is fixed on the phone

The production phone contains complete-file repaired versions of:

```text
tools/supervisor_clock_status.py
tools/build_indicators.py
tools/format_status.py
tools/autostatus.sh
tools/bota_supervisor.sh
services/bota-supervisor/run
```

Verified behavior:

- `tf_minutes("D1") == 1440`;
- trusted-clock unavailability remains fail-closed for trading without falsely
  becoming a process-health failure;
- status formatting is cache-only and explicitly not an entry signal;
- autostatus does not call the formatter or Telegram when the market gate is
  closed or the trusted clock is unavailable;
- the active and repository supervisor wrappers are identical, executable, and
  non-mutating;
- the supervisor wrapper cannot create or restart `runsvdir`, `runsv`, or an
  individual service;
- one manager currently owns all seven required services.

## Current control-plane proof

P7 verified immediately after restarting only `bota-supervisor`:

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

The seven required components are:

```text
bota-updater
bota-watcher
bota-closer
bota-shadow
bota-heartbeat
bota-supervisor
crond
```

This closes the supervisor-wrapper auto-mutation risk. Automatic recovery must
remain disabled unless a separately authorized recovery design is built and
failure-tested.

## Remaining heartbeat gap

The active phone path is:

```text
services/bota-heartbeat/run
  -> tools/bota_heartbeat_utc.sh
```

GitHub contains:

```text
tools/heartbeat.sh
  -> tools/heartbeat_delivery.py
```

The GitHub controller adds single-execution locking and bounded monotonic retry
backoff. The active phone UTC wrapper additionally owns authoritative UTC
bucketing, deadman alerting, and recovery delivery. Do not replace one with the
other until those deadman semantics are preserved deliberately.

The next package must produce one active heartbeat delivery controller with:

- authoritative UTC bucket semantics;
- deadman and recovery behavior preserved;
- one lock;
- bounded monotonic retry backoff;
- distinct state for heartbeat, deadman, and recovery delivery;
- no strategy, provider, Supabase, or service-topology changes.

## Scope lock

Current work is limited to runtime reliability, repository/runtime convergence,
data integrity, provider-budget accounting, Telegram/status correctness, and
signal-lifecycle proof.

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
2. preserve tracked, staged, untracked, config, crontab, and Git refs;
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

Reconcile the active heartbeat path while preserving authoritative UTC bucketing,
deadman alerting, and recovery behavior, and add the GitHub controller's locking
and bounded monotonic retry backoff. No other runtime or trading behavior changes
belong in that package.
