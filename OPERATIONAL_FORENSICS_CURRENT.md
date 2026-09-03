# BotA Current Operational Forensics

Last updated: **2026-09-03 UTC**

This file is the short operational handoff for the post-closure Android/Termux investigation.

Canonical detailed evidence:

- `audits/OPERATIONAL_RUNTIME_AND_DELIVERY_FORENSICS_2026-09-03.md`
- `audits/FINAL_STRATEGY_CLOSURE_2026-09-03.md`

## Governance boundary

```text
FINAL_STRATEGY_VERDICT=CLOSE
ACTIVE_STRATEGY_VALIDATION=NO
STRATEGY_TUNING_AUTHORIZED=NO
PRODUCTION_READY=NO
HETZNER_PRODUCTION_CUTOVER=NO
THIS_WORK=OPERATIONAL_FORENSICS_ONLY
```

## Current proven operational state

```text
SEP3_MARKET_GATE_RESULT=CORRECT
PHONE_WALL_CLOCK≈14_HOURS_FAST
TRUSTED_CLOCK_ARCHITECTURE_NOT_FULLY_INDEPENDENT=YES

LAST_CONFIRMED_SUPABASE_SIGNAL=2026-08-12
LAST_NORMAL_EVALUATED_DAY=2026-08-14
PACKAGE6_DEPLOYED=2026-08-16
FIRST_ALL_OPEN_WINDOW_INTERNAL_ERROR_DAY=2026-08-17

PACKAGE6_MANIFEST_FILES=12
PACKAGE6_RUNTIME_PARITY_FALSE_GREEN=YES
DEPENDENCY_CLOSURE_VERIFIED_BY_DEPLOYER=NO

MISSING_RUNTIME_DEPENDENCY_1=tools/watcher_persistence_gate.py
MISSING_RUNTIME_DEPENDENCY_2=tools/telegram_delivery.py

POST_AUG17_ALERT_ROWS=3052
POST_AUG17_ACCEPTED_ROWS=15
POST_AUG17_NONZERO_BUY_SELL_ROWS=694
UPSTREAM_SCORING_COLLAPSE_AFTER_PACKAGE6=NO
```

## Why the runtime went false-green

`ops/transactional_phone_deploy.py` verified only its hard-coded 12-file MANIFEST. It did not verify local script/import dependency closure.

The deployed watcher wrapper required `watcher_persistence_gate.py`, but that file was omitted. The deployed Telegram guard imports `telegram_delivery`, but `telegram_delivery.py` was also omitted.

Result:

```text
MANIFEST_PARITY=PASS
TRUE_RUNTIME_DEPENDENCY_CLOSURE=FAIL
```

## Current unresolved delivery question

The strategy/evaluation layer continued to produce accepted decisions after Aug-16, but Supabase has no signal rows after Aug-12.

The strongest current delivery-path failure is:

```text
telegram_send.sh
 -> telegram_send_guard.py
 -> import telegram_delivery
 -> ModuleNotFoundError
 -> Telegram transaction cannot complete
 -> GREEN Supabase publication cannot complete
```

This is strongly supported by code plus runtime errors, but the final forensic task is to correlate each of the 15 post-Aug-17 accepted alert rows to its exact delivery outcome.

## Next read-only action

Correlate all 15 post-Aug-17 accepted `logs/alerts.csv` rows against retained watcher/Telegram/Supabase/error evidence and classify each outcome. Do not repair or restore runtime dependencies until that evidence is preserved.

## Explicit non-actions

```text
DO_NOT_TUNE_STRATEGY=YES
DO_NOT_REOPEN_BOTA=YES
DO_NOT_DEPLOY_HETZNER_PRODUCTION=YES
DO_NOT_CHANGE_THRESHOLDS=YES
DO_NOT_RESTORE_PHONE_FILES_BEFORE_EVIDENCE_CAPTURE=YES
```
