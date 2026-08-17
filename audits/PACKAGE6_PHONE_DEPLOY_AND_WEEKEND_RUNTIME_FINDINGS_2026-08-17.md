# Package 6 Phone Deployment and Weekend Runtime Findings — 2026-08-17

This record captures the production-phone evidence produced during the weekend release window after PR #108 and PR #113 merged. It is an operational evidence record, not a strategy-change authorization.

## Scope and release identity

```text
GITHUB_MAIN_AT_PACKAGE6_START=028db6ee5a993869bf33a534c4339475981d9357
PACKAGE5_PR=113
PACKAGE5_STATE=MERGED
PACKAGE5_MERGE_MAIN=028db6ee5a993869bf33a534c4339475981d9357
RUNTIME_RELEASE_PIN=f36836315526fd2be826e8abff1c333004b64b0c
PR108_STATE=MERGED
PHONE_ACTION=YES
STRATEGY_CHANGED=NO
THRESHOLDS_CHANGED=NO
PAIRS_CHANGED=NO
TIMEFRAME_CHANGED=NO
```

The transactional deployment executor on `main` remained intentionally pinned to runtime release `f36836315526fd2be826e8abff1c333004b64b0c`. The executor merge SHA was not substituted for the runtime release pin.

## Package 6 deployment result

Phone preflight proved:

```text
REMOTE_MAIN=028db6ee5a993869bf33a534c4339475981d9357
EXECUTOR_BLOB=d2090356ee7beca810e8983cd1c84a5c966008f7
WATCHER_RUNSV_COUNT_BEFORE=1
PHONE_PREFLIGHT=PASS
```

The first deployment attempt failed closed before mutation with:

```text
DEPLOYMENT_ABORTED=REQUIRED_CREDENTIALS_MISSING
```

Safe credential-path investigation established:

```text
TELEGRAM_TOKEN=PRESENT
TELEGRAM_CHAT_ID=PRESENT
SUPABASE_SERVICE_KEY=MISSING_FROM_DEPLOYER_READ_PATH
SUPABASE_SERVICE_KEY=PRESENT_IN=config/strategy.env
KEY_TYPE=NEW_SUPABASE_SECRET
CURRENT_PUBLISHER_HEADERS_HTTP=200
APIKEY_ONLY_HTTP=200
```

No secret value was printed or stored in repository evidence. The existing BotA Supabase secret was copied locally into ignored `.env.runtime` as `SUPABASE_SERVICE_KEY`, mode `0600`, solely to satisfy the production configuration contract. This exposed a configuration-source mismatch: production already had the credential under `config/strategy.env`, while the transactional deploy preflight checked `.env` / `.env.runtime`.

The resumed transactional deployment then passed:

```text
DEPLOYMENT=PASS
AUDIT_DIRECTORY=/data/data/com.termux/files/home/BotA/audits/transactional_phone_deploy_20260816T201256Z_31681
DEPLOY_RC=0
RUNTIME_PARITY=PASS
RUNTIME_FILES_VERIFIED=12
WATCHER_COUNT_AFTER=1
```

Therefore the 12-file PR #108 runtime payload was installed successfully and independently verified against the pinned Git objects.

## Post-deploy acceptance findings

The first production integrity check was not green:

```text
PRE_MARKET_HEALTHY=FALSE
CHECK_CONTROL_PLANE=TRUE
CHECK_WATCHDOG_OWNERSHIP=TRUE
CHECK_BOOT_PERSISTENCE=TRUE
CHECK_CRON_OWNERSHIP=TRUE
CHECK_RUNTIME_PARITY=FALSE
CHECK_PRODUCTION_CONFIG=TRUE
CHECK_PROFITLAB=FALSE
CHECK_MARKET_GATE=TRUE
CHECK_PROGRESS=TRUE
CHECK_TRUSTED_CLOCK=TRUE
```

Failures were:

```text
runtime_blob_mismatch:tools/start_native_service_daemon_watchdog.sh
runtime_mode_mismatch:tools/start_native_service_daemon_watchdog.sh:700:755
runtime_blob_mismatch:tools/control_plane_status.py
profitlab_pending_bytes:271063
```

