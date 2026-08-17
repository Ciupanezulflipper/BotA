# BotA Errors and Silent-Failure Register

Last updated: **2026-08-17 UTC**

Purpose: preserve verified failure classes, current open risks, fixed solutions, and prevention rules without letting old snapshots masquerade as current production truth. Older detailed wording remains available in Git history and dated audits.

Canonical current sources:

- `CONTINUITY_CURRENT.md`
- `AI_START_HERE.md`
- `CHAT_HANDOFF_BOTA.md`
- `audits/PACKAGE6_PHONE_DEPLOY_AND_WEEKEND_RUNTIME_FINDINGS_2026-08-17.md`
- GitHub issue #9

## Current verdict

```text
GITHUB_MAIN_AT_PACKAGE6=028db6ee5a993869bf33a534c4339475981d9357
PR108_RUNTIME_RELEASE=f36836315526fd2be826e8abff1c333004b64b0c
PR108=MERGED
PR113=MERGED
PACKAGE6_PHONE_DEPLOYMENT=PASS
PACKAGE6_12_FILE_RUNTIME_PARITY=PASS
CONTROL_PLANE_PARITY_REPAIR=PASS
LATEST_MANAGER_COUNT=1
LATEST_OWNED=7/7
LATEST_RUNNING=7/7
LATEST_ORPHANED=0
LATEST_DUPLICATES=0
LATEST_FAILURE=zombie_runsv_count:1
WEEKEND_CONTROL_PLANE_STABILITY=FAIL
PROFITLAB_PENDING_BYTES_AT_FIRST_POSTDEPLOY_GATE=271063
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
`runsv` supervisors can survive manager loss as PID-1 orphans. Historical repairs proved recovery, but weekend 2026-08-14..17 evidence proves recurrence; see E026.

### E005 — Device wall-clock leakage into trading semantics
Package #1 moved audited strategy/event-time paths to trusted server epoch. Wall-clock scheduling remains an operational warning.

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
Canonical service root is `$PREFIX/var/service`; resolve active wrappers explicitly.

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
Fixed in Package #1.

### E019 — Nested components established inconsistent cycle time
Fixed by inherited `BOTA_SERVER_EPOCH` through audited strategy/event paths.

### E020 — Stale live singleton daemon blocked manager-owned service
Historical `crond` incident repaired with exact identity checks. Weekend recurrence means the failure family remains operationally relevant; see E026.

### E021 — Health gate checked service liveness without owner lineage
Health must include manager count, owner lineage, duplicate count, service liveness, and singleton-child ownership.

### E022 — Watchdog source existed while persistent startup was unproven
Boot persistence was later proven, but persistent runtime stability is not proven by boot startup alone.

### E023 — Independent watchdog-liveness guardian
PR #89 merged historically. It is not the current release blocker. Weekend evidence proves broader control-plane instability still exists despite guardian/recovery mechanisms.

## New Package 6 findings

### E024 — Deployment preflight configuration-source mismatch

**Observed:** first Package 6 deploy aborted safely with `REQUIRED_CREDENTIALS_MISSING` even though BotA already had `SUPABASE_SERVICE_KEY` in local untracked `config/strategy.env`.

**Proof:** key type was `NEW_SUPABASE_SECRET`; both current publisher headers and `apikey`-only probes returned HTTP 200 against the BotA Supabase project. No secret value was printed.

**Containment:** local ignored `.env.runtime` received the existing key as `SUPABASE_SERVICE_KEY`, mode `0600`; resumed deployment passed.

**Prevention:** deployment preflight and production runtime must share one documented credential-source contract. Never solve this by committing a secret.

### E025 — Transactional runtime manifest did not cover stale control-plane parity

**Observed after successful 12-file deployment:** production integrity failed because `tools/start_native_service_daemon_watchdog.sh` and `tools/control_plane_status.py` did not match the pinned release; launcher mode was `0700` instead of `0755`.

**Repair:** exact pinned blobs were installed and verified:

```text
start_native_service_daemon_watchdog.sh=c383857b7323e1511d71e351a3becd54ca42d682 mode=755
control_plane_status.py=45e7aa5d5b88668720d48efc009cb376c0109783 mode=755
```

**Prevention:** post-deploy integrity must continue to verify release-critical control-plane files even when they are outside the transactional runtime payload.

### E026 — Recurring native-manager / runsv / crond control-plane flapping

**Severity:** CURRENT RELEASE BLOCKER.

The operator reported **89 BotA Telegram messages during the weekend**. The messages show real recurring DEGRADED/RECOVERY transitions, not one unchanged notification repeatedly resent.

Observed 2026-08-14..17 UTC failure families include:

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
```

The latest direct control-plane sample after parity repair was otherwise healthy but still failed on `zombie_runsv_count:1`.

**Key lesson:** self-recovery to 7/7 is not stability proof when degradation repeatedly returns. Do not declare production healthy from one sample.

**Prevention requirement:** close the recurring ownership/manager/zombie/crond failure before presentation tuning or live-market readiness claims.

### E027 — DEADMAN/recovery flapping and operator alert overload

Weekend Telegram evidence includes shadow DEADMAN windows of 118, 218, 245, 197, and 151 minutes followed by recovery.

The resulting 89-message weekend volume is unacceptable for operator use, but the primary defect is not simply notification deduplication. Many messages correspond to distinct real state changes.

**Prevention:** first stabilize runtime; then implement concise incident-lifecycle messaging that preserves first failure, meaningful change/escalation, and recovery without hiding real distinct incidents.

### E028 — ProfitLab post-deploy backlog

The first post-deploy integrity gate measured:

```text
profitlab_pending_bytes:271063
```

**Status:** unresolved until the pending region is inspected/reconciled.

**Prohibited shortcut:** no `--bootstrap`, cursor reset, or skip-to-end solely to turn the gate green.

## Current open risks

```text
CONTROL_PLANE_WEEKEND_FLAPPING=BLOCKER
ZOMBIE_RUNSV_ACCUMULATION=BLOCKER
CROND_OWNER_PIDFILE_RECURRENCE=BLOCKER_FAMILY
PROFITLAB_PENDING_REGION=BLOCKER
TELEGRAM_OPERATOR_ALERT_VOLUME=BLOCKER_FOR_USABILITY_AFTER_RUNTIME_TRUTH
OPEN_MARKET_THREE_PAIR_PROOF=PENDING
STRATEGY_CHANGE=FROZEN
PRODUCTION_READY=NO
```

## Exactly one next engineering action

Use the accumulated weekend evidence to close E026 as one control-plane stability defect. Do not spend another package rediscovering prior architecture or changing strategy. After stability is proven, reconcile E028, then perform natural open-market three-pair acceptance.
