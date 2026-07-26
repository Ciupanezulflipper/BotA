# BotA Current Continuity State

Last updated: 2026-07-26

This is the compact current handoff. Historical detail remains in `CONTINUITY.md`, `ERRORS.md`, `audits/ERROR_LOG.md`, the Phase 4/5 incident records, and issue #9.

## Operating rules

- Reliability and observability only. Strategy, thresholds, pairs, scoring, SL/TP, filters, PR #7, DeepSource, and Supabase signal semantics remain frozen.
- No direct push to `main`.
- Every Termux package displays `audits/ERROR_LOG.md`, runs in a bounded child script, preserves the parent shell, and ends with exactly one next action.
- Read-only packages answer one narrow question.
- Mutating recovery requires fresh topology validation, backup, rollback, explicit approval, and independent verification.
- Never depend on `/proc/uptime` on this Android build.
- Trusted server/provider UTC controls market semantics; monotonic time controls same-boot cadence and health; Android/ship wall time is display-only.

## Native service-manager migration: complete

The migration from the legacy boot guard to the native `service-daemon` manager and watchdog is complete.

Repository milestones:

```text
PR #18 MERGED=ef94e4fd1c9a7a786f7514024828fbdfc1146143
PR #19 MERGED=12000f04137a000cb3d1c6bf7acb45da288907c9
PR #20 MERGED=87e43ce76d43d625e7e9c7a6715cabb59f4b65c9
PR #21 MERGED=09a1bd5b57e0bf3a39e79afc827d14e09e8b1031
PR #22 MERGED=0694e17c09c3c8663622dce745d8b449c3cd2405
```

PR #22 made the partial migration journaled, resumable, and fail-closed after interruption. The phone had already reconverged to a fully owned native state, so the partial executor correctly rejected that source topology and rolled files back. The fully-owned finalizer from PR #20 was then used instead.

## Final verified runtime topology

Finalization evidence:

```text
FINALIZER_SOURCE_STATE=native_manager_fully_owned_no_watchdog
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
FINALIZATION_PACKAGE=PASS
```

A later read-only stability check after normal service cycles independently returned:

```text
CONTROL_PLANE_GATE=PASS
STABILITY_CHECK=PASS
STABILITY_WRAPPER_EXIT_CODE=0
RUNTIME_MUTATION_PERFORMED=NO
```

All seven required services had exactly one `runsv` supervisor owned by the native manager:

- `bota-updater`
- `bota-watcher`
- `bota-closer`
- `bota-shadow`
- `bota-heartbeat`
- `bota-supervisor`
- `crond`

## Current repository/runtime distinction

The phone checkout remains on operational branch `ops/ship-time-independent-runtime-20260717`, HEAD `c9ab9996190025ab51202b1f6508a05f8fc148c3`, with a dirty worktree. That repository housekeeping is separate from the verified runtime control-plane closure and must not be overwritten casually.

## What remains

The infrastructure migration is closed. Do not rerun either migration executor or the finalizer while the verified topology remains healthy.

The next meaningful proof is market-session behavior:

1. wait for Monday/open-market watcher cycles;
2. verify fresh updater and watcher progress using active logs only;
3. classify each cycle as normal HOLD/rejection, eligible signal, send failure, or infrastructure failure;
4. when the next real signal becomes ACTIVE, verify Telegram delivery, Supabase persistence, closer execution, and transition to CLOSED/CANCELLED with result pips.

Do not change ADX, scoring thresholds, pair scope, filters, SL/TP, or dedup merely because Monday produces no signal. A healthy rejected HOLD is valid runtime behavior.

## Exactly one next action

On Monday after at least one verified open-market cycle, run one compact read-only watcher-cycle proof. Inspect strategy only if the infrastructure path passes and the recorded decision evidence is internally inconsistent.