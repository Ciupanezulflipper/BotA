# BotA Chat Handoff

Last updated: **2026-08-17 UTC**

Read this first in any new AI session before proposing BotA changes.

## Current grounded answer

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
OPEN_MARKET_THREE_PAIR_PROOF=PENDING
PRODUCTION_READY=NO
```

## Scope

Do not expand BotA work into unrelated audits, tools, repos, or strategy changes. The production scope remains EURUSD/GBPUSD/USDJPY M15 with the existing thresholds and modern text-only Telegram trade presentation.

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

No threshold lowering, forced signals, fake Telegram trades, or chart reintroduction is authorized.

## Package 7 result

Production watchdog blob:

`7dd58b7ea0be3663d380de0a7961eeec482f1c14`

Real production manager-loss recovery occurred after deployment:

```text
EVENT=orphan_tree_drained_before_native
new_manager=26290
drained=[30851,30942,31191,31243,31325,31489,31638]
EVENT=topology_healthy manager=26290
```

Latest direct control plane:

```text
CONTROL_PLANE_HEALTHY=TRUE
MANAGER_PID=26290
OWNED=7/7
RUNNING=7/7
ORPHANED=0
DUPLICATES=0
ZOMBIES=0
WATCHDOG_SINGLETON=YES
```

Two transient zombie `runsv` rows disappeared without another restart. The Termux service root is shared by BotA plus `sshd` and `ssh-agent`, and the zombie cmdlines were empty, so those rows could not be attributed to a BotA service. Do not reopen runit surgery unless new real ownership/orphan/crond flapping appears.

## ProfitLab result

The 372609-byte stale region was classified before mutation: 1450 rows, 5 eligible historical GREEN rows, 0 malformed, 0 partial. Reconciliation advanced only the exact verified region and published no stale trade.

```text
OLD_CURSOR=930393
NEW_CURSOR=1303002
STALE_PUBLICATIONS_SENT=0
PENDING_BYTES=0
CURSOR_CAUGHT_UP=TRUE
KEY_AVAILABLE_TO_CRON_ENV=YES
PROFITLAB_DELIVERY=NO_NEW_ROWS x4
PROFITLAB_RECONCILED=YES
```

No `--bootstrap` or reset-to-end shortcut was used.

## Closed-market final gate

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

Phone audit:

`/data/data/com.termux/files/home/BotA/audits/pre_market_integrity_20260817T203832Z.json`

## GitHub identity note

Current `main` is four no-op commits ahead of Package 7 due to two accidental empty placeholder create/delete pairs. GitHub compare shows zero changed files between `48db934e...` and `b0f30df...`. Do not force-rewrite `main` without explicit operator authorization.

## Remaining blockers

1. natural open-market same-cycle EURUSD:M15 / GBPUSD:M15 / USDJPY:M15 acceptance;
2. verify `INTERNAL_ERROR:MARKET_OPEN` and missing current M15 decisions do not recur on the stable runtime;
3. if a genuine GREEN/YELLOW occurs, verify modern Telegram delivery plus normal ProfitLab handling;
4. confirm operational Telegram incident lifecycle is concise enough without hiding distinct failures.

A genuine HOLD/reject is a valid acceptance outcome. Do not manufacture a trade.

## Exactly one next action

Wait for the next configured market-open window and collect the natural three-pair M15 acceptance. No more phone mutation is justified tonight by current evidence.
