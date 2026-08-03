# BotA Phone Deployment State — 2026-08-02

Last updated: 2026-08-03 00:07 UTC

## Purpose

This record reconciles GitHub `main`, the preserved production-phone checkout,
the bounded core deployment, the supervisor-wrapper closure, and the remaining
heartbeat gap.

## Repository and phone state

```text
GITHUB_MAIN=29ae5babd5a0d6fc5e65b64d3f4f2eea16eaef6d
PHONE_BRANCH=deploy/repaired-core-20260802T215531Z
PHONE_HEAD=dbdb1b1f9e2e1a6d66bb94b8eda4d1cf40617d20
PHONE_PARENT_HEAD=66fe241cc6afc8ec4fa21f805b5f52340dac3a32
REMOTE_PUSH_PERFORMED=NO
```

The phone was not reset or pulled to GitHub `main`. Existing phone-only work was
preserved first, then complete files were applied and committed locally.

## Preservation evidence

```text
PRESERVE_DIR=~/bota-phone-preserve-20260802T210517Z
WORKTREE_CHANGED_FILES=0
INDEX_CHANGED_FILES=0
UNTRACKED_FILES=519
UNTRACKED_ARCHIVED=YES
LOCAL_CONFIG_FILES_BACKED_UP=8
ACTIVE_CRONTAB_BACKED_UP=YES
ALL_GIT_REFS_BUNDLED=YES
```

The preservation package includes Git patches, untracked-file archive, config
copies, crontab snapshot, Git bundle, checksums, and later deployment evidence.

## Core files deployed

The following were deployed byte-for-byte from the repaired GitHub baseline and
committed locally as `d5c765df6fee1241be21ce892fc53e9c4bdcfb8c`:

```text
tools/supervisor_clock_status.py
tools/build_indicators.py
tools/format_status.py
tools/autostatus.sh
tools/bota_supervisor.sh
```

Verified acceptance:

```text
P6_TARGETED_RUNTIME_ACCEPTANCE=PASS
SUPERVISOR_ACCEPTANCE_SCENARIOS=6
D1_TIMEFRAME_ACCEPTANCE=PASS
FORMATTER_ACCEPTANCE=PASS
AUTOSTATUS_ACCEPTANCE=PASS
PROTECTED_HEARTBEAT_FILES_UNCHANGED=YES
PIPELINE_HEALTH_UNCHANGED=YES
LIVE_UNTRACKED_FILES=519
```

No Telegram, provider, Supabase, strategy, crontab, service restart, or remote
push occurred during P6.

## D1 defect status

The root defect was `tools/build_indicators.py::tf_minutes()` mapping D1 to zero.
The deployed implementation verifies:

```text
tf_minutes("D1")=1440
tf_minutes("d1")=1440
D1_TIMEFRAME_MAPPING=FIXED_AND_DEPLOYED
D1_LIVE_CACHE_REGENERATION=NOT_YET_RECORDED
```

The code defect is closed. A later live updater cycle still needs to regenerate
and verify the actual D1 cache.

## Status, autostatus, and supervisor core

Verified deployed behavior:

- formatter reads cache only and performs no provider calls;
- status output is technical context, not a trade entry;
- H1, H4, and D1 coverage is validated;
- autostatus does not invoke the formatter or Telegram when the market gate is
  closed or trusted time is unavailable;
- trusted-clock unavailability remains fail-closed for trading without falsely
  degrading process health;
- supervisor runtime health uses schema 2.1 and atomic writes.

## P7 supervisor-wrapper closure

GitHub added and reviewed a non-mutating executable runit wrapper at:

```text
services/bota-supervisor/run
```

The phone has two independent physical wrapper files:

```text
ACTIVE=~/.config/bota-sv/bota-supervisor/run
REPOSITORY=~/BotA/services/bota-supervisor/run
```

P7 replaced both with the same GitHub version, committed the repository copy as:

```text
PHONE_COMMIT=dbdb1b1f9e2e1a6d66bb94b8eda4d1cf40617d20
COMMIT_SUBJECT=deploy: activate non-mutating supervisor wrapper
```

Only `bota-supervisor` was restarted. Post-restart control-plane proof:

```text
manager_count=1
manager_pid=10341
required=7
owned=7
running=7
orphaned=0
duplicate_service_rows=0
healthy=true
control_plane_rc=0
```

The seven owned/running components were:

```text
bota-updater
bota-watcher
bota-closer
bota-shadow
bota-heartbeat
bota-supervisor
crond
```

The active wrapper is now identical to the repository copy and contains no
manager or service mutation. The earlier risk that the supervisor wrapper could
start `runsvdir` automatically is closed.

P7 backup:

```text
~/bota-phone-preserve-20260802T210517Z/p7-supervisor-wrapper-20260802T230646Z
```

## Heartbeat topology gap

The active phone heartbeat path remains:

```text
services/bota-heartbeat/run
  -> tools/bota_heartbeat_utc.sh
```

GitHub implements:

```text
tools/heartbeat.sh
  -> tools/heartbeat_delivery.py
```

The GitHub controller provides locking and bounded monotonic retry backoff. The
active phone UTC wrapper owns authoritative UTC bucketing plus deadman and
recovery notifications. It may retry failed delivery every 60 seconds because
the runit service loop invokes it each minute.

Required reconciliation properties:

- one active heartbeat delivery controller;
- authoritative UTC bucket behavior preserved;
- deadman alerting preserved;
- recovery delivery preserved;
- separate persisted state for heartbeat, deadman, and recovery outcomes;
- one execution lock;
- bounded monotonic retry backoff;
- no control-plane, crontab, strategy, provider, or Supabase changes.

## Files deliberately unchanged through P7

```text
tools/heartbeat.sh
tools/bota_heartbeat_utc.sh
services/bota-heartbeat/run
tools/pipeline_health.py
```

The active crontab and 519 untracked runtime/audit files remain preserved.

## Scope lock

No strategy, threshold, scoring, pair, ADX, H1/D1 confirmation, volatility,
macro, deduplication, SL/TP, PR #7, provider, Telegram, or Supabase semantic
changes are authorized by this record.

## Exact next action

Reconcile heartbeat topology while preserving UTC bucketing and deadman/recovery
behavior and adding locking plus bounded monotonic retry backoff. No other
runtime or trading behavior belongs in that package.
