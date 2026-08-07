# BotA Current Continuity State

Last updated: 2026-08-07 17:15 UTC

## Authoritative identifiers

```text
HEARTBEAT_CODE_BASELINE=4b89d1e0c729b81472ca78d723316289dd4aebb1
PHONE_BRANCH=deploy/repaired-core-20260802T215531Z
PHONE_HEAD=011baaaad7071110e33bca06903047c842e7331a
PHONE_REMOTE_PUSHED=NO
PHONE_PRESERVATION_ROOT=~/bota-phone-preserve-20260802T210517Z
PHONE_UNTRACKED_FILES_PRESERVED=519
P8_BACKUP=~/bota-phone-preserve-20260802T210517Z/p8-unified-heartbeat-20260803T001345Z
```

## Scope lock

Do not change strategy, thresholds, pairs, scoring, ADX, H1/D1 confirmation,
volatility or macro filters, deduplication, SL/TP, PR #7, provider semantics, or
Supabase signal semantics during runtime-reliability work.

Never push directly to `main`. Use a branch and reviewable commit history.

## Current live control-plane incident — 2026-08-07

The previously healthy one-manager state is no longer current. Direct phone
forensics now prove two matching `runsvdir` managers:

```text
PID 16360
CMDLINE=/data/data/com.termux/files/usr/bin/runsvdir -P /data/data/com.termux/files/usr/var/service
CWD=/data/data/com.termux/files/home/BotA
PPID=1
ROLE=active owner

PID 31140
CMDLINE=/data/data/com.termux/files/usr/bin/runsvdir /data/data/com.termux/files/usr/var/service
CWD=/data/data/com.termux/files/usr
PPID=1
ROLE=duplicate idle native manager
```

The installed Termux `service-daemon` launches `runsvdir` without `-P` and writes
`$PREFIX/var/run/service-daemon.pid`. The live pidfile contains `31140` and its
mtime is:

```text
2026-08-07 11:38:58.044992610 -0400
```

This exactly fingerprints PID 31140 as a manager launched through native Termux
`service-daemon` semantics.

All observed required BotA `runsv` children are owned by PID 16360:

```text
bota-updater   runsv=16368 owner=16360
bota-watcher   runsv=16493 owner=16360
bota-closer    runsv=16694 owner=16360
bota-shadow    runsv=17529 owner=16360
bota-heartbeat runsv=17998 owner=16360
bota-supervisor runsv=18309 owner=16360
crond          runsv=18724 owner=16360
```

Additional Termux services `sshd` and `ssh-agent` are also owned by PID 16360.
PID 31140 owns zero observed `runsv` children.

Precise verdict:

```text
SEVEN_SERVICE_OWNERSHIP_SPLIT=NO
MANAGER_COUNT=2
ACTIVE_MANAGER_PID=16360
ACTIVE_MANAGER_FORM=runsvdir -P
ACTIVE_MANAGER_REQUIRED_OWNERSHIP=7/7
DUPLICATE_MANAGER_PID=31140
DUPLICATE_MANAGER_FORM=runsvdir without -P
DUPLICATE_MANAGER_REQUIRED_OWNERSHIP=0/7
PIDFILE_CONTENT=31140
PIDFILE_MATCHES_ACTIVE_OWNER=NO
CONTROL_PLANE_HEALTHY=NO
CREATOR_OF_PID_31140=NOT_YET_PROVEN
```

`tools/control_plane_status.py` reports `manager_pid=null` and `owned=0/7`
because it deliberately refuses to nominate a canonical manager when
`manager_count != 1`. That output is therefore consistent with the direct PPID
evidence; it is not evidence of a seven-service ownership split.

## Repository implementation evidence

Current repository code contains two distinct manager-launch fingerprints:

```text
tools/runsvdir_guard.py
  -> runsvdir -P <service-root>

tools/native_service_daemon_watchdog.py
  -> service-daemon start
  -> runsvdir <service-root>
```

Current watchdog code fails closed on `manager_count > 1`. Current migration
code also fails preflight on `manager_count > 1`; when migrating from one
legacy detached `-P` manager it is designed to terminate that manager and wait
for exit before starting the native manager. Therefore the present two-manager
state is inconsistent with the intended current steady state and requires
historical provenance attribution.

