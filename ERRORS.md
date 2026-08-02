# BotA Errors and Silent-Failure Register

Last updated: 2026-08-02

Purpose: preserve verified failure classes, current open risks, and prevention
rules so they are not rediscovered through repeated broad audits.

## Current highest-priority incident: open

The one-week production validation ending 2026-08-01 failed.

The July 26 service-manager closure remains valid historical evidence, but it was
superseded as a production-readiness verdict by later regressions.

Verified validation failures:

- control-plane regression to `owned=0/7`, `running=7/7`, `orphaned=7`;
- temporary required-service counts below seven;
- canonical crontab verification failure;
- phone checkout and GitHub `main` divergence;
- repository documentation not matching the actual watchdog topology;
- configured native service-daemon executable unavailable on the phone;
- repeated Termux restarts while a continuous `runsvdir` guard was active;
- production validation could not be declared complete despite valid data fetch,
  decision calculation, and at least one eligible GBPUSD M15 signal.

Final rollback evidence recorded:

```text
manager_count=1
owned=7/7
running=7/7
orphaned=0
control_plane_rc=0
automatic_recovery=disabled
```

The current phone topology after that timestamp is UNKNOWN until one fresh,
narrow proof is actually required.

See `audits/INCIDENT_2026-08-01_VALIDATION_FAILURE.md`.

## Repository contamination: PR #24

PR #24 started as a three-file preservation branch from an older phone checkout.
It later expanded to seven commits and thirty-two changed files, diverged heavily
from current `main`, became non-mergeable, and mixed unrelated concerns.

It must not be merged or deployed.

Prevention:

- create and verify a clean branch from current `main` before any write;
- keep one behavior and one acceptance gate per branch;
- never use a preservation branch as an integration branch;
- salvage complete files deliberately rather than cherry-picking unknown scope;
- close or mark contaminated PRs as superseded instead of repairing them in place.

## Current data-integrity defect

The August 2 read-only discovery ended with:

```text
LOCAL_STATUS_DATA_DISCOVERY_COMPLETE=YES
RUNTIME_MUTATION_PERFORMED=NO
GIT_CHANGED=NO
```

Do not repeat the broad discovery.

The supplied cache evidence showed:

```text
cache/indicators_EURUSD_D1.json
error=tf_mismatch
tf_ok=false
tf_actual_min=0.0
weak=true
ema9=0.0
ema21=0.0
atr=0.0
```

This is an explicit invalid-data state. It must be reproduced through the exact
active EURUSD D1 fetch/build path before changing strategy or declaring a missed
signal.

Weekend-stale intraday candles alone are not proof of provider failure.

## Runtime ownership and scheduler lessons

- A manager process and matching pidfile do not prove service ownership.
- `supervise/pid` identifies the supervised service process, not `runsv`.
- Correct ownership proof is service PID -> PPID -> `runsv` -> supervisor
  PPID/cwd/state/command.
- `sv status` alone cannot prove parentage or restart capability.
- Surviving supervisors may remain under PID 1 after manager death.
- Starting a second manager while orphans remain can create duplicates.
- A transient split control plane may reconverge; record both failure and
  recovery without erasing either.
- A stale or wiped crontab can leave Daily Proof alive while the signal factory
  is unscheduled.
- Detached crond and runit crond can create split-brain scheduling.
- Multiple executable boot files can independently start the same daemon.

## Automatic-recovery lessons

- Automatic recovery is currently disabled by design after the August 1
  rollback.
- The configured native service-daemon executable must be verified on the phone
  before any launcher references it.
- A continuous recovery guard must not be deployed merely because a one-shot
  reconciliation worked.
- Any replacement guard requires bounded cadence, locking, backoff,
  failure-injection tests, Termux restart observation, and a kill switch.
- Do not re-enable a watchdog or guard from stale repository documentation.

## Health and time semantics

