# BotA Production Validation Failure — 2026-08-01

Last updated: 2026-08-02 23:31 UTC

## Status

```text
INCIDENT_STATUS=OPEN
PRODUCTION_VALIDATION=FAILED
FINAL_ROLLBACK_CONTROL_PLANE=PASS_AT_RECORDED_TIMESTAMP
PHONE_PRESERVATION=PASS
FIVE_FILE_CORE_DEPLOYMENT=PASS
D1_TIMEFRAME_MAPPING=FIXED_AND_DEPLOYED
CURRENT_FULL_CONTROL_PLANE=UNKNOWN
ACTIVE_SUPERVISOR_WRAPPER_AUTO_MUTATION=OPEN_RISK
HEARTBEAT_TOPOLOGY=OPEN_RISK
AUTOMATIC_RECOVERY_REENABLE_ALLOWED=NO
```

The one-week production validation did not pass. The bounded August 2 repair and
phone deployment materially reduced the defect set but do not convert the
incident to closed or constitute a new endurance-validation pass.

Current detailed phone record:
`audits/PHONE_DEPLOYMENT_2026-08-02.md`.

## Original incident scope

This incident concerns:

- Termux/runit control-plane ownership;
- automatic recovery and boot behavior;
- repository/runtime divergence;
- canonical scheduling verification;
- provider-budget and data-validation reliability;
- Telegram/status correctness;
- production-validation acceptance.

It does not authorize strategy, threshold, scoring, pair, ADX, H1/D1
confirmation, volatility, macro, deduplication, SL/TP, PR #7, or Supabase
signal-semantic changes.

## Verified August 1 failure evidence

During the validation period:

- one `runsvdir` manager existed while all seven required `runsv` supervisors
  were reparented to PID 1;
- measured degraded state:

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
- phone checkout and GitHub `main` diverged;
- repository documentation described watchdog behavior that did not match the
  phone;
- the configured service-daemon executable was unavailable;
- repeated Termux restarts occurred while a continuous `runsvdir` guard was
  active.

The exact cause of every transition was not proven. Android lifecycle, Termux
lifecycle, explicit restarts, resource pressure, and guard behavior must not be
presented as proven causes without direct evidence.

## Original automatic-recovery rollback

The continuous guard and watchdog were stopped. The intended rollback policy was
that the production boot launcher would start the standard Termux service tree
without starting automatic topology recovery.

Recorded rollback verification:

```text
manager_count=1
owned=7/7
running=7/7
orphaned=0
control_plane_rc=0
automatic_recovery=disabled
```

That result remains valid for the recorded timestamp only.

## Repository containment

PR #24 became a divergent, multi-concern preservation branch and is not a valid
repair or deployment vehicle. Focused behaviors were subsequently reapplied from
current `main` through narrow branches.

No direct push to `main` is allowed.

## August 2 repair progress

GitHub baseline after focused repairs:

```text
GITHUB_MAIN=b4d961ea8e5d254c8578e2c022e1394cd134cd7e
```

The production phone was preserved before reconciliation:

```text
PRESERVE_DIR=~/bota-phone-preserve-20260802T210517Z
WORKTREE_CHANGED_FILES=0
INDEX_CHANGED_FILES=0
UNTRACKED_FILES=519
UNTRACKED_ARCHIVED=YES
LOCAL_CONFIG_FILES_BACKED_UP=8
ACTIVE_CRONTAB_BACKED_UP=YES
ALL_GIT_REFS_BUNDLED=YES
```

Five repaired files were deployed as complete byte-verified replacements on a
phone-only local deployment branch:

```text
PHONE_BRANCH=deploy/repaired-core-20260802T215531Z
PHONE_HEAD=d5c765df6fee1241be21ce892fc53e9c4bdcfb8c
REMOTE_PUSH_PERFORMED=NO
```

Files:

```text
tools/supervisor_clock_status.py
tools/build_indicators.py
tools/format_status.py
tools/autostatus.sh
tools/bota_supervisor.sh
```

No heartbeat file, pipeline-health file, service wrapper, crontab entry,
strategy, provider, Telegram, Supabase, or remote branch was changed by this
deployment.

## Acceptance evidence

