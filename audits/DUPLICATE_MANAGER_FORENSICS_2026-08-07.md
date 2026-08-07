# BotA Duplicate Manager Forensics — 2026-08-07

Status: ACTIVE FORENSIC INVESTIGATION

Scope: runtime control-plane reliability only. No strategy, provider, Supabase, signal, threshold, or trade-behavior mutation is authorized by this record.

## Executive finding

The live phone is not in a seven-service ownership split. It is in a duplicate-manager state with one active legacy/detached manager that owns all observed `runsv` children and one later native Termux `service-daemon` manager that owns none of them.

Observed live managers:

```text
PID 16360
CMDLINE=/data/data/com.termux/files/usr/bin/runsvdir -P /data/data/com.termux/files/usr/var/service
CWD=/data/data/com.termux/files/home/BotA
EXE=/data/data/com.termux/files/usr/bin/runsvdir
PPid=1
ROLE=active owner of all observed service runsv children

PID 31140
CMDLINE=/data/data/com.termux/files/usr/bin/runsvdir /data/data/com.termux/files/usr/var/service
CWD=/data/data/com.termux/files/usr
EXE=/data/data/com.termux/files/usr/bin/runsvdir
PPid=1
ROLE=duplicate idle manager with zero observed runsv children
```

## Live pidfile evidence

```text
PATH=/data/data/com.termux/files/usr/var/run/service-daemon.pid
CONTENT=31140
MODIFY=2026-08-07 11:38:58.044992610 -0400
CHANGE=2026-08-07 11:38:58.044992610 -0400
MODE=0644
```

The pidfile points to the idle/native manager rather than the active owner.

## Installed Termux service-daemon fingerprint

The installed executable is a shell script at:

```text
/data/data/com.termux/files/usr/bin/service-daemon
```

Its start path is:

```sh
start-stop-daemon -S -b -m -p $PIDFILE -x $DAEMON -d $PREFIX -- $DAEMON_OPTS
```

with:

```text
NAME=service-daemon
PIDFILE=$PREFIX/var/run/service-daemon.pid
DAEMON=$PREFIX/bin/runsvdir
DAEMON_OPTS=$SVDIR
```

Therefore a manager started through this native wrapper has the fingerprint:

```text
runsvdir /data/data/com.termux/files/usr/var/service
```

without `-P`, and the wrapper writes `service-daemon.pid`. This exactly matches PID 31140 and the current pidfile.

## Active manager fingerprint

Repository code in `tools/runsvdir_guard.py` launches:

```text
runsvdir -P /data/data/com.termux/files/usr/var/service
```

This exactly matches PID 16360.

## Current child ownership

The observed `runsv` rows all have PPID 16360:

```text
16368 -> bota-updater
16493 -> bota-watcher
16694 -> bota-closer
17529 -> bota-shadow
17998 -> bota-heartbeat
18309 -> bota-supervisor
18724 -> crond
29562 -> sshd
29563 -> ssh-agent
```

For BotA's required seven services:

```text
RUNNING=7/7
ACTIVE_OWNER_MANAGER=16360
NATIVE_PIDFILE_MANAGER=31140
REQUIRED_RUNSV_OWNED_BY_16360=7/7
REQUIRED_RUNSV_OWNED_BY_31140=0/7
```

## Why `control_plane_status.py` reports `owned=0`

The status tool deliberately refuses to nominate a canonical manager when more than one matching `runsvdir` manager exists. With `manager_count=2`, `manager_pid` is `null`; every service is consequently classified `owner=other_or_missing` even though each service row exposes `runsv_ppid=16360`.

Observed status:

```text
manager_count=2
manager_pid=null
required=7
running=7
owned=0
orphaned=0
duplicate_service_rows=0
healthy=false
failure_reasons=[manager_count:2, owned:0/7]
```

This is expected behavior for an ambiguous control plane, not proof that the seven services lack a live owner.

## GitHub implementation evidence

