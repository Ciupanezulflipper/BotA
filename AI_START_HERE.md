# BotA AI Start Here

Last updated: **2026-08-17 UTC**

Read this before proposing BotA commands, code, service, strategy, Telegram, provider, Supabase, ProfitLab, deployment, or Android/Termux changes.

## Current authoritative truth

```text
GITHUB_MAIN_AT_DOC_REFRESH=b0f30df9aeade1711b7e2c45045b2bc95c9954b4
PACKAGE7_RELEASE=48db934e44ffebd0e0a419c9ca57554ecf7f372e
PR108=MERGED
PR113=MERGED
PR115=MERGED
PACKAGE6_PHONE_DEPLOYMENT=PASS
PACKAGE7_REAL_MANAGER_LOSS_RECOVERY=PASS
CURRENT_CONTROL_PLANE=HEALTHY
PROFITLAB_RECONCILED=YES
CLOSED_MARKET_PREMARKET_INTEGRITY=PASS
OPEN_MARKET_THREE_PAIR_LIVE_PROOF=PENDING
PRODUCTION_READY=NO

PAIRS=EURUSD GBPUSD USDJPY
TIMEFRAMES=M15
TELEGRAM_ENABLED=1
DRY_RUN_MODE=0
POLICY_B_ENABLED=1
POLICY_B_SCORE_MIN=70
POLICY_B_ADX_MAX=30
NEWS_ON=0
```

`main` is four no-op commits ahead of Package 7 because two accidental empty placeholder create/delete pairs were written through the GitHub connector. GitHub comparison from `48db934e...` to `b0f30df...` shows zero changed files. Do not rewrite `main` history without explicit operator authorization.

## What is now closed

Package 7 was deployed with exact watchdog blob:

```text
7dd58b7ea0be3663d380de0a7961eeec482f1c14
```

Production then exercised the real manager-loss path. The watchdog drained all seven old PID-1 orphan supervisors before native manager replacement and immediately returned to a healthy topology:

```text
EVENT=orphan_tree_drained_before_native
new_manager=26290
drained=[30851,30942,31191,31243,31325,31489,31638]
EVENT=topology_healthy manager=26290
```

Latest direct control-plane evidence:

```text
CONTROL_PLANE_HEALTHY=TRUE
MANAGER_COUNT=1
MANAGER_PID=26290
OWNED=7/7
RUNNING=7/7
ORPHANED=0
DUPLICATES=0
ZOMBIES=0
WATCHDOG_SINGLETON=YES
```

The Termux service root contains BotA's seven services plus `sshd` and `ssh-agent`; two transient zombie `runsv` rows disappeared without another restart and could not be attributed to a BotA service.

ProfitLab stale backlog was classified and reconciled without bootstrap/reset or stale publication:

```text
OLD_CURSOR=930393
NEW_CURSOR=1303002
CLASSIFIED_ROWS=1450
STALE_ELIGIBLE_GREEN_ROWS=5
STALE_PUBLICATIONS_SENT=0
PENDING_BYTES=0
PROFITLAB_DELIVERY=NO_NEW_ROWS x4
PROFITLAB_RECONCILED=YES
```

The final closed-market read-only integrity gate passed all checks:

```text
PRE_MARKET_HEALTHY=TRUE
PRE_MARKET_RC=0
CONTROL_PLANE=TRUE
WATCHDOG_OWNERSHIP=TRUE
BOOT_PERSISTENCE=TRUE
CRON_OWNERSHIP=TRUE
RUNTIME_PARITY=TRUE
PRODUCTION_CONFIG=TRUE
PROFITLAB=TRUE
MARKET_GATE=TRUE
PROGRESS=TRUE
TRUSTED_CLOCK=TRUE
MARKET_STATUS=Closed
PROFITLAB_PENDING_BYTES=0
FAILURE_COUNT=0
```

Audit file on the production phone:

`/data/data/com.termux/files/home/BotA/audits/pre_market_integrity_20260817T203832Z.json`

## Production freeze

```text
DO_NOT_LOWER_THRESHOLDS=YES
DO_NOT_FORCE_SIGNAL_COUNT=YES
DO_NOT_FORCE_TELEGRAM_TEST_SIGNAL=YES
DO_NOT_BOOTSTRAP_PROFITLAB=YES
DO_NOT_RESET_PROFITLAB_CURSOR_TO_HIDE_BACKLOG=YES
DO_NOT_REOPEN_CONTROL_PLANE_WITHOUT_NEW_FLAPPING_EVIDENCE=YES
DO_NOT_DECLARE_READY_BEFORE_NATURAL_OPEN_MARKET_PROOF=YES
```

No readiness action may manufacture a signal or change strategy to create activity.

## Mandatory operating model

```text
GitHub reviewed branch/PR -> source, review, CI, documentation
Phone / Termux          -> bounded runtime evidence and approved deployment
```

Do not equate merged, deployed, parity PASS, closed-market integrity PASS, and live-market acceptance.

## Read first

1. `CONTINUITY_CURRENT.md`
2. `audits/PACKAGE7_RUNTIME_AND_PROFITLAB_CLOSURE_2026-08-17.md`
3. GitHub issue #9
4. `ERRORS.md`
5. `RESOLVED.md`

## Exactly one next engineering action

During the next configured open-market window, collect one natural same-cycle EURUSD:M15 / GBPUSD:M15 / USDJPY:M15 acceptance on the stable runtime and verify that `INTERNAL_ERROR:MARKET_OPEN` / missing current M15 decisions do not recur. Genuine HOLD/reject outcomes are valid. If a genuine GREEN/YELLOW occurs, verify modern Telegram delivery and normal ProfitLab handling. Do not force a trade.
