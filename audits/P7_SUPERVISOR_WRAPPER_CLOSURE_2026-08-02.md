# P7 Supervisor Wrapper Closure — 2026-08-02

Recorded at: 2026-08-03 00:07 UTC

## Result

The active phone supervisor wrapper and the repository copy were both replaced
with the tracked non-mutating scheduler from GitHub.

```text
GITHUB_MAIN=29ae5babd5a0d6fc5e65b64d3f4f2eea16eaef6d
PHONE_BRANCH=deploy/repaired-core-20260802T215531Z
PHONE_HEAD=dbdb1b1f9e2e1a6d66bb94b8eda4d1cf40617d20
ACTIVE_WRAPPER_UPDATED=YES
REPOSITORY_WRAPPER_UPDATED=YES
ACTIVE_EQUALS_REPOSITORY=YES
SUPERVISOR_WRAPPER_MUTATION_DISABLED=YES
SUPERVISOR_SERVICE_RESTARTED=YES
REMOTE_PUSH_PERFORMED=NO
```

The active wrapper path is independent from the repository path:

```text
~/.config/bota-sv/bota-supervisor/run
~/BotA/services/bota-supervisor/run
```

Both now contain the same executable non-mutating scheduler.

## Control-plane acceptance

After restarting only `bota-supervisor`, the phone reported:

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

All seven required components were owned by manager PID `10341`:

- bota-updater
- bota-watcher
- bota-closer
- bota-shadow
- bota-heartbeat
- bota-supervisor
- crond

The supervisor wrapper no longer probes for or starts `runsvdir`, `runsv`, or
individual services. Automatic topology mutation from this wrapper is closed.

## Preserved scope

P7 did not change:

- heartbeat scripts or service wrapper;
- crontab;
- strategy, thresholds, pairs, scoring, ADX, H1/D1 rules, deduplication, or
  SL/TP;
- provider, Telegram, or Supabase semantics;
- remote phone branch state.

Backup:

```text
~/bota-phone-preserve-20260802T210517Z/p7-supervisor-wrapper-20260802T230646Z
```

## Remaining runtime gap

The only remaining reconciliation item from this sequence is heartbeat topology:

```text
active phone: services/bota-heartbeat/run -> tools/bota_heartbeat_utc.sh
GitHub repair: tools/heartbeat.sh -> tools/heartbeat_delivery.py
```

The active phone wrapper owns authoritative UTC bucketing plus deadman/recovery
behavior, while the GitHub controller provides locking and bounded monotonic
retry backoff. Reconciliation must preserve deadman semantics and produce one
active delivery controller.