Dedicated evidence record:

- `audits/DUPLICATE_MANAGER_FORENSICS_2026-08-07.md`

## Previously deployed and accepted state

The following was verified on 2026-08-02/03 and remains valid historical
evidence, but must not be described as the current live control-plane state:

```text
D1 mapping=1440
supervisor core=PASS
supervisor wrapper=non-mutating PASS
status formatter=PASS
autostatus=PASS
unified heartbeat topology=DEPLOYED
heartbeat delivery=PASS
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
  deploy: apply repaired non-heartbeat runtime core

dbdb1b1f9e2e1a6d66bb94b8eda4d1cf40617d20
  deploy: activate non-mutating supervisor wrapper

011baaaad7071110e33bca06903047c842e7331a
  deploy: activate unified heartbeat runtime
```

## P8 heartbeat deployment

The active path was deployed as:

```text
services/bota-heartbeat/run
  -> tools/heartbeat.sh
  -> tools/heartbeat_runtime.py
  -> tools/heartbeat_delivery.py
```

P8 replaced the four repository files plus the separate active wrapper,
restarted only `bota-heartbeat`, and verified that only the heartbeat wrapper PID
changed. The legacy `tools/bota_heartbeat_utc.sh` was preserved unchanged.

Fresh markers from that deployment:

```text
[RUNIT bota-heartbeat 2026-08-03T00:13:49Z] SERVICE_START pid=7453 interval_sec=60 mutation=disabled
[2026-08-03 00:13:59 UTC] HB_UTC_RESULT=PASS sources=3
[2026-08-03 00:13:59 UTC] DEADMAN_UTC_RESULT=MONOTONIC_PROGRESS_INVALID
```

Historical P8 verdict:

```text
P8_UNIFIED_HEARTBEAT_DEPLOYMENT=PASS
HEARTBEAT_TOPOLOGY=DEPLOYED
HEARTBEAT_DELIVERY=PASS
AUTHORITATIVE_UTC=PASS_3_SOURCES
CONTROL_PLANE=HEALTHY_7_OF_7_AT_VALIDATION_TIME
DEADMAN_INPUT_ACCEPTANCE=FAIL
```

The deadman defect remains separately unresolved unless later evidence proves it
closed. Do not conflate that defect with the 2026-08-07 duplicate-manager
incident.

## Historical status

The August 1 endurance validation remains failed historical evidence. A new
endurance-validation pass has not yet been completed.

Two documentation-only direct-main commits occurred while recording P8. They are
recorded in `audits/P8_DIRECT_MAIN_DOC_EXCEPTION_2026-08-03.md`. No runtime code
or phone state was changed by those documentation commits, but the process rule
was violated and must not be repeated.

## Evidence

- `audits/DUPLICATE_MANAGER_FORENSICS_2026-08-07.md`
- `audits/P8_HEARTBEAT_PHONE_DEPLOYMENT_2026-08-03.md`
- `audits/PR39_HEARTBEAT_RECONCILIATION_2026-08-03.md`
- `audits/P7_SUPERVISOR_WRAPPER_CLOSURE_2026-08-02.md`
- `audits/PHONE_DEPLOYMENT_2026-08-02.md`
- `audits/INCIDENT_2026-08-01_VALIDATION_FAILURE.md`
- `audits/ERROR_LOG.md`
- `ERRORS.md`
- GitHub issue #9

## Exactly one next action

Perform a read-only historical provenance correlation around the pidfile mtime
`2026-08-07 11:38:58 -0400` and PID 31140 process start time. Correlate
`/proc/31140/stat`, boot time, native watchdog JSONL/launch logs,
migration/finalizer audit directories, `~/.termux/boot/*`, Termux service startup
profile scripts, repository launchers, shell history where available, and any
Tasker/RunCommand traces available locally.

Do not kill either manager, rewrite the pidfile, or restart services until the
creator of PID 31140 is attributed or the remaining ambiguity is explicitly
accepted through a separate controlled recovery plan.
