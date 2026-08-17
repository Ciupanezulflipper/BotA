# BotA Errors and Silent-Failure Register

Last updated: **2026-08-17 UTC**

Purpose: preserve verified failure classes, current open risks, fixed solutions, and prevention rules without letting old snapshots masquerade as current production truth.

Canonical current sources:

- `CONTINUITY_CURRENT.md`
- `AI_START_HERE.md`
- `CHAT_HANDOFF_BOTA.md`
- `audits/PACKAGE7_RUNTIME_AND_PROFITLAB_CLOSURE_2026-08-17.md`
- GitHub issue #9

## Current verdict

```text
PACKAGE7_RELEASE=48db934e44ffebd0e0a419c9ca57554ecf7f372e
PR108=MERGED
PR113=MERGED
PR115=MERGED
PACKAGE6_PHONE_DEPLOYMENT=PASS
PACKAGE7_MANAGER_LOSS_RECOVERY=PASS
CURRENT_CONTROL_PLANE=HEALTHY
PROFITLAB_RECONCILED=YES
CLOSED_MARKET_PREMARKET_INTEGRITY=PASS
OPEN_MARKET_THREE_PAIR_LIVE_PROOF=PENDING
PRODUCTION_READY=NO
```

## Historical failure classes retained

### E001 — Scope branching / mixed phases
Repository, runtime, documentation, deployment, and strategy work were mixed. Prevention: one actual release blocker at a time.

### E002 — Repository state mistaken for deployed runtime
GitHub HEAD is not deployment identity. Prevention: immutable source pin + deployed blob/mode parity + runtime evidence.

### E003 — Duplicate execution ownership
Cron/runit/boot/wrappers can own the same job. Current watcher rule remains one runit owner.

### E004 — Dead manager / orphaned service topology
`runsv` supervisors can survive manager loss as PID-1 orphans. Package 7 now closes the recovery amplification path; see E026.

### E005 — Device wall-clock leakage into trading semantics
Audited strategy/event-time paths use trusted server epoch. Wall-clock scheduling remains an operational warning.

### E006 — Partial pair observability
Health cannot pass while a required pair disappears. Current scope: EURUSD/GBPUSD/USDJPY M15.

### E007 — Pre-journal dedup / lost decision evidence
Persist decisions independently from delivery/dedup state.

### E008 — Inner watcher failure hidden by semantic aggregation
Current inner nonzero execution must dominate semantic aggregation.

### E009 — Watcher cycle without terminal outcome
Require cycle ID, append-only evidence, and authoritative terminal outcome.

### E010 — Moving GitHub release target during deployment
Use immutable release pins and verify immediately before mutation.

### E011 — Non-executable runit wrapper
Git mode matters; watcher wrapper must be executable.

### E012 — Wrong service-root assumption
Canonical Termux service root is `$PREFIX/var/service`; the manager also owns non-BotA services such as `sshd` and `ssh-agent`.

### E013 — Deployment manifest drift
Deployment manifest must be exact, pinned, reviewed, and parity-verified.

### E014 — ProfitLab cursor replay risk
Do not bootstrap/reset production cursor to make a gate green. Historical rows must not be replayed accidentally.

### E015 — Persisted compact-state schema label lag
Bookkeeping debt unless behavior changes.

### E016 — Stale event mistaken for current failure
Timestamp/cycle must be compared against deployment and current boot.

### E017 — Stale overlapping PRs
Old-base PRs are not deployment authority merely because they remain open.

### E018 — Calendar before/after exclusion-window sign inversion
Resolved in Package #1.

### E019 — Nested components established inconsistent cycle time
Resolved by inherited `BOTA_SERVER_EPOCH` through audited strategy/event paths.

### E020 — Stale live singleton daemon blocked manager-owned service
Historical `crond` incident repaired with exact identity checks; Package 7 later closed the broader manager-loss recovery amplification path.

### E021 — Health gate checked service liveness without owner lineage
Health must include manager count, owner lineage, duplicate count, service liveness, and singleton-child ownership.

