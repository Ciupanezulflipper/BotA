# BotA Current Continuity State

Last updated: 2026-08-03 00:55 UTC

This is the compact authoritative handoff.

## Current repository and phone state

```text
GITHUB_MAIN=4b89d1e0c729b81472ca78d723316289dd4aebb1
PHONE_BRANCH=deploy/repaired-core-20260802T215531Z
PHONE_HEAD=dbdb1b1f9e2e1a6d66bb94b8eda4d1cf40617d20
PHONE_PARENT_HEAD=66fe241cc6afc8ec4fa21f805b5f52340dac3a32
PHONE_REMOTE_PUSHED=NO
PHONE_PRESERVATION_ROOT=~/bota-phone-preserve-20260802T210517Z
PHONE_UNTRACKED_FILES_PRESERVED=519
```

## Scope lock

Current work is runtime reliability, ownership, repository/runtime convergence,
data integrity, provider-budget accounting, notification correctness, and
signal-lifecycle proof.

Do not change trading strategy, thresholds, configured pairs, scoring, ADX,
H1/D1 confirmation, volatility or macro filters, deduplication, SL/TP, PR #7,
or Supabase signal semantics to create more signals.

No direct push to `main`.

## Historical production verdict

The August 1 one-week production validation remains **FAILED** historical
evidence. The current bounded control-plane state has since been repaired and
verified, but a new endurance validation has not yet been completed.

## Deployed phone repairs

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

Acceptance evidence:

```text
P6_TARGETED_RUNTIME_ACCEPTANCE=PASS
SUPERVISOR_ACCEPTANCE_SCENARIOS=6
D1_TIMEFRAME_ACCEPTANCE=PASS
FORMATTER_ACCEPTANCE=PASS
AUTOSTATUS_ACCEPTANCE=PASS
P7_SUPERVISOR_WRAPPER_DEPLOYMENT=PASS
manager_count=1
required=7
owned=7
running=7
orphaned=0
duplicate_service_rows=0
healthy=true
```

The supervisor wrapper auto-mutation risk is closed. Automatic recovery remains
prohibited unless built and tested as a separate authorized mechanism.

## D1 status

```text
tf_minutes("D1")=1440
D1_TIMEFRAME_MAPPING=FIXED_AND_DEPLOYED
D1_LIVE_CACHE_REGENERATION=NOT_YET_RECORDED
```

The code defect is closed. A later live updater cycle must still verify the real
D1 cache artifact.

## GitHub heartbeat reconciliation

PR #39 merged to main as:

```text
4b89d1e0c729b81472ca78d723316289dd4aebb1
```

Merged execution path:

```text
services/bota-heartbeat/run
  -> tools/heartbeat.sh
  -> tools/heartbeat_runtime.py
  -> tools/heartbeat_delivery.py
```

Merged semantics:

- authoritative UTC hour-bucket delivery;
- monotonic deadman age calculation;
- deadman alert and recovery delivery preserved;
- one non-blocking execution lock;
- atomic state persistence;
- bounded Telegram transport;
- separate heartbeat, deadman, and recovery retry states;
- bounded exponential failure backoff;
- no service, crontab, strategy, provider, or Supabase mutation.

Verification:

```text
DeepSource Python=PASS
DeepSource Shell=PASS
DeepSource Secrets=PASS
CodeRabbit production implementation review=PASS
heartbeat_delivery tests=18 PASS
heartbeat_runtime tests=8 PASS
live phone runtime mutation during tests=NO
```

## Remaining phone heartbeat deployment

The active phone still uses:

```text
services/bota-heartbeat/run -> tools/bota_heartbeat_utc.sh
```

Therefore:

```text
HEARTBEAT_GITHUB=MERGED_AND_TESTED
HEARTBEAT_PHONE=NOT_YET_DEPLOYED
HEARTBEAT_TOPOLOGY_RISK=CODE_CLOSED_DEPLOYMENT_OPEN
```

The next package must deploy exactly:

```text
services/bota-heartbeat/run
tools/heartbeat.sh
tools/heartbeat_runtime.py
tools/heartbeat_delivery.py
```

It must also replace the separate active wrapper at:

```text
~/.config/bota-sv/bota-heartbeat/run
```

Then restart only `bota-heartbeat`, verify one manager and 7/7 ownership, and
inspect heartbeat result markers. The legacy `tools/bota_heartbeat_utc.sh` must
remain preserved until the replacement is accepted.

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
HEARTBEAT_GITHUB_RECONCILIATION=CLOSED
HEARTBEAT_PHONE_DEPLOYMENT=OPEN
AUTOMATIC_RECOVERY_REENABLE_ALLOWED=NO
STRATEGY_MUTATION_ALLOWED=NO
```

## Evidence files

- `audits/PHONE_DEPLOYMENT_2026-08-02.md`
- `audits/P7_SUPERVISOR_WRAPPER_CLOSURE_2026-08-02.md`
- `audits/PR39_HEARTBEAT_RECONCILIATION_2026-08-03.md`
- `audits/INCIDENT_2026-08-01_VALIDATION_FAILURE.md`
- `audits/ERROR_LOG.md`
- `ERRORS.md`
- GitHub issue #9

## Exactly one next action

Deploy the four merged heartbeat files and separate active wrapper copy, restart
only `bota-heartbeat`, and verify control-plane plus heartbeat markers. No other
runtime or trading behavior changes belong in that package.