- Service presence is not useful progress.
- Use trusted provider/server UTC for market semantics.
- Use monotonic time for same-boot cadence, cooldowns, and health.
- Android/ship wall time is display-only.
- Reject negative and future stale ages.
- Print exact time inputs used in diagnostics.
- Never depend on `/proc/uptime` on this Android build.
- Changed PIDs are restart events, not failures by themselves.

## Provider and data risks

- Track budgets per actual provider and endpoint, not through a generic success
  counter.
- Formatting or status code must not make hidden unaccounted network calls.
- Provider fallback must have explicit source conditions, caching, and quota
  ownership.
- Validate pair, timeframe, granularity, timestamps, ordering, row count, and
  closed-candle semantics before indicator calculation.
- A cache writer must fail closed on timeframe mismatch; zero indicators must not
  be treated as neutral valid data.
- Do not mix Yahoo, OANDA, RapidAPI, or other provider evidence without naming
  the exact source for each artifact.

## Notification and persistence risks

- Telegram status messages are context, not executable trade entries.
- Internal vote/scoring language must not be presented as an entry signal.
- Status notifications should respect configured market-session policy.
- Telegram delivery, Supabase persistence, provider failure, runtime failure,
  and a valid HOLD/rejection are distinct outcomes.
- Count only events inside a verified current-cycle boundary.
- Confirm the full decision record is written before dedup.

## Operational package failures

- Broad scans can enter runit FIFOs or mix active and historical evidence.
- Generic symbol/timeframe regexes can parse arbitrary log tags as pairs.
- Historical watcher logs must not be selected as current evidence because they
  contain more marker strings.
- CSV schema must be printed and verified before parsing assumptions are coded.
- Expected zero-match commands must not abort under `pipefail`.
- `set -Eeuo pipefail` belongs in a bounded child script, not the interactive
  shell.
- Top-level `exit` can close Termux.
- Oversized pasted packages can crash Termux.
- Read-only packages answer one narrow question.
- Mutation requires fresh preflight, backup, rollback, authorization, and
  independent verification.

## Repository milestones retained

```text
PR #18 MERGED=ef94e4fd1c9a7a786f7514024828fbdfc1146143
PR #19 MERGED=12000f04137a000cb3d1c6bf7acb45da288907c9
PR #20 MERGED=87e43ce76d43d625e7e9c7a6715cabb59f4b65c9
PR #21 MERGED=09a1bd5b57e0bf3a39e79afc827d14e09e8b1031
PR #22 MERGED=0694e17c09c3c8663622dce745d8b449c3cd2405
PR #23 MERGED=95c54beff7741b32da086bcbd5e87f1c9d132cb5
PR #25 MERGED=2f50904644d86c5564e3d6ae9d3cc777a5a29278
```

These merges do not authorize redeploying the failed August 1 automatic-recovery
configuration.

## Efficient diagnostic order

### Gate A — repository safety

Before phone Git operations, preserve and classify every local change. Do not
reset, checkout, pull, merge, or overwrite a dirty production worktree.

### Gate B — current control plane

When current runtime evidence is required, verify one intended manager, seven
owned/running supervisors, zero orphans/invalid/duplicates, supervised crond,
and the actual boot launcher. Do not assume a watchdog exists.

If Gate B fails, stop. Do not inspect strategy, watcher decisions, CSV, caches,
or Telegram history.

### Gate C — one active data path

After Gate B passes, reproduce one pair/timeframe through exact provider fetch,
cache write, and indicator build. Validate granularity and timestamps first.

### Gate D — decision integrity

Classify one current cycle as valid HOLD/rejection, eligible signal, send failure,
persistence failure, data failure, or infrastructure failure.

### Gate E — signal lifecycle

For the next ACTIVE signal, verify Telegram, Supabase, closer execution, and
CLOSED/CANCELLED transition with result pips.

### Gate F — mutation

Require persistent failure, narrow cause, exact expected source state, backup,
rollback, explicit authorization, and independent post-change verification.

## Current next repair

Reproduce and fix the EURUSD D1 `tf_mismatch` from current `main` on a focused
clean branch. Do not touch strategy, notification code, automatic recovery, or
the production phone in the same package.