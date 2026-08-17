# Package 7 Runtime and ProfitLab Closure — 2026-08-17

This record captures the production-phone evidence that closed the Package 7 control-plane recovery blocker and the ProfitLab stale backlog. It does not authorize strategy changes, threshold changes, forced signals, or a production-ready declaration before natural open-market acceptance.

## Release identity

```text
PACKAGE7_PR=115
PACKAGE7_RELEASE=48db934e44ffebd0e0a419c9ca57554ecf7f372e
PACKAGE7_WATCHDOG_BLOB=7dd58b7ea0be3663d380de0a7961eeec482f1c14
GITHUB_MAIN_AT_DOC_REFRESH=b0f30df9aeade1711b7e2c45045b2bc95c9954b4
```

Current `main` is four no-op commits ahead of Package 7 because two accidental empty placeholder create/delete pairs were written through the GitHub connector. GitHub comparison between `48db934e...` and `b0f30df...` reports zero changed files. The repository tree is content-equivalent. No force rewrite of `main` is authorized without explicit operator approval.

## Package 7 phone deployment

The watchdog was deployed narrowly from exact merged commit `48db934e...` with launcher parity verification, backup, atomic install, graceful watchdog restart, singleton verification, and runtime blob verification.

```text
EXPECTED_WATCHDOG_BLOB=7dd58b7ea0be3663d380de0a7961eeec482f1c14
INSTALLED_WATCHDOG_BLOB=7dd58b7ea0be3663d380de0a7961eeec482f1c14
WATCHDOG_COUNT_BEFORE=1
WATCHDOG_COUNT_AFTER=1
PACKAGE7_DEPLOY=PASS
PACKAGE7_RUNTIME_BLOB=7dd58b7ea0be3663d380de0a7961eeec482f1c14
```

Primary deployment audit:

`/data/data/com.termux/files/home/BotA/audits/package7_phone_deploy_20260817T200230Z`

A repeated operator paste restarted the already-correct watchdog once more and produced a second audit directory:

`/data/data/com.termux/files/home/BotA/audits/package7_phone_deploy_20260817T200406Z`

No strategy/runtime payload beyond the watchdog file was changed by Package 7 deployment.

## Real production manager-loss recovery proof

Before Package 7, weekend evidence repeatedly showed manager loss followed by mixed ownership, orphaned `runsv`, crond lineage/pidfile failures, zombie accumulation, and DEGRADED/RECOVERY flapping.

After Package 7 deployment, production naturally lost the previous manager. The new watchdog recorded the exact intended recovery sequence:

```text
EVENT=orphan_tree_drained_before_native manager=26290 drained=[30851, 30942, 31191, 31243, 31325, 31489, 31638] error=None
EVENT=topology_healthy manager=26290 drained=None error=None
```

This proves the seven old PID-1 orphan supervisors were drained before the replacement native manager converged.

Latest direct control-plane state:

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

## Shared Termux service-root finding

The active service root contains 9 service directories:

```text
bota-closer
bota-heartbeat
bota-shadow
bota-supervisor
bota-updater
bota-watcher
crond
ssh-agent
sshd
```

Two transient zombie `runsv` rows were observed under manager 26290, then disappeared without another restart. Their cmdlines were empty, while the shared manager also owns `sshd` and `ssh-agent`, so those transient zombie rows could not be attributed to a BotA service.

Conclusion: do not reopen broad runit surgery unless new ownership/orphan/crond flapping is observed.

## ProfitLab stale-region classification

Final pre-reconciliation measurement:

```text
ALERTS_SIZE=1303002
CURSOR_OFFSET=930393
PENDING_BYTES=372609
CURSOR_LINE_BOUNDARY=TRUE
PENDING_ROWS=1450
ELIGIBLE_GREEN_ROWS=5
INELIGIBLE_ROWS=1445
MALFORMED_ROWS=0
PARTIAL_ROWS=0
ELIGIBLE_BY_PAIR={"GBPUSD":2,"USDJPY":3}
ELIGIBLE_BY_DIRECTION={"BUY":5}
CLASSIFIED_REGION_SHA256=fba1bc80ecf68cba3c8574236748fb939e2e1e1b4abb70f5b3e22969771caad6
```

The five eligible historical GREEN rows were:

