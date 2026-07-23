# Durable Termux runsvdir guard

## Problem proven on the production phone

The standard `runsvdir` manager repeatedly exited or was killed while its seven
BotA `runsv` children survived under PID 1. A manual V5 reconciliation restored
`OWNED=7/7`, but a later deployment gate again found `OWNED=0/7` and
`ORPHANED=7` under a newly started manager.

This means V5 repaired the split tree correctly but did not repair the durable
manager-survival failure.

## Guard design

`tools/runsvdir_guard.py` is a single-instance, boot-relative recovery loop.
It:

- holds an exclusive process-lifetime file lock;
- requests a Termux wake lock on a best-effort basis;
- recognizes exactly one standard manager for `$PREFIX/var/service`;
- starts a detached `runsvdir -P` manager only when none exists;
- refuses to mutate when more than one manager or duplicate service supervisors
  exist;
- hands off only the seven required BotA/crond supervisors that are proven PID 1
  orphans;
- requires manager ownership and a running service after every handoff;
- records append-only boot ID and monotonic-time events.

`tools/start_runsvdir_guard.sh` launches the guard with `nohup` and `setsid` when
available so it is not tied to the interactive Termux shell.

## Runtime boundary

This repository change does not alter the phone by itself. Deployment must:

1. install both guard files from a reviewed commit;
2. back up the canonical `~/.termux/boot/00-termux-services.sh`;
3. change only that canonical boot entry to call
   `tools/start_runsvdir_guard.sh`;
4. start the guard once;
5. verify one guard process, one manager, seven manager-owned supervisors,
   seven running services, zero orphans, and one supervised `crond -n -s`;
6. deliberately terminate only the manager once and prove the guard restores
   the exact healthy topology before PR #11 runtime deployment continues.

No strategy, scoring, pair, timeframe, threshold, SL/TP, risk, dedup, or signal
semantics are changed.

## Rollback

Stop the guard process, restore the backed-up canonical boot file, remove the two
guard files, and run the existing V5 reconciliation once if supervisor ownership
is split. Verify the exact seven-service topology independently afterward.
