# BotA Current Continuity State

Last updated: **2026-08-17 UTC**

This is the current operational handoff. Older dated readiness snapshots are historical context only.

## Current authoritative status

```text
GITHUB_MAIN_AT_PACKAGE6=028db6ee5a993869bf33a534c4339475981d9357
PR108_RUNTIME_RELEASE=f36836315526fd2be826e8abff1c333004b64b0c
PR108_STATE=MERGED
PR113_STATE=MERGED
PACKAGE5_TRANSACTIONAL_DEPLOYER=COMPLETE
PACKAGE6_PHONE_DEPLOYMENT=PASS
PACKAGE6_12_FILE_RUNTIME_PARITY=PASS
PACKAGE6_POSTDEPLOY_ACCEPTANCE=BLOCKED

PAIRS=EURUSD GBPUSD USDJPY
TIMEFRAMES=M15
POLICY_B_ENABLED=1
POLICY_B_SCORE_MIN=70
POLICY_B_ADX_MAX=30
NEWS_ON=0
TELEGRAM_ENABLED=1
DRY_RUN_MODE=0

LATEST_CONTROL_PLANE_MANAGER_COUNT=1
LATEST_CONTROL_PLANE_OWNED=7/7
LATEST_CONTROL_PLANE_RUNNING=7/7
LATEST_CONTROL_PLANE_ORPHANED=0
LATEST_CONTROL_PLANE_DUPLICATES=0
LATEST_CONTROL_PLANE_LIVE_CROND=1
LATEST_CONTROL_PLANE_FAILURE=zombie_runsv_count:1
WEEKEND_RUNTIME_STABILITY=FAIL
PROFITLAB_PENDING_BYTES_AT_FIRST_POSTDEPLOY_GATE=271063
OPEN_MARKET_THREE_PAIR_LIVE_PROOF=PENDING
PRODUCTION_READY=NO
```

## Deployment evidence

Package 6 verified remote main, the exact transactional deployer blob, the exact runtime release pin, one watcher owner before deployment, and then installed the reviewed 12-file runtime payload.

```text
DEPLOYMENT=PASS
DEPLOY_AUDIT=/data/data/com.termux/files/home/BotA/audits/transactional_phone_deploy_20260816T201256Z_31681
RUNTIME_FILES_VERIFIED=12
WATCHER_COUNT_AFTER=1
```

The initial attempt failed safely before mutation because the deployer did not find `SUPABASE_SERVICE_KEY` in `.env` / `.env.runtime`. The key already existed in local untracked `config/strategy.env`; compatibility probes against the BotA Supabase project returned HTTP 200 with the current publisher headers and with `apikey` only. The key value was never printed. It was aliased locally into ignored `.env.runtime` mode `0600`.

## Post-deploy integrity findings

The first post-deploy integrity gate failed only after deployment had succeeded. It exposed two stale control-plane files plus a ProfitLab backlog:

```text
runtime_blob_mismatch:tools/start_native_service_daemon_watchdog.sh
runtime_mode_mismatch:tools/start_native_service_daemon_watchdog.sh:700:755
runtime_blob_mismatch:tools/control_plane_status.py
profitlab_pending_bytes:271063
```

The two stale files were repaired from the exact runtime release and reverified:

```text
tools/start_native_service_daemon_watchdog.sh
  blob=c383857b7323e1511d71e351a3becd54ca42d682
  mode=755

tools/control_plane_status.py
  blob=45e7aa5d5b88668720d48efc009cb376c0109783
  mode=755

CONTROL_PLANE_PARITY_REPAIR=PASS
```

A subsequent control-plane snapshot showed exactly one remaining local condition:

```text
CONTROL_PLANE_HEALTHY=FALSE
MANAGER_COUNT=1
OWNED=7
RUNNING=7
ORPHANED=0
DUPLICATES=0
LIVE_CROND_COUNT=1
FAILURE=zombie_runsv_count:1
```

## Weekend runtime history is the key finding

The operator reported **89 BotA Telegram messages during the weekend**. This is not a single stale alert being resent. The accumulated messages show repeated real DEGRADED/RECOVERY and DEADMAN/RECOVERY cycles between 2026-08-14 and 2026-08-17 UTC.

Repeated failure families include:

- manager loss (`manager_count:0`);
- ownership collapse from 6/7 down to 0/7, with PID-1 orphaning;
- `crond` absent or not owned by the current runsv;
- missing `crond.pid` and parent mismatch;
- zombie `runsv` counts increasing from 1 to 2 to 3;
- shadow DEADMAN windows of 118, 218, 245, 197, and 151 minutes, followed by recovery.

This changes the release diagnosis: **runtime/control-plane flapping is still unresolved even though individual snapshots recover to 7/7**. A single healthy snapshot cannot be used as production-stability proof.

## Telegram classification

The message volume is unacceptable for operator use, but notification suppression is not the primary fix. Many messages correspond to genuinely different failure/recovery transitions. The correct sequence is:

1. stabilize the underlying control plane;
2. preserve truthful incident transitions;
3. then coalesce/debounce operator messaging so one incident lifecycle is concise and useful without hiding distinct real failures.

The modern GREEN/YELLOW trade-card presentation remains separate from infrastructure health messaging.

## ProfitLab status

The first post-deploy integrity check measured:

```text
PROFITLAB_PENDING_BYTES=271063
```

Do not bootstrap or reset the cursor merely to make the gate green. Inspect/reconcile the pending region and preserve historical delivery semantics.

## Current freeze

```text
DO_NOT_BOOTSTRAP_PROFITLAB=YES
DO_NOT_RESET_CURSOR_TO_HIDE_BACKLOG=YES
DO_NOT_LOWER_THRESHOLDS=YES
DO_NOT_FORCE_SIGNAL_COUNT=YES
DO_NOT_FORCE_TELEGRAM_TEST_SIGNAL=YES
DO_NOT_HIDE_REAL_RUNTIME_FAILURES_WITH_DEDUP=YES
DO_NOT_DECLARE_PRODUCTION_READY_FROM_SINGLE_HEALTHY_SAMPLE=YES
```

## Exactly one next engineering action

Treat the recurring manager/runsv/crond ownership failures, zombie accumulation, and associated DEADMAN episodes as the single current release blocker. Use the existing evidence to close that stability defect before doing more strategy work, tooling work, presentation work, or broad repository auditing.

After stable control-plane acceptance, reconcile ProfitLab pending bytes, then run the natural market-open same-cycle EURUSD:M15 / GBPUSD:M15 / USDJPY:M15 acceptance on the final runtime.

Canonical detailed evidence: `audits/PACKAGE6_PHONE_DEPLOY_AND_WEEKEND_RUNTIME_FINDINGS_2026-08-17.md`.
