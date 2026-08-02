# BotA Current Continuity State

Last updated: 2026-08-02

This file is the compact authoritative handoff. Historical detail remains in
`CONTINUITY.md`, `ERRORS.md`, `audits/ERROR_LOG.md`,
`audits/INCIDENT_2026-08-01_VALIDATION_FAILURE.md`, and GitHub issue #9.

## Scope lock

Current work is reliability, data integrity, provider-budget accounting,
notification correctness, and repository/runtime convergence.

Do not change trading strategy, thresholds, configured pairs, scoring, ADX,
H1/D1 confirmation rules, volatility or macro filters, dedup semantics, SL/TP,
PR #7, or Supabase signal semantics merely to create more signals.

No direct push to `main`.

## Evidence rules

Material claims must be classified as VERIFIED, ASSUMED, or UNKNOWN.

- VERIFIED means proven by current GitHub state, direct Termux output, current
  provider/server evidence, Supabase evidence, or an explicit user-provided log.
- ASSUMED means plausible but not proven.
- UNKNOWN means it must not drive mutation.

Trusted provider/server UTC controls market semantics. Monotonic time controls
same-boot cadence, cooldowns, and health. Android/ship wall time is display-only.
Never depend on `/proc/uptime` on this Android build.

Every Termux package must display `audits/ERROR_LOG.md`, run strict shell options
only inside a bounded child script, preserve the interactive parent shell,
inspect one narrow evidence domain, and end with exactly one next action.

## Superseded July 26 snapshot

On 2026-07-26, the native service-manager migration and watchdog finalization
were verified at:

```text
MANAGER_COUNT=1
OWNED=7/7
RUNNING=7/7
ORPHANED=0
INVALID=0
DUPLICATES=0
DOWN_SERVICES=NONE
WATCHDOG_COUNT=1
CONTROL_PLANE_GATE=PASS
STABILITY_CHECK=PASS
```

That evidence remains historically valid for that timestamp. It is not the
current production-readiness verdict because later validation exposed new
regressions.

## August 1 production validation: failed

The one-week production validation did not pass.

Verified during the validation period:

- BotA remained capable of fetching data, calculating decisions, and delivering
  at least one eligible GBPUSD M15 signal.
- The control plane regressed to one manager with all seven required `runsv`
  supervisors orphaned under PID 1: `owned=0/7`, `running=7/7`, `orphaned=7`.
- A later one-shot reconciliation restored one manager, `owned=7/7`,
  `running=7/7`, and `orphaned=0`.
- Required service counts temporarily fell below seven.
- The phone checkout and GitHub `main` were not synchronized.
- Canonical crontab verification failed.
- Runtime and repository documentation described a watchdog configuration that
  did not match the phone.
- The configured native service-daemon executable was unavailable on the phone.
- A continuous `runsvdir` guard was followed by repeated Termux restarts.
- The continuous guard and watchdog were stopped.
- The boot launcher was replaced with a safe launcher that starts the standard
  Termux service tree but intentionally does not start automatic topology
  recovery.

Final rollback verification recorded:

```text
manager_count=1
owned=7/7
running=7/7
orphaned=0
control_plane_rc=0
automatic_recovery=disabled
```

The full incident record is:
`audits/INCIDENT_2026-08-01_VALIDATION_FAILURE.md`.

## Repository containment

PR #24 began as a three-file preservation PR based on an older phone checkout.
It later drifted to seven commits and thirty-two changed files, diverged heavily
from current `main`, became non-mergeable, and accumulated unrelated runtime,
documentation, testing, provider, and notification changes.

PR #24 must not be merged or used as a deployment source. Salvageable behavior
must be reapplied deliberately from current `main` in narrow clean branches with
complete-file replacements and focused tests.

The clean containment branch is:

```text
repair/production-validation-truth-20260802
```

This branch changes repository documentation only. It performs no phone,
service, process, cron, provider, Telegram, Supabase, strategy, or runtime
mutation.

## August 2 read-only data discovery

The latest provided Termux package ended with:

```text
LOCAL_STATUS_DATA_DISCOVERY_COMPLETE=YES
RUNTIME_MUTATION_PERFORMED=NO
GIT_CHANGED=NO
```

Do not repeat that broad discovery.

A concrete unresolved data defect was visible in the supplied cache evidence:

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

Weekend-stale M15/H1/H4 candles are not automatically a defect. The EURUSD D1
`tf_mismatch` is different: it is an explicit invalid-data state and must be
traced through the active fetch/build path before any strategy conclusion.

## Current verified status

```text
PRODUCTION_VALIDATION=FAILED
FINAL_ROLLBACK_CONTROL_PLANE=PASS_AT_RECORDED_TIMESTAMP
AUTOMATIC_TOPOLOGY_RECOVERY=DISABLED
CURRENT_PHONE_TOPOLOGY=UNKNOWN_UNTIL_FRESH_NARROW_PROOF
PR24_MERGE_ALLOWED=NO
BROAD_DATA_DISCOVERY_REPEAT_REQUIRED=NO
STRATEGY_MUTATION_ALLOWED=NO
```

## Efficient repair order

1. Keep repository truth and incident records synchronized.
2. Preserve the phone worktree before any checkout, reset, merge, or overwrite.
3. Prove one current control-plane snapshot only when a runtime mutation or live
   diagnosis actually requires it.
4. Diagnose the EURUSD D1 timeframe mismatch from the active updater path using
   exact files and a bounded reproduction.
5. Reconcile provider calls and budgets per provider.
6. Repair Telegram status wording and market gating separately from executable
   signal delivery.
7. Reintroduce automatic topology recovery only after a bounded implementation
   passes failure-injection tests and does not restart Termux.
8. Run a new production-validation window only after the above gates pass.

## Exactly one next action

Create one clean code-repair package from current `main` that reproduces and
fixes the EURUSD D1 `tf_mismatch` without touching strategy, runtime processes,
or the production phone checkout.