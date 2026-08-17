# BotA Resolved Issues

Last updated: **2026-08-17 UTC**

This file records closed items only. Current blockers belong in `ERRORS.md`, `CONTINUITY_CURRENT.md`, and GitHub issue #9.

## Historical resolved groups

### 2026-04-21 / 2026-04-22
- Yahoo 429 retry storm — RESOLVED.
- `phase=Unknown` market-open contract mismatch — RESOLVED.
- stale watcher lock regression — RESOLVED.

### 2026-05-27
- private Telegram Market Pulse send — RESOLVED.
- daily pulse wrapper and first private live send — RESOLVED for wrapper/send behavior.

### 2026-07-10
- watcher pre-journal dedup observability defect — RESOLVED.

### 2026-08-09 Package #1
Android wall-clock leakage from audited strategy/event-time semantics — RESOLVED / DEPLOYED / LIVE-PROVEN through inherited trusted server epoch. Calendar signed before/after exclusion windows were corrected. Strategy thresholds and pair scope were unchanged.

### 2026-08-09 Package #2 historical repairs
- stale live `crond` singleton incident — RESOLVED at that time;
- PID-1-orphaned BotA `runsv` supervisors — topology repaired at that time;
- watchdog boot persistence/finalizer — DEPLOYED and proven;
- PR #87/#88 runtime dependency/pre-market package — DEPLOYED and proven.

## 2026-08-16 — PR #108 corrective runtime merge

Status: **RESOLVED / MERGED**

```text
PR108_RUNTIME_MERGE=f36836315526fd2be826e8abff1c333004b64b0c
PR108_STATE=MERGED
```

Resolved current-cycle evidence contracts, generation barrier, crash-consistent Telegram/Supabase delivery ordering, delivery hash consistency/atomicity, evidence retention/recovery, and modern GREEN/YELLOW Telegram text presentation. No strategy threshold, pair/timeframe, SL/TP/risk, or provider-policy change was authorized.

## 2026-08-16 — Package 5 / PR #113

Status: **RESOLVED / MERGED**

The reviewed transactional phone deployer remained intentionally pinned to PR #108 runtime release `f36836315526fd2be826e8abff1c333004b64b0c`.

## 2026-08-16 — Package 6 phone deployment

Status: **DEPLOYMENT RESOLVED**

```text
DEPLOYMENT=PASS
RUNTIME_PARITY=PASS
RUNTIME_FILES_VERIFIED=12
WATCHER_COUNT_AFTER=1
DEPLOY_AUDIT=/data/data/com.termux/files/home/BotA/audits/transactional_phone_deploy_20260816T201256Z_31681
```

The first attempt safely failed before mutation because `SUPABASE_SERVICE_KEY` was outside the deployer's read paths. The existing local untracked key was aliased into ignored `.env.runtime`, mode `0600`; no secret was committed.

Two stale control-plane file parity mismatches were then repaired exactly on phone.

## 2026-08-17 — Package 7 / PR #115 manager-loss recovery

Status: **RESOLVED / MERGED / DEPLOYED / REAL PRODUCTION PATH PROVEN**

```text
PR115_MERGE=48db934e44ffebd0e0a419c9ca57554ecf7f372e
WATCHDOG_RUNTIME_BLOB=7dd58b7ea0be3663d380de0a7961eeec482f1c14
PACKAGE7_DEPLOY=PASS
WATCHDOG_SINGLETON=1
```

Production naturally exercised the failure path that Package 7 was written to fix:

```text
EVENT=orphan_tree_drained_before_native
new_manager=26290
drained=[30851,30942,31191,31243,31325,31489,31638]
EVENT=topology_healthy manager=26290
```

Latest direct control plane:

```text
CONTROL_PLANE_HEALTHY=TRUE
OWNED=7/7
RUNNING=7/7
ORPHANED=0
DUPLICATES=0
ZOMBIES=0
```

The recurring manager-loss/orphan amplification blocker is therefore closed. Do not reopen it without new production flapping evidence.

## 2026-08-17 — ProfitLab stale backlog

Status: **RESOLVED WITHOUT STALE REPLAY**

The pending region was classified before mutation:

```text
PENDING_BYTES=372609
PENDING_ROWS=1450
STALE_ELIGIBLE_GREEN_ROWS=5
MALFORMED_ROWS=0
PARTIAL_ROWS=0
```

Exact evidence-backed reconciliation:

```text
OLD_CURSOR=930393
NEW_CURSOR=1303002
STALE_PUBLICATIONS_SENT=0
REMAINING_NEW_BYTES=0
AUDIT_DIRECTORY=audits/profitlab_stale_reconcile_20260817T202901Z
```

Normal scheduled cron then proved:

```text
PENDING_BYTES=0
CURSOR_CAUGHT_UP=TRUE
KEY_AVAILABLE_TO_CRON_ENV=YES
PROFITLAB_DELIVERY=NO_NEW_ROWS x4
```

No bootstrap, cursor reset, or stale ACTIVE signal publication was used.

## 2026-08-17 — Closed-market pre-market integrity

Status: **RESOLVED / PASS**

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

## Still not resolved

```text
OPEN_MARKET_PIPELINE_PROOF=PENDING
NATURAL_EURUSD_GBPUSD_USDJPY_M15_ACCEPTANCE=PENDING
TELEGRAM_OPERATIONAL_INCIDENT_LIFECYCLE_USABILITY=PENDING
PRODUCTION_READY=NO
```

A genuine HOLD/reject is a valid live acceptance result. Do not lower thresholds or force a signal.

Canonical closure evidence: `audits/PACKAGE7_RUNTIME_AND_PROFITLAB_CLOSURE_2026-08-17.md`.
