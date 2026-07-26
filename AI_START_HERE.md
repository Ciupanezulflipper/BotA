# BotA AI Start Here

Last updated: 2026-07-26

Read this before proposing BotA commands, code, cron, service, strategy, or deployment changes.

## Evidence and scope rules

Classify material claims as VERIFIED, ASSUMED, or UNKNOWN. Do not promote a failed acceptance criterion because adjacent behavior worked, and do not fail a healthy recovery because process IDs changed.

The native service-manager migration is complete. Current work is open-market watcher and signal-path observation only. Do not change strategy, thresholds, pairs, scoring, SL/TP, filters, PR #7, DeepSource, Supabase signal semantics, or `main` directly.

Every Termux package must:

1. display `$HOME/BotA/audits/ERROR_LOG.md`;
2. run strict options only inside a bounded child script;
3. preserve the interactive parent shell;
4. use compact active-path checks;
5. avoid supervise FIFOs and broad historical scans;
6. revalidate exact targets immediately before mutation;
7. separate backup, rollback, mutation, and independent verification;
8. end with exactly one next action.

Additional mandatory rules:

- do not use `/proc/uptime` on this Android build;
- changed PIDs are restart events, not failures by themselves;
- use trusted server/provider UTC for market semantics;
- use monotonic time for same-boot cadence and health;
- Android/ship wall time is display-only;
- read-only packages answer one narrow question;
- never combine infrastructure, watcher logs, CSV, cache JSON, Telegram history, and strategy conclusions in one package;
- `supervise/pid` identifies the supervised service process, not the `runsv` supervisor;
- resolve ownership through service PID -> PPID -> `runsv`, then validate command, state, PPID, and cwd;
- a normal rejected HOLD is not an infrastructure failure.

## Current verified control plane

```text
MANAGER_COUNT=1
MANAGER_PID=22175
PIDFILE_VALUE=22175
OWNED=7/7
RUNNING=7/7
ORPHANED=0
INVALID=0
DUPLICATES=0
DOWN_SERVICES=NONE
WATCHDOG_COUNT=1
WATCHDOG_PID=8752
WATCHDOG_LOCK_HOLDERS=8752
BOOT_LEGACY_COUNT=0
BOOT_WATCHDOG_COUNT=1
ACTIVE_MIGRATION_JOURNAL=ABSENT
CONTROL_PLANE_GATE=PASS
STABILITY_CHECK=PASS
```

All seven required services have exactly one native-manager-owned supervisor: updater, watcher, closer, shadow, heartbeat, supervisor, and crond.

## Migration closure

PRs #18 through #22 are merged. Final relevant merge:

```text
PR #22=0694e17c09c3c8663622dce745d8b449c3cd2405
```

The partial migration executor correctly rejected an already fully owned `7/7` source state and rolled files back. The fully-owned finalizer then replaced the legacy boot launcher and started exactly one watchdog without restarting or reconciling the healthy manager/service tree.

Do not rerun the migration executors or finalizer while the control-plane gate remains healthy.

## Repository caution

The phone checkout remains on:

```text
BRANCH=ops/ship-time-independent-runtime-20260717
HEAD=c9ab9996190025ab51202b1f6508a05f8fc148c3
WORKTREE_DIRTY=YES
```

Do not reset, checkout, merge, or overwrite this worktree without first identifying and preserving every local change.

## Next proof: Monday/open market

After at least one verified open-market cycle, inspect only current active evidence and determine:

1. updater produced fresh data;
2. watcher completed the expected EURUSD/GBPUSD M15 cycle;
3. the decision was persisted before dedup;
4. the outcome was a valid HOLD/rejection, eligible signal, send failure, or infrastructure failure;
5. if a signal becomes ACTIVE, Telegram, Supabase, and closer lifecycle complete correctly.

Do not loosen ADX, score, H1/D1, volatility, macro, session, or dedup gates merely to manufacture signals.

## Files to read

- `CONTINUITY_CURRENT.md`
- `audits/ERROR_LOG.md`
- `ERRORS.md`
- `CONTINUITY.md`
- GitHub issue #9
- PRs #18 through #22

## Exactly one next action

On Monday after an open-market watcher cycle, run one compact read-only cycle proof. Stop if the control-plane gate fails; otherwise classify the watcher decision from current evidence before considering any code or strategy change.