```text
2026-08-10T13:51:37-0400 USDJPY BUY score=81.60 entry=159.16400
2026-08-10T13:57:01-0400 USDJPY BUY score=81.60 entry=159.16400
2026-08-12T08:11:02-0400 GBPUSD BUY score=84.90 entry=1.35379
2026-08-12T08:16:28-0400 GBPUSD BUY score=84.90 entry=1.35379
2026-08-17T07:12:22-0400 USDJPY BUY score=76.30 entry=159.26600
```

Supabase read-only checks immediately before reconciliation showed no ACTIVE USDJPY or GBPUSD signal. Two stale rows also matched historical CLOSED records already present in Supabase.

## ProfitLab reconciliation

The exact classified region was reconciled under the ProfitLab worker lock. The action did not use `--bootstrap`, did not reset to an unverified file end, and did not publish any stale signal.

```text
PROFITLAB_RECONCILE=PASS
OLD_CURSOR=930393
NEW_CURSOR=1303002
CURRENT_ALERTS_SIZE=1303002
REMAINING_NEW_BYTES=0
STALE_PUBLICATIONS_SENT=0
AUDIT_DIRECTORY=audits/profitlab_stale_reconcile_20260817T202901Z
```

Normal scheduled worker proof after reconciliation:

```text
ALERTS_SIZE=1303002
CURSOR_OFFSET=1303002
PENDING_BYTES=0
CURSOR_CAUGHT_UP=TRUE
KEY_AVAILABLE_TO_CRON_ENV=YES
PROFITLAB_DELIVERY=NO_NEW_ROWS
PROFITLAB_DELIVERY=NO_NEW_ROWS
PROFITLAB_DELIVERY=NO_NEW_ROWS
PROFITLAB_DELIVERY=NO_NEW_ROWS
```

Therefore:

```text
PROFITLAB_RECONCILED=YES
```

The earlier `failed_missing_service_key` / `RETRY_REQUIRED` lines are historical log entries from the stuck cursor before the local runtime env alias was corrected.

## Final closed-market integrity gate

The read-only production integrity gate was executed against Package 7 release identity:

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
MARKET_OPEN=False
PROFITLAB_PENDING_BYTES=0
FAILURE_COUNT=0
```

Phone audit:

`/data/data/com.termux/files/home/BotA/audits/pre_market_integrity_20260817T203832Z.json`

The closed market is expected and is not a failure. This gate performs no watcher execution, Telegram send, ProfitLab bootstrap, strategy mutation, or runtime mutation.

## Current release classification

```text
PACKAGE7_REAL_RECOVERY=PASS
CURRENT_CONTROL_PLANE=HEALTHY
PROFITLAB_RECONCILED=YES
CLOSED_MARKET_PREMARKET_INTEGRITY=PASS
OPEN_MARKET_THREE_PAIR_LIVE_PROOF=PENDING
TELEGRAM_INCIDENT_LIFECYCLE_USABILITY=PENDING
PRODUCTION_READY=NO
```

## Remaining acceptance only

During the next configured open-market window:

1. verify the stable runtime no longer emits `INTERNAL_ERROR:MARKET_OPEN` or missing current M15 decisions;
2. collect one natural same-cycle EURUSD:M15 / GBPUSD:M15 / USDJPY:M15 acceptance;
3. genuine HOLD/reject outcomes are valid and do not need to produce Telegram;
4. if a genuine GREEN/YELLOW qualifies, verify the modern text-only Telegram card and normal ProfitLab handling;
5. confirm operational Telegram incident lifecycle is concise enough without hiding distinct failures.

## Explicit non-actions

```text
DO_NOT_LOWER_THRESHOLDS=YES
DO_NOT_FORCE_SIGNAL_COUNT=YES
DO_NOT_FORCE_TELEGRAM_SIGNAL=YES
DO_NOT_BOOTSTRAP_PROFITLAB=YES
DO_NOT_RESET_PROFITLAB_CURSOR_TO_HIDE_BACKLOG=YES
DO_NOT_REOPEN_CONTROL_PLANE_WITHOUT_NEW_FLAPPING_EVIDENCE=YES
DO_NOT_DECLARE_READY_BEFORE_NATURAL_OPEN_MARKET_PROOF=YES
```

No secret values are recorded in this document.