```text
P6_TARGETED_RUNTIME_ACCEPTANCE=PASS
SUPERVISOR_ACCEPTANCE_SCENARIOS=6
D1_TIMEFRAME_ACCEPTANCE=PASS
FORMATTER_ACCEPTANCE=PASS
AUTOSTATUS_ACCEPTANCE=PASS
PROTECTED_HEARTBEAT_FILES_UNCHANGED=YES
PIPELINE_HEALTH_UNCHANGED=YES
TELEGRAM_CALL_PERFORMED=NO
PROVIDER_CALL_PERFORMED=NO
SERVICE_RESTART_PERFORMED=NO
CRONTAB_MUTATION_PERFORMED=NO
REMOTE_PUSH_PERFORMED=NO
```

The deployed supervisor correctly separated clock availability from runtime
failure while retaining fail-closed market gating. Status formatting was proven
cache-only. Autostatus was proven to skip formatting and delivery outside the
trusted market gate.

## D1 acceptance-gate update

Original invalid evidence:

```text
cache/indicators_EURUSD_D1.json
error=tf_mismatch
tf_ok=false
tf_actual_min=0.0
```

Root cause was `tools/build_indicators.py::tf_minutes()` returning zero for D1.
The deployed implementation now verifies:

```text
tf_minutes("D1")=1440
tf_minutes("d1")=1440
```

Therefore the code-level D1 acceptance failure is repaired. The actual live D1
cache still needs regeneration and verification during a later updater cycle.

## New topology finding discovered during acceptance

The active phone supervisor service is running and invokes the deployed
`tools/bota_supervisor.sh`.

However, its active phone-only wrapper `services/bota-supervisor/run` is absent
from GitHub `main` and includes:

```text
if no process matches runsvdir.*bota-sv:
    runsvdir -P "$HOME/.config/bota-sv" &
```

This contradicts the intended rollback policy that automatic topology recovery
was disabled.

P6 recorded:

```text
SUPERVISOR_SERVICE_STATUS=run
RUNSVDIR_PROCESS_SNAPSHOT=none
```

The `none` snapshot may be caused by an incorrect process matcher rather than
true manager absence. In that case, the wrapper may attempt repeated manager
creation and reintroduce duplicate/split control-plane risk.

This is now the first unresolved incident gate.

## Heartbeat topology finding

Active phone path:

```text
services/bota-heartbeat/run -> tools/bota_heartbeat_utc.sh
```

GitHub repaired path:

```text
tools/heartbeat.sh -> tools/heartbeat_delivery.py
```

The active phone wrapper retains deadman and recovery behavior but may retry a
failed delivery every 60 seconds. The GitHub controller provides locking and
bounded monotonic retry backoff but does not replace the phone deadman semantics
by itself.

Heartbeat remains an open gate after supervisor-wrapper topology is corrected.

## Current acceptance-gate status

1. **Control-plane endurance** — OPEN; current complete ownership not re-proven.
2. **Automatic recovery safety** — OPEN; active supervisor wrapper can create a
   manager automatically.
3. **Repository/runtime convergence** — PARTIAL PASS; five core files converge,
   but service wrappers and heartbeat topology remain phone-only/divergent.
4. **Canonical scheduling** — OPEN; crontab was preserved, not re-certified.
5. **Data integrity** — D1 CODE DEFECT PASS; live cache regeneration pending.
6. **Provider-budget accounting** — repository repairs exist; production
   acceptance remains open.
7. **Notification correctness** — status/autostatus PASS; active heartbeat path
   remains open.
8. **Production endurance** — NOT RERUN.

## Prohibited actions

- Do not merge or deploy PR #24.
- Do not re-enable the old watchdog or continuous guard.
- Do not let service schedulers create managers implicitly.
- Do not reset, pull, merge, or overwrite the phone without preservation.
- Do not replace heartbeat scripts without preserving deadman/recovery behavior.
- Do not change strategy to compensate for runtime or data defects.
- Do not call the incident closed before a new bounded endurance window passes.

## Repair sequence from current state

1. Track and repair `services/bota-supervisor/run` as a non-mutating scheduler.
2. Verify exactly one intended manager, seven owned/running required services,
   zero orphans/duplicates, and no automatic manager creation.
3. Reconcile heartbeat delivery/backoff while retaining deadman/recovery
   semantics.
4. Regenerate and verify live D1 caches.
5. Reconcile canonical scheduling and provider-budget evidence.
6. Run a new production-validation window.

## Exactly one next action

Replace `services/bota-supervisor/run` with a tracked, non-mutating scheduler and
verify the full current control plane before any heartbeat replacement.