Current repository implementation contains two distinct manager creation mechanisms:

1. `tools/runsvdir_guard.py` launches `runsvdir -P .../var/service`.
2. `tools/native_service_daemon_watchdog.py` can execute `service-daemon start` when it observes zero matching managers.
3. `tools/native_service_daemon_migration.py` can execute `service-daemon start` as part of the migration cutover.
4. `tools/start_native_service_daemon_watchdog.sh` launches the native watchdog detached from the shell and passes `$PREFIX/bin/service-daemon` explicitly.

The current watchdog implementation fails closed when `manager_count > 1`; it does not intentionally start a third manager from the already-duplicated state.

The current migration implementation also fails preflight when `manager_count > 1`. For a single detached `-P` manager, it is designed to SIGTERM that manager and wait for its exit before starting the native service-daemon manager.

Therefore the current two-manager live state is inconsistent with the intended steady-state behavior of the current code and requires historical provenance attribution.

## Historical repository timeline

Relevant repository commits include:

```text
c32af4250d655b48d163fac002a80610d25adb8c
fix: use native Termux service-daemon as sole manager
2026-07-23

a2cabf38842b57010bcbf9e9190e0e3ece3492b2
fix: migrate exact zero-manager orphan topology
2026-07-25

a18f7bfeaa267d25c85ad6fd38053231c1cd64d9
fix: use packaged Termux service-daemon path
2026-07-25

a6717f8c74bd005e93c2e8584037ae9ee448f35f
fix: use installed Termux service-daemon path
2026-07-25

09a1bd5b57e0bf3a39e79afc827d14e09e8b1031
merge PR #21 for installed Termux service-daemon path
2026-07-25
```

## External Termux behavior relevant to attribution

Termux:Boot executes scripts placed under `~/.termux/boot/` in sorted order. Its official example for termux-services sources `$PREFIX/etc/profile.d/start-services.sh`. Any boot script, profile script, Tasker/RunCommand invocation, shell action, migration/finalizer, or watchdog launch that executes native `service-daemon start` is therefore a plausible creator class and must be ruled in or out with direct evidence.

## Current forensic verdict

```text
SEVEN_SERVICE_OWNERSHIP_SPLIT=NO
ACTIVE_MANAGER_PID=16360
ACTIVE_MANAGER_FORM=runsvdir -P
ACTIVE_MANAGER_REQUIRED_OWNERSHIP=7/7
DUPLICATE_MANAGER_PID=31140
DUPLICATE_MANAGER_FORM=runsvdir without -P
DUPLICATE_MANAGER_REQUIRED_OWNERSHIP=0/7
PIDFILE_CONTENT=31140
PIDFILE_MANAGER_MATCHES_ACTIVE_OWNER=NO
PID_31140_NATIVE_SERVICE_DAEMON_FINGERPRINT=PASS
CURRENT_CODE_INTENTIONALLY_SUPPORTS_TWO_MANAGER_STEADY_STATE=NO
CREATOR_OF_PID_31140=NOT_YET_PROVEN
```

## Safety decision

Do not kill PID 16360 or PID 31140 yet. Do not rewrite or delete `service-daemon.pid` yet. Do not restart services yet. The active owner is PID 16360; terminating it before a controlled handoff could disturb all seven required BotA services.

## Exactly one next action

Perform a read-only historical provenance correlation around the pidfile modification time `2026-08-07 11:38:58 -0400` and the process start time of PID 31140. Correlate:

- `/proc/31140/stat` start ticks and boot time
- native watchdog JSONL and launch logs
- migration/finalizer audit directories and result JSON
- `~/.termux/boot/*`
- `$PREFIX/etc/profile.d/*start*service*`
- repository and shell-visible launch scripts
- shell history where available
- any Tasker/RunCommand traces available locally
- file mtimes of launchers and pidfile

The next mutation decision must be based on that evidence. If creator attribution remains ambiguous, fail closed and do not terminate either manager.