The two stale control-plane files were repaired on the phone from the exact pinned runtime release and reverified:

```text
tools/start_native_service_daemon_watchdog.sh
  blob=c383857b7323e1511d71e351a3becd54ca42d682
  mode=755

tools/control_plane_status.py
  blob=45e7aa5d5b88668720d48efc009cb376c0109783
  mode=755

CONTROL_PLANE_PARITY_REPAIR=PASS
```

The subsequent control-plane check still failed on one operational condition only:

```text
CONTROL_PLANE_HEALTHY=FALSE
MANAGER_COUNT=1
OWNED=7
REQUIRED=7
RUNNING=7
ORPHANED=0
DUPLICATES=0
LIVE_CROND_COUNT=1
FAILURE_COUNT=1
FAILURE=zombie_runsv_count:1
```

The watcher itself remained running and singleton-owned.

## Weekend Telegram/runtime evidence

The operator reported **89 BotA Telegram messages during the weekend**, not during a Monday market session. The message stream is not one unchanged repeated error. It contains many real DEGRADED → RECOVERY transitions plus DEADMAN → RECOVERY transitions.

Representative emitted failures from 2026-08-14 through 2026-08-17 UTC include:

- `manager_count:0`, `owned:0/7`, `orphaned:7`;
- repeated `owned:6/7`, `running:6/7`, `orphaned:1`;
- `owned:1/7`, `2/7`, `3/7`, `4/7`, `5/7`, and `6/7` episodes;
- `live_crond_count:0`;
- `crond_pidfile:missing`;
- `crond_not_owned_by_current_runsv`;
- `crond_parent_not_current_runsv`;
- `zombie_runsv_count:1`, later `2`, later `3`;
- shadow DEADMAN periods reported as 118, 218, 245, 197, and 151 minutes, each followed by recovery.

The repeated recoveries show that the control plane often restores itself, but the frequency of renewed degradation proves **runtime flapping remains unresolved**. The message volume is therefore primarily an observability symptom of recurring control-plane instability, not merely duplicate-notification spam.

## Correct classification

```text
PACKAGE5_TRANSACTIONAL_DEPLOY_PACKAGE=COMPLETE
PACKAGE6_PHONE_DEPLOYMENT=PASS
PACKAGE6_12_FILE_RUNTIME_PARITY=PASS
PACKAGE6_POSTDEPLOY_ACCEPTANCE=BLOCKED
CONTROL_PLANE_STATIC_7_OF_7_SAMPLE=PASS_EXCEPT_ZOMBIE
CONTROL_PLANE_WEEKEND_STABILITY=FAIL
PROFITLAB_BACKLOG=UNRESOLVED
TELEGRAM_OPERATIONAL_MESSAGE_VOLUME=UNACCEPTABLE_FOR_OPERATOR_USE
OPEN_MARKET_NATURAL_THREE_PAIR_ACCEPTANCE=PENDING
PRODUCTION_READY=NO
```

The release blocker is not “make Telegram quieter” in isolation. The required order is:

1. determine and stop the recurring native-manager / runsv / crond ownership instability without changing strategy;
2. prove stable control-plane ownership over a meaningful soak window with no new orphan/manager-loss/zombie/crond-owner episodes;
3. inspect and reconcile the ProfitLab pending bytes without bootstrap/reset or historical replay;
4. then harden operator alert presentation so one incident lifecycle is concise and actionable without hiding distinct real failures;
5. finally require a natural market-open same-cycle EURUSD/GBPUSD/USDJPY M15 acceptance on the final runtime.

## Explicit non-actions

```text
DO_NOT_LOWER_THRESHOLDS=YES
DO_NOT_FORCE_SIGNAL_COUNT=YES
DO_NOT_FORCE_TELEGRAM_SIGNAL=YES
DO_NOT_BOOTSTRAP_PROFITLAB=YES
DO_NOT_HIDE_REAL_RUNTIME_FLAPPING_WITH_NOTIFICATION_DEDUP=YES
DO_NOT_DECLARE_READY_FROM_ONE_HEALTHY_SAMPLE=YES
```

This record contains no secret values and does not authorize a new phone mutation by itself.