### E022 — Watchdog source existed while persistent startup was unproven
Boot persistence is now proven and the latest pre-market integrity gate passes.

### E023 — Independent watchdog-liveness guardian
Historical safeguard; not the current release blocker.

### E024 — Deployment preflight configuration-source mismatch

**Observed:** first Package 6 deploy safely aborted with `REQUIRED_CREDENTIALS_MISSING` although the service key already existed in local untracked `config/strategy.env`.

**Containment:** the existing key was aliased locally into ignored `.env.runtime`, mode `0600`; no secret value was printed or committed.

**Prevention:** deployment preflight and runtime must share one documented credential-source contract.

### E025 — Transactional runtime manifest did not cover stale control-plane parity

**Observed:** two control-plane files were stale after the 12-file Package 6 deployment.

**Repair:** exact release blobs/modes were restored and verified.

**Prevention:** post-deploy integrity must verify release-critical control-plane files even when outside the transactional payload.

### E026 — Recurring native-manager / runsv / crond control-plane flapping

**Status: RESOLVED BY PACKAGE 7 / REAL PRODUCTION RECOVERY PROVEN.**

Weekend evidence showed repeated manager loss, partial ownership, PID-1 orphans, crond ownership/pidfile failures, and zombie accumulation.

Package 7 changed manager-loss recovery ordering so a safe PID-1 orphan forest is drained before starting a replacement native manager. Production then naturally exercised that path:

```text
EVENT=orphan_tree_drained_before_native
new_manager=26290
drained=[30851,30942,31191,31243,31325,31489,31638]
EVENT=topology_healthy manager=26290
```

Latest direct state:

```text
CONTROL_PLANE_HEALTHY=TRUE
OWNED=7/7
RUNNING=7/7
ORPHANED=0
DUPLICATES=0
ZOMBIES=0
```

Do not reopen E026 without new real ownership/orphan/crond flapping evidence.

### E027 — DEADMAN/recovery flapping and operator alert overload

**Status: UNDERLYING CONTROL-PLANE CAUSE CLOSED; PRESENTATION FOLLOW-UP REMAINS.**

The weekend 89-message volume was unacceptable. Runtime stabilization came first. Remaining work is to confirm incident lifecycle messaging is concise without hiding distinct real failures.

### E028 — ProfitLab post-deploy backlog

**Status: RESOLVED.**

The pending region was 372609 bytes at final classification, containing 1450 rows and 5 eligible historical GREEN rows. It was reconciled under the worker lock without bootstrap/reset and without stale publication:

```text
OLD_CURSOR=930393
NEW_CURSOR=1303002
STALE_PUBLICATIONS_SENT=0
PENDING_BYTES=0
PROFITLAB_DELIVERY=NO_NEW_ROWS x4
```

### E029 — GitHub no-op commit pollution

**Status: CONTAINED, NOT HISTORY-REWRITTEN.**

Two accidental empty placeholder create/delete pairs produced four commits after Package 7. GitHub compare from `48db934e...` to `b0f30df...` shows zero changed files. Repository content is unchanged. Do not force-rewrite `main` without explicit operator authorization.

## Current open risks

```text
CONTROL_PLANE=HEALTHY
PROFITLAB=RECONCILED
CLOSED_MARKET_INTEGRITY=PASS
OPEN_MARKET_PIPELINE_PROOF=PENDING
NATURAL_THREE_PAIR_M15_ACCEPTANCE=PENDING
TELEGRAM_INCIDENT_LIFECYCLE_USABILITY=PENDING
STRATEGY_CHANGE=FROZEN
PRODUCTION_READY=NO
```

## Exactly one next engineering action

During the next configured market-open window, collect one natural same-cycle EURUSD:M15 / GBPUSD:M15 / USDJPY:M15 acceptance and verify that `INTERNAL_ERROR:MARKET_OPEN` / missing current M15 decisions do not recur. Genuine HOLD/reject outcomes are valid. Do not force a signal.
