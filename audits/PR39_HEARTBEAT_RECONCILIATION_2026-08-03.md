# PR39 Heartbeat Reconciliation — 2026-08-03

## Repository result

PR #39 merged into `main` as:

```text
4b89d1e0c729b81472ca78d723316289dd4aebb1
```

The PR replaced the split GitHub heartbeat architecture with one unified runtime
controller while preserving the production phone's required UTC and deadman
semantics.

## Merged files

```text
services/bota-heartbeat/run
tools/heartbeat.sh
tools/heartbeat_runtime.py
tests/test_heartbeat_runtime_policy.py
```

The unified runtime reuses the existing:

```text
tools/heartbeat_delivery.py
```

## Merged execution path

```text
services/bota-heartbeat/run
  -> tools/heartbeat.sh
  -> tools/heartbeat_runtime.py
  -> tools/heartbeat_delivery.py
```

## Preserved behavior

- authoritative server UTC controls the hourly heartbeat bucket;
- monotonic same-boot age controls deadman detection;
- deadman alert delivery is preserved;
- recovery delivery is preserved;
- a successful alert creates the deadman flag;
- a successful recovery removes the deadman flag;
- the legacy phone script is not deleted by this repository change.

## Added reliability controls

- one non-blocking file lock for each runtime cycle;
- atomic state and marker writes;
- bounded Telegram timeout and response parsing;
- bounded exponential retry after delivery failure;
- distinct persisted delivery state for heartbeat, deadman, and recovery;
- boot-aware monotonic state reset;
- fixed HTTPS clock hosts only;
- no file, FTP, or arbitrary URL scheme opening;
- no service, crontab, strategy, provider, or Supabase mutation.

## Review evidence

```text
DeepSource Python=PASS
DeepSource Shell=PASS
DeepSource Secrets=PASS
CodeRabbit production implementation review=PASS
all analyzer review threads resolved=YES
```

The final commit changed only test fixture assertions after the production code
review. DeepSource remained green on the final head.

## Isolated phone test evidence

The PR head was tested in a detached temporary worktree. The live phone branch,
HEAD, services, Telegram, providers, and runtime state were not changed.

```text
heartbeat_delivery test count=18
heartbeat_delivery result=PASS
heartbeat_runtime test count=8
heartbeat_runtime result=PASS
shell syntax=PASS
python compile=PASS
service file mode=100755
live runtime mutation=NO
service restart=NO
Telegram call=NO
provider call=NO
```

One initial test failed because it evaluated `Path.exists()` after
`TemporaryDirectory` cleanup. Production behavior had already emitted
`DEADMAN_UTC_RESULT=ALERT_SENT`. The test was corrected to capture flag state
before fixture cleanup. The recovery test was corrected at the same time so it
could not pass merely because the temporary directory had been deleted.

Final tested PR head:

```text
b55b997cc3fc2a5275ec91a95496dce06b913c5e
```

## Phone deployment state

At the time of this record, the phone remains at:

```text
PHONE_BRANCH=deploy/repaired-core-20260802T215531Z
PHONE_HEAD=dbdb1b1f9e2e1a6d66bb94b8eda4d1cf40617d20
```

The active phone heartbeat path remains:

```text
services/bota-heartbeat/run -> tools/bota_heartbeat_utc.sh
```

Therefore the repository fix is merged and tested, but the phone deployment is
not yet complete.

## Required next package

Deploy exactly these GitHub files:

```text
services/bota-heartbeat/run
tools/heartbeat.sh
tools/heartbeat_runtime.py
tools/heartbeat_delivery.py
```

Also replace the separate active wrapper copy:

```text
~/.config/bota-sv/bota-heartbeat/run
```

Restart only `bota-heartbeat`, then verify:

```text
manager_count=1
required=7
owned=7
running=7
orphaned=0
heartbeat service=run
HB_UTC_RESULT marker present
DEADMAN_UTC_RESULT marker present
```

Do not remove `tools/bota_heartbeat_utc.sh` until the unified runtime is accepted
on the phone. Do not change crontab, providers, strategy, Supabase, or any other
service in the deployment package.
