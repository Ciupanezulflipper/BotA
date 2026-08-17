# BotA Chat Handoff

Last updated: **2026-08-17 UTC**

Read this first in any new AI session before proposing BotA changes.

## Current grounded answer

```text
GITHUB_MAIN_AT_PACKAGE6=028db6ee5a993869bf33a534c4339475981d9357
PR108=MERGED
PR108_RUNTIME_RELEASE=f36836315526fd2be826e8abff1c333004b64b0c
PR113=MERGED
PACKAGE6_PHONE_DEPLOYMENT=PASS
PACKAGE6_RUNTIME_FILES_VERIFIED=12
PACKAGE6_POSTDEPLOY_ACCEPTANCE=BLOCKED
LATEST_CONTROL_PLANE=7/7_RUNNING_7/7_OWNED_WITH_1_ZOMBIE_RUNSV
WEEKEND_CONTROL_PLANE_STABILITY=FAIL
PROFITLAB_PENDING_BYTES_AT_FIRST_POSTDEPLOY_GATE=271063
OPEN_MARKET_THREE_PAIR_PROOF=PENDING
PRODUCTION_READY=NO
```

## User scope and release objective

Do not expand BotA work into unrelated audits, tools, repos, or strategy changes. The objective is a clean, reliable production signal bot using the existing EURUSD/GBPUSD/USDJPY M15 strategy and modern Telegram signal presentation.

Do not waste phone/laptop sessions by repeatedly rediscovering already-proven facts. Use the accumulated evidence and close one actual release blocker at a time.

## Package 6 phone deployment

The reviewed transactional deployer from PR #113 successfully installed the 12-file PR #108 runtime payload pinned to:

```text
f36836315526fd2be826e8abff1c333004b64b0c
```

Deployment audit:

```text
/data/data/com.termux/files/home/BotA/audits/transactional_phone_deploy_20260816T201256Z_31681
```

The first attempt safely aborted because the deployer did not find `SUPABASE_SERVICE_KEY` in `.env` / `.env.runtime`. The key already existed in local untracked `config/strategy.env`, was identified as a new Supabase secret key, and returned HTTP 200 with both the current publisher headers and `apikey` only. No secret value was printed or committed. The local ignored `.env.runtime` alias is mode `0600`.

## Post-deploy findings

The first production-integrity check found two stale control-plane files and a ProfitLab backlog. The two runtime files were repaired to exact release bytes/modes:

```text
start_native_service_daemon_watchdog.sh
  blob=c383857b7323e1511d71e351a3becd54ca42d682
  mode=755
control_plane_status.py
  blob=45e7aa5d5b88668720d48efc009cb376c0109783
  mode=755
CONTROL_PLANE_PARITY_REPAIR=PASS
```

The latest control-plane snapshot then showed:

```text
MANAGER_COUNT=1
OWNED=7/7
RUNNING=7/7
ORPHANED=0
DUPLICATES=0
LIVE_CROND_COUNT=1
FAILURE=zombie_runsv_count:1
```

## Critical correction from weekend telemetry

The operator reported **89 BotA Telegram messages during the weekend**. These were not Monday-market notifications and were not one duplicated unchanged failure.

The stream shows repeated real control-plane degradation and recovery from 2026-08-14 through 2026-08-17 UTC, including:

```text
manager_count:0
owned:0/7 .. 6/7
orphaned:1 .. 7
running:6/7
live_crond_count:0
crond_pidfile:missing
crond_not_owned_by_current_runsv
crond_parent_not_current_runsv
zombie_runsv_count:1 -> 2 -> 3
shadow DEADMAN=118m,218m,245m,197m,151m
```

The correct diagnosis is **recurring runtime/control-plane flapping**. Repeated RECOVERY messages prove self-recovery occurs, but they do not prove stability because the same failure families return.

Do not treat the 89-message problem as a notification-dedup bug only. Alert coalescing is desirable later, but it must not conceal real instability.

## Current production scope

```text
PAIRS=EURUSD GBPUSD USDJPY
TIMEFRAMES=M15
POLICY_B_ENABLED=1
POLICY_B_SCORE_MIN=70
POLICY_B_ADX_MAX=30
NEWS_ON=0
TELEGRAM_ENABLED=1
DRY_RUN_MODE=0
```

No threshold lowering, forced signals, or fake Telegram trade is authorized.

## Current release blockers

1. recurring native-manager / runsv / crond ownership instability, including zombie accumulation;
2. ProfitLab pending region (`271063` bytes at first post-deploy gate) must be reconciled without bootstrap/reset;
3. natural market-open same-cycle EURUSD/GBPUSD/USDJPY M15 acceptance remains pending.

Telegram operator-alert presentation should be cleaned only after the health state is trustworthy enough not to hide distinct incidents.

## Canonical current sources

1. `CONTINUITY_CURRENT.md`
2. `AI_START_HERE.md`
3. `audits/PACKAGE6_PHONE_DEPLOY_AND_WEEKEND_RUNTIME_FINDINGS_2026-08-17.md`
4. GitHub issue #9
5. `ERRORS.md`
6. this file

## Exactly one next action

Close the recurring control-plane stability defect from the existing weekend evidence. Do not start another broad audit or another unrelated package before that blocker is causally narrowed and fixed.
