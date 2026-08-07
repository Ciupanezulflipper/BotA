# Duplicate Manager Runtime Transition — 2026-08-07

Status: FORENSIC EVIDENCE CAPTURED
Branch: `forensics/duplicate-manager-provenance-20260807`
Runtime mutation by collector: NO

## Confirmed observations

1. Earlier in the same runtime investigation, PID 16360 was the active BotA `runsvdir` manager:
   - argv: `/data/data/com.termux/files/usr/bin/runsvdir -P /data/data/com.termux/files/usr/var/service`
   - all required BotA `runsv` children had PPID 16360.

2. PID 31140 was created as a second `runsvdir` instance:
   - argv: `/data/data/com.termux/files/usr/bin/runsvdir /data/data/com.termux/files/usr/var/service`
   - cwd: `/data/data/com.termux/files/usr`
   - PPID: 1
   - the command form matches the packaged Termux `service-daemon` launch path, which invokes `runsvdir` without `-P`.

3. `/data/data/com.termux/files/usr/var/run/service-daemon.pid` contained `31140`.

4. The forensic collector measured:
   - PID 31140 estimated process start epoch: `1786117138.0485427`
   - pidfile mtime epoch: `1786117138.0449927`
   - difference: `-0.0035500526428222656` seconds.

   This is strong temporal evidence that creation of PID 31140 and writing of `service-daemon.pid` occurred as the same service-daemon start operation.

5. During the later provenance collector execution, PID 16360 was no longer alive.

6. At that same later sample:
   - only PID 31140 remained as a `runsvdir` manager;
   - all previously manager-owned `runsv` processes were still alive but had PPID 1;
   - the BotA required services therefore became orphaned at the process-parentage level after PID 16360 exited;
   - no watchdog process was running;
   - no migration process was running;
   - the watchdog lock file had no holder.

7. The collector safety record reported:
   - `mutation_performed=false`
   - `files_written=false`
   - `pidfile_changed=false`
   - `services_restarted=false`
   - `signals_sent=false`

## Current forensic interpretation

The evidence now separates two faults:

- duplicate native manager creation: PID 31140 was created by the packaged Termux `service-daemon` path and its pidfile was written essentially simultaneously with process creation;
- active manager loss: PID 16360 subsequently exited, leaving the existing `runsv` supervisors orphaned under PID 1 while PID 31140 remained alive but had not acquired those existing supervisors.

The exact actor or mechanism that caused PID 16360 to exit is not yet proven. No claim is made beyond the recorded evidence.

## Next forensic question

Identify the event immediately surrounding PID 16360 disappearance: signal delivery, terminal/session lifecycle, Android process reparent/termination behavior, explicit migration/cleanup command, or another launcher/runtime path.

Do not terminate PID 31140 or mutate `service-daemon.pid` until that attribution step is complete.
