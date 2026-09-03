# BotA Current Operational Forensics

Last updated: **2026-09-03 UTC**

This file is the canonical short handoff for the completed post-closure Android/Termux investigation.

Canonical evidence:

- `audits/OPERATIONAL_RUNTIME_AND_DELIVERY_FORENSICS_2026-09-03.md`
- `audits/FINAL_STRATEGY_CLOSURE_2026-09-03.md`
- PR #125 / merge commit `17345c3c6d5403d968cfbc204ec49a1d5a118dbc`

## Final governance state

```text
FINAL_STRATEGY_VERDICT=CLOSE
ACTIVE_STRATEGY_VALIDATION=NO
STRATEGY_TUNING_AUTHORIZED=NO
PRODUCTION_READY=NO
HETZNER_PRODUCTION_CUTOVER=NO
BOTA_OPERATIONAL_FORENSICS=CLOSED
DELIVERY_ROW_ARCHAEOLOGY=STOP
FURTHER_BOTA_RUNTIME_INVESTIGATION=NO
```

The operational investigation does not alter the final strategy result:

```text
POLICY_B_ACCEPTED=195
PRE_REGISTERED_KILL_THRESHOLD=400
195 < 400 -> CLOSE
```

## Final proven operational findings

```text
LAST_CONFIRMED_SUPABASE_SIGNAL=2026-08-12
LAST_NORMAL_EVALUATED_DAY=2026-08-14
PACKAGE6_DEPLOYED=2026-08-16
FIRST_ALL_OPEN_WINDOW_INTERNAL_ERROR_DAY=2026-08-17

PACKAGE6_MANIFEST_FILES=12
PACKAGE6_RUNTIME_PARITY_FALSE_GREEN=YES
PACKAGE6_TRANSITIVE_DEPENDENCY_CLOSURE_CHECKED=NO

MISSING_RUNTIME_DEPENDENCY_1=tools/watcher_persistence_gate.py
MISSING_RUNTIME_DEPENDENCY_2=tools/telegram_delivery.py

POST_AUG17_ALERT_ROWS=3052
POST_AUG17_ACCEPTED_ROWS=15
POST_AUG17_NONZERO_BUY_SELL_ROWS=694
UPSTREAM_SCORING_COLLAPSE_AFTER_PACKAGE6=NO
```

Package 6 proved parity only for a hand-selected manifest, not for the runtime dependency graph. That allowed an incomplete mixed generation to be reported green.

The deployed watcher wrapper required `watcher_persistence_gate.py`, which was omitted. The deployed Telegram guard imported `telegram_delivery`, while `telegram_delivery.py` was also omitted. Runtime evidence later showed both the missing persistence helper and repeated `ModuleNotFoundError: No module named 'telegram_delivery'` failures.

## Reusable deployer defect — fixed

PR #125 hardened `ops/transactional_phone_deploy.py` so manifest parity alone can no longer produce a full green runtime-generation claim.

The merged deployer now requires:

```text
MANIFEST_PARITY=PASS
DEPENDENCY_CLOSURE=PASS
```

before reporting a green runtime generation.

The dependency check:

- computes a transitive fixed-point closure from the pinned release;
- follows local shell helper references and local Python imports;
- detects missing dependencies;
- detects stale dependencies that exist on disk but do not match the pinned release;
- fails before service quiesce, generation mutation, backup, or install;
- preserves the existing transactional rollback behavior.

Pre-merge validation included:

```text
TRANSITIVE_FIXED_POINT=PASS
DEPENDENCY_FAILURE_BEFORE_MUTATION=PASS
STALE_OR_UNKNOWN_GENERATION_CAN_PASS=NO
FALSE_GREEN_REPORTING_PATH_REMAINS=NO
TRANSACTIONAL_TESTS=27/27 PASS
CRASH_CONSISTENCY_TESTS=PASS
RUNTIME_BARRIER_TESTS=PASS
PY_COMPILE=PASS
DIFF_CHECK=CLEAN
STRATEGY_FILES_CHANGED=0
RUNTIME_DEPLOYED=NO
```

## Android wall-clock exception

The Android device wall clock remains approximately 14 hours fast despite attempted manual correction.

Final observed sample:

```text
PHONE_UTC=2026-09-03T23:26:53Z
SERVER_UTC=2026-09-03T09:28:02Z
CLOCK_DRIFT_SECONDS=50331
CLOCK_DRIFT_ABS_SECONDS=50331
LOCAL_CLOCK_UNSAFE=YES
SERVER_CLOCK_OK=YES
SERVER_SOURCES=4
SERVER_SPREAD_SECONDS=1
```

This is classified as an unresolved **device/OS clock defect**, not a remaining BotA forensic blocker.

Reason:

- BotA market/session gating uses its trusted server clock path rather than Android wall time when trusted time is available;
- the observed market gate followed the trusted clock;
- `tools/clock_drift_check.py` is reporting-only and does not mutate strategy or gate behavior.

Therefore the phone wall-clock issue may be handled separately as general device maintenance if the phone is reused for another project. It does not authorize more BotA investigation.

## Delivery question — intentionally not pursued

The strategy/evaluation layer produced accepted decisions after Aug-16 while Supabase publication stopped after Aug-12. The missing `telegram_delivery.py` dependency is a strong delivery-path failure mechanism because `telegram_send_guard.py` imports it before Telegram delivery can proceed, and GREEN Supabase publication is downstream of the Telegram transaction.

The exact row-by-row mapping of the 15 post-Aug-17 accepted alerts is intentionally **not** being completed.

```text
DELIVERY_ROW_MAPPING=NOT_REQUIRED
REASON=NON_DECISION_RELEVANT_ARCHAEOLOGY_AFTER_STRATEGY_CLOSURE
```

The known deployment defect has been fixed at the reusable system layer. Additional signal-delivery reconstruction would not change any authorized action.

## Final non-actions

```text
DO_NOT_TUNE_STRATEGY=YES
DO_NOT_REOPEN_BOTA=YES
DO_NOT_TRACE_15_HISTORICAL_ACCEPTS=YES
DO_NOT_DEPLOY_BOTA_RUNTIME=YES
DO_NOT_DEPLOY_HETZNER_PRODUCTION=YES
DO_NOT_CHANGE_THRESHOLDS=YES
DO_NOT_CREATE_ANOTHER_BOTA_FORENSIC_GATE=YES
```

## Final action

**Archive/preserve BotA evidence and remove BotA from the active-work queue. Move decision effort to projects with an authorized future.**
