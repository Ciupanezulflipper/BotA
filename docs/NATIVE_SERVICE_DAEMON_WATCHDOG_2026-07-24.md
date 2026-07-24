# Native Termux service-daemon watchdog

## Decision

BotA will use one manager authority only: Termux's installed `service-daemon`,
which owns `$PREFIX/var/run/service-daemon.pid` and starts the standard
`runsvdir $PREFIX/var/service` tree.

The watchdog never launches `runsvdir` directly and never kills duplicate
managers automatically.

## Behavior

- One native manager with seven healthy services: no mutation.
- No manager: remove only a proven-dead numeric PID file, invoke
  `service-daemon start`, then require its PID file to match the sole manager.
- Multiple managers: fail closed.
- Sole manager missing or mismatching the native PID file: fail closed.
- PID 1 orphaned supervisors: hand off one service at a time through bounded
  `sv down` and `sv exit` operations.
- Manager-owned down service: bounded `sv up`.
- Final acceptance: one native manager, seven manager-owned supervisors,
  seven running wrappers, zero orphans, zero invalid rows, zero duplicates.

## Scope lock

No strategy, thresholds, pairs, timeframes, scoring, SL/TP, provider selection,
Telegram semantics, Supabase semantics, or signal lifecycle changes.

## Deployment boundary

This branch does not mutate the phone. Migration from the current detached
manager to the native manager requires a separate short, hash-pinned,
rollback-backed deployment after CI and review pass.
