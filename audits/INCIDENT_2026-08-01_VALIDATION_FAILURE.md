# BotA Production Validation Failure — 2026-08-01

## Status

```text
INCIDENT_STATUS=OPEN
PRODUCTION_VALIDATION=FAILED
FINAL_ROLLBACK_CONTROL_PLANE=PASS_AT_RECORDED_TIMESTAMP
AUTOMATIC_TOPOLOGY_RECOVERY=DISABLED
CURRENT_PHONE_TOPOLOGY=UNKNOWN_UNTIL_FRESH_NARROW_PROOF
```

The one-week production validation did not pass.

BotA remained capable of fetching data, calculating decisions, and delivering at
least one eligible GBPUSD M15 signal. That functional evidence does not override
failures in runtime ownership, recovery safety, deployment consistency,
provider-budget accounting, and notification correctness.

## Scope

This incident concerns:

- Termux/runit control-plane ownership;
- automatic recovery and boot behavior;
- repository/runtime divergence;
- canonical scheduling verification;
- provider-budget and data-validation reliability;
- Telegram/status correctness;
- production-validation acceptance.

It does not authorize strategy, threshold, scoring, pair, ADX, H1/D1 rule,
volatility, macro, dedup, SL/TP, PR #7, or Supabase signal-semantic changes.

## Verified runtime evidence

During the validation period:

- the control plane reached one `runsvdir` manager while all seven required
  `runsv` supervisors were reparented to PID 1;
- the measured degraded state was:

```text
owned=0/7
running=7/7
orphaned=7
```

- a later one-shot reconciliation restored:

```text
manager_count=1
owned=7/7
running=7/7
orphaned=0
```

- required service counts temporarily fell below seven;
- canonical crontab verification failed;
- the phone checkout and GitHub `main` were not synchronized;
- repository documentation described a watchdog configuration that did not
  match the phone.

The exact root cause of every manager/service transition was not proven. Android
process management, Termux lifecycle, guard behavior, explicit restarts, and
resource pressure must not be presented as proven causes without direct evidence.

## Automatic-recovery incident

The configured native service-daemon watchdog startup path could not run because
the referenced service-daemon executable was unavailable on the phone.

A continuous `runsvdir` guard was then started. Repeated Termux restarts occurred
while that continuous guard was active.

This establishes an unsafe association requiring rollback. It does not by itself
prove the precise Android/Termux restart mechanism.

The continuous guard and watchdog were stopped.

The production boot launcher was replaced with a safe launcher that starts the
standard Termux service tree but intentionally does not start an automatic
topology-recovery process.

## Final rollback verification

The recorded final rollback state was:

```text
manager_count=1
owned=7/7
running=7/7
orphaned=0
control_plane_rc=0
automatic_recovery=disabled
```

Interpretation:

- the rollback restored a healthy control plane at the recorded timestamp;
- automatic topology recovery was intentionally disabled;
- the incident remains open because endurance, recurrence prevention, repository
  convergence, and production revalidation are not complete;
- the current phone topology must not be inferred from this historical snapshot.

## Repository incident

PR #24 began as a three-file preservation PR based on an older phone checkout.
It later expanded to seven commits and thirty-two changed files, diverged heavily
from current `main`, became non-mergeable, and mixed unrelated concerns.

PR #24 is not a valid repair or deployment vehicle.

It must be closed or retained only as a historical preservation artifact. Any
salvageable behavior must be reapplied from current `main` in narrow clean
branches with complete-file replacements and focused tests.

## August 2 read-only discovery

The latest supplied discovery ended with:

```text
LOCAL_STATUS_DATA_DISCOVERY_COMPLETE=YES
RUNTIME_MUTATION_PERFORMED=NO
GIT_CHANGED=NO
```

No broad rediscovery is required.

The supplied cache evidence exposed an explicit unresolved defect:

```text
cache/indicators_EURUSD_D1.json
pair=EURUSD
timeframe=D1
tf_ok=false
tf_actual_min=0.0
weak=true
error=tf_mismatch
ema9=0.0
ema21=0.0
atr=0.0
```

Weekend age of intraday candles is not automatically a failure. The explicit D1
mismatch must be reproduced through the active provider fetch, cache writer, and
indicator builder before any strategy or missed-signal conclusion.

## Acceptance failures

The validation failed the following gates:

1. **Control-plane endurance** — ownership regressed during production operation.
2. **Automatic recovery safety** — the configured watchdog path was unavailable,
   and the continuous guard was associated with repeated Termux restarts.
3. **Repository/runtime convergence** — phone and GitHub state diverged.
4. **Canonical scheduling** — crontab verification failed.
5. **Data integrity** — at least one explicit D1 timeframe mismatch remained.
6. **Provider-budget accounting** — provider calls and status-related calls were
   not sufficiently reconciled for production acceptance.
7. **Notification correctness** — status messaging and executable signal meaning
   were not sufficiently isolated for production acceptance.

Passing adjacent behavior does not convert these failed gates into PASS.

## Prohibited actions until repaired

- Do not merge or deploy PR #24.
- Do not rerun the old migration executor, finalizer, watchdog, or continuous
  guard from stale documentation.
- Do not re-enable automatic topology recovery without a bounded redesign,
  failure-injection tests, backoff, locking, kill switch, and restart observation.
- Do not reset, checkout, pull, merge, or overwrite the phone worktree before
  every local change is preserved and classified.
- Do not repeat broad process/log/cache discovery.
- Do not change strategy to compensate for invalid or stale data.

## Repair sequence

1. Correct canonical repository truth and quarantine PR #24.
2. Preserve and classify the production phone worktree before Git operations.
3. Reproduce and fix the EURUSD D1 `tf_mismatch` on a clean branch from current
   `main`.
4. Reconcile provider usage and hidden network calls per provider.
5. Repair Telegram status policy separately from executable signal delivery.
6. Design automatic topology recovery only after the above paths are stable.
7. Run a new production-validation window with explicit acceptance evidence.

## Exactly one next action

Create one focused clean branch from current `main` that reproduces and fixes the
EURUSD D1 `tf_mismatch` without modifying strategy, automatic recovery,
Telegram, Supabase signal semantics, or the production phone checkout.