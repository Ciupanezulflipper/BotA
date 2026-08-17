# BotA AI Start Here

Last updated: **2026-08-17 UTC**

Read this before proposing BotA commands, code, service, strategy, Telegram, provider, Supabase, ProfitLab, deployment, or Android/Termux changes.

## Current authoritative truth

```text
GITHUB_MAIN=028db6ee5a993869bf33a534c4339475981d9357
PR108=MERGED
PR108_RUNTIME_RELEASE=f36836315526fd2be826e8abff1c333004b64b0c
PR113=MERGED
PACKAGE5_TRANSACTIONAL_DEPLOYER=COMPLETE
PACKAGE6_PHONE_DEPLOYMENT=PASS
PACKAGE6_12_FILE_RUNTIME_PARITY=PASS
PACKAGE6_POSTDEPLOY_ACCEPTANCE=BLOCKED

PAIRS=EURUSD GBPUSD USDJPY
TIMEFRAMES=M15
TELEGRAM_ENABLED=1
DRY_RUN_MODE=0
POLICY_B_ENABLED=1
POLICY_B_SCORE_MIN=70
POLICY_B_ADX_MAX=30
NEWS_ON=0

CURRENT_CONTROL_PLANE_SAMPLE_MANAGER_COUNT=1
CURRENT_CONTROL_PLANE_SAMPLE_OWNED=7/7
CURRENT_CONTROL_PLANE_SAMPLE_RUNNING=7/7
CURRENT_CONTROL_PLANE_SAMPLE_ORPHANED=0
CURRENT_CONTROL_PLANE_SAMPLE_DUPLICATES=0
CURRENT_CONTROL_PLANE_SAMPLE_LIVE_CROND=1
CURRENT_CONTROL_PLANE_SAMPLE_FAILURE=zombie_runsv_count:1
WEEKEND_CONTROL_PLANE_STABILITY=FAIL
PROFITLAB_PENDING_BYTES_AT_FIRST_POSTDEPLOY_GATE=271063
OPEN_MARKET_THREE_PAIR_LIVE_PROOF=PENDING
PRODUCTION_READY=NO
```

Do not reconstruct present state from the old 2026-08-09 readiness files. The current detailed record is `audits/PACKAGE6_PHONE_DEPLOY_AND_WEEKEND_RUNTIME_FINDINGS_2026-08-17.md`, with GitHub issue #9 as the mutable tracker.

## What Package 6 actually proved

The phone fetched `origin/main` at exact SHA `028db6ee5a993869bf33a534c4339475981d9357`, verified the transactional deployer blob, and started with exactly one `bota-watcher` runsv supervisor.

The first deploy attempt failed closed before mutation because `SUPABASE_SERVICE_KEY` was absent from the deployer's supported config read paths. The existing production key was already present in local untracked `config/strategy.env`; it is a new Supabase secret key and returned HTTP 200 with both the current publisher headers and `apikey`-only. The value was never printed or committed. A local ignored `.env.runtime` alias was installed mode `0600`.

The resumed transactional deployment then passed:

```text
DEPLOYMENT=PASS
RUNTIME_FILES_VERIFIED=12
WATCHER_COUNT_AFTER=1
RUNTIME_RELEASE=f36836315526fd2be826e8abff1c333004b64b0c
```

Two stale control-plane runtime files were then repaired to exact release blobs and mode `0755`:

```text
tools/start_native_service_daemon_watchdog.sh=c383857b7323e1511d71e351a3becd54ca42d682
tools/control_plane_status.py=45e7aa5d5b88668720d48efc009cb376c0109783
CONTROL_PLANE_PARITY_REPAIR=PASS
```

## Weekend evidence changes the release diagnosis

The operator reported **89 BotA Telegram messages during the weekend**. The stream contains many distinct DEGRADED → RECOVERY and DEADMAN → RECOVERY transitions from 2026-08-14 through 2026-08-17 UTC.

Observed failure classes include manager loss, 1–6/7 service ownership, PID-1 orphaning, crond ownership/pidfile failures, increasing zombie `runsv` counts, and repeated multi-hour shadow DEADMAN periods.

Therefore the primary blocker is **recurring runtime/control-plane flapping**, not merely notification duplication. Do not silence or deduplicate real failures to make the channel look clean. Operator alert presentation can be coalesced only after the incident lifecycle remains truthful.

## Current production freeze

```text
DO_NOT_LOWER_THRESHOLDS=YES
DO_NOT_FORCE_SIGNAL_COUNT=YES
DO_NOT_FORCE_TELEGRAM_TEST_SIGNAL=YES
DO_NOT_BOOTSTRAP_PROFITLAB=YES
DO_NOT_RESET_PROFITLAB_CURSOR_TO_HIDE_BACKLOG=YES
DO_NOT_HIDE_RUNTIME_FLAPPING_WITH_ALERT_DEDUP=YES
DO_NOT_DECLARE_READY_FROM_ONE_HEALTHY_SAMPLE=YES
```

No readiness fix may manufacture signals or change trading strategy to create activity.

## Mandatory operating model

```text
GitHub connector / reviewed PR -> source, review, CI, documentation
Phone / Termux               -> bounded runtime evidence and approved deployment
```

Never equate merged, deployed, runtime-parity PASS, one healthy sample, stable production, and live-market acceptance.

Do not push directly to `main`. Repository changes go through a reviewable branch/PR unless the user explicitly authorizes a merge.

## Read first

1. `CONTINUITY_CURRENT.md`
2. `audits/PACKAGE6_PHONE_DEPLOY_AND_WEEKEND_RUNTIME_FINDINGS_2026-08-17.md`
3. GitHub issue #9
4. `ERRORS.md`
5. `RESOLVED.md`

## Exactly one next engineering action

Close the recurring native-manager / runsv / crond ownership instability using the accumulated weekend evidence. Treat `zombie_runsv_count`, manager loss, orphan ownership, crond pidfile/parent drift, and DEADMAN episodes as one control-plane stability problem until causally separated. Do not spend another package on strategy, presentation, new tools, or unrelated static debt before this runtime blocker is closed.
