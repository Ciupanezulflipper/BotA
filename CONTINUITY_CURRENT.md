# BotA Current Continuity State

Last updated: 2026-08-03 01:02 UTC

## Authoritative identifiers

```text
HEARTBEAT_CODE_BASELINE=4b89d1e0c729b81472ca78d723316289dd4aebb1
CANONICAL_DOCS_PR=40
PHONE_BRANCH=deploy/repaired-core-20260802T215531Z
PHONE_HEAD=dbdb1b1f9e2e1a6d66bb94b8eda4d1cf40617d20
PHONE_REMOTE_PUSHED=NO
PHONE_PRESERVATION_ROOT=~/bota-phone-preserve-20260802T210517Z
PHONE_UNTRACKED_FILES_PRESERVED=519
```

`HEARTBEAT_CODE_BASELINE` is the immutable merge containing the unified heartbeat
code. Canonical docs do not self-report a current `main` SHA because merging the
documentation necessarily advances `main`.

## Scope lock

Do not change strategy, thresholds, pairs, scoring, ADX, H1/D1 confirmation,
volatility or macro filters, deduplication, SL/TP, PR #7, provider semantics, or
Supabase signal semantics during runtime-reliability work.

## Current phone state

The following repairs are deployed and accepted:

```text
D1 mapping=1440
supervisor core=PASS
supervisor wrapper=non-mutating PASS
status formatter=PASS
autostatus=PASS
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
dbdb1b1f9e2e1a6d66bb94b8eda4d1cf40617d20
```

The August 1 endurance validation remains failed historical evidence. A new
endurance-validation pass has not yet been completed.

## GitHub heartbeat reconciliation

PR #39 merged the heartbeat code baseline:

```text
4b89d1e0c729b81472ca78d723316289dd4aebb1
```

Merged path:

```text
services/bota-heartbeat/run
  -> tools/heartbeat.sh
  -> tools/heartbeat_runtime.py
  -> tools/heartbeat_delivery.py
```

Verified behavior:

- authoritative UTC hour buckets;
- monotonic deadman age;
- deadman alert and recovery preservation;
- one execution lock;
- atomic state;
- bounded Telegram transport;
- separate heartbeat, deadman, and recovery backoff state;
- no service, crontab, strategy, provider, or Supabase mutation.

Verification evidence:

```text
DeepSource Python=PASS
DeepSource Shell=PASS
DeepSource Secrets=PASS
CodeRabbit production review=PASS
heartbeat_delivery tests=18 PASS
heartbeat_runtime tests=8 PASS
live phone mutation during tests=NO
```

## Remaining phone deployment

The active phone still uses:

```text
services/bota-heartbeat/run -> tools/bota_heartbeat_utc.sh
```

Therefore:

```text
HEARTBEAT_GITHUB=MERGED_AND_TESTED
HEARTBEAT_PHONE=NOT_YET_DEPLOYED
```

Deploy exactly:

```text
services/bota-heartbeat/run
tools/heartbeat.sh
tools/heartbeat_runtime.py
tools/heartbeat_delivery.py
```

Also replace:

```text
~/.config/bota-sv/bota-heartbeat/run
```

Restart only `bota-heartbeat`, verify one manager / 7 owned / 7 running / zero
orphans, and inspect `HB_UTC_RESULT` plus `DEADMAN_UTC_RESULT`. Preserve the
legacy UTC script until acceptance passes.

## Evidence

- `audits/PHONE_DEPLOYMENT_2026-08-02.md`
- `audits/P7_SUPERVISOR_WRAPPER_CLOSURE_2026-08-02.md`
- `audits/PR39_HEARTBEAT_RECONCILIATION_2026-08-03.md`
- `audits/INCIDENT_2026-08-01_VALIDATION_FAILURE.md`
- `audits/ERROR_LOG.md`
- `ERRORS.md`
- GitHub issue #9

## Exactly one next action

Deploy the unified heartbeat package to the phone and verify the live heartbeat
service without changing any other service or trading behavior.
