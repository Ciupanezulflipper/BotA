# BotA AI Start Here

Last updated: 2026-08-02 23:31 UTC

Read this before proposing BotA commands, code, cron, service, strategy,
notification, provider, Supabase, or deployment changes.

## Current authoritative truth

```text
GITHUB_MAIN=b4d961ea8e5d254c8578e2c022e1394cd134cd7e
PHONE_BRANCH=deploy/repaired-core-20260802T215531Z
PHONE_HEAD=d5c765df6fee1241be21ce892fc53e9c4bdcfb8c
PHONE_REMOTE_PUSHED=NO
PHONE_PRESERVATION_COMPLETE=YES
PHONE_UNTRACKED_FILES_PRESERVED=519
D1_TIMEFRAME_MAPPING=FIXED_AND_DEPLOYED
SUPERVISOR_CORE=FIXED_DEPLOYED_AND_ACCEPTED
STATUS_FORMATTER=FIXED_DEPLOYED_AND_ACCEPTED
AUTOSTATUS=FIXED_DEPLOYED_AND_ACCEPTED
HEARTBEAT_ACTIVE_PATH=NOT_RECONCILED
AUTOMATIC_TOPOLOGY_RECOVERY=INCONSISTENT_WITH_ACTIVE_PHONE_WRAPPER
FULL_CURRENT_7_OF_7_OWNERSHIP=UNKNOWN
STRATEGY_MUTATION_ALLOWED=NO
```

Read `audits/PHONE_DEPLOYMENT_2026-08-02.md` for the exact current phone state,
checksums, backup locations, acceptance evidence, and remaining gaps.

The August 1 production validation remains failed. The five-file August 2 phone
deployment is a bounded repair milestone, not a new production-validation pass.

## What is fixed on the phone

The production phone now contains complete-file copies from repaired GitHub
`main` for:

```text
tools/supervisor_clock_status.py
tools/build_indicators.py
tools/format_status.py
tools/autostatus.sh
tools/bota_supervisor.sh
```

Verified behavior:

- `tf_minutes("D1") == 1440`;
- temporary trusted-clock failure remains fail-closed for trading but no longer
  falsely becomes a process-health failure;
- status formatting is cache-only and explicitly not an entry signal;
- autostatus does not call the formatter or Telegram when the market gate is
  closed or the trusted clock is unavailable;
- six isolated supervisor scenarios passed;
- no Telegram, provider, Supabase, service restart, crontab mutation, strategy
  mutation, or remote push occurred during acceptance.

## Critical unresolved topology finding

The active phone file `services/bota-supervisor/run` is not tracked on GitHub
`main`. It contains logic that starts:

```text
runsvdir -P "$HOME/.config/bota-sv" &
```

when its process match fails.

That contradicts the earlier canonical statement that automatic topology
recovery is disabled. It also means the service wrapper can mutate manager state
while the deployed `tools/bota_supervisor.sh` itself is read-only.

Do not treat the current topology as fully verified merely because:

```text
sv status bota-supervisor = run
```

The next gate must inspect exact manager command, parentage, service ownership,
and process matching, then replace the wrapper with a non-mutating scheduler.

## Heartbeat gap

The active phone path is:

```text
services/bota-heartbeat/run
  -> tools/bota_heartbeat_utc.sh
```

GitHub `main` contains:

```text
tools/heartbeat.sh
  -> tools/heartbeat_delivery.py
```

The GitHub controller adds locking and bounded monotonic retry backoff. The phone
UTC wrapper additionally owns deadman and recovery behavior. Do not replace one
with the other until deadman semantics are preserved deliberately.

Topology reconciliation comes before heartbeat reconciliation.

## Scope lock

Current work is limited to:

- runtime reliability and ownership;
- repository/runtime convergence;
- data integrity;
- provider-budget accounting;
- Telegram/status correctness;
- signal-lifecycle proof.

Do not change strategy, thresholds, pairs, scoring, ADX, H1/D1 confirmation,
volatility or macro filters, deduplication, SL/TP, PR #7, or Supabase signal
semantics to manufacture signals.

Never push directly to `main`.

## Evidence rules

Classify material claims as:

- **VERIFIED** — current direct evidence proves it;
- **ASSUMED** — plausible but unproven;
- **UNKNOWN** — insufficient evidence and must not drive mutation.

Historical PASS evidence remains valid only for its timestamp. A running service
status is not proof of correct ownership or restart safety.

## Time semantics

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
5. stage and commit only the exact intended file set;
6. do not pull, reset, checkout, or overwrite unknown local work;
7. do not push directly to `main`.

Current preservation root:

```text
~/bota-phone-preserve-20260802T210517Z
```

## Files to read

1. `CONTINUITY_CURRENT.md`
2. `audits/PHONE_DEPLOYMENT_2026-08-02.md`
3. `audits/INCIDENT_2026-08-01_VALIDATION_FAILURE.md`
4. `audits/ERROR_LOG.md`
5. `ERRORS.md`
6. GitHub issue #9

## Exactly one next action

Reconcile `services/bota-supervisor/run`: remove automatic `runsvdir` creation,
retain only bounded scheduling of the deployed supervisor, and independently
verify one intended manager, seven owned/running required services, zero
orphans/duplicates, and no manager mutation. Heartbeat work follows after this
gate passes.
