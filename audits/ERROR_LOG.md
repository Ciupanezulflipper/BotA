# BotA Runtime Error Log

Last updated: **2026-08-09 UTC**

This is the canonical compact error/prevention index. Full historical detail remains in Git history, `ERRORS.md`, dated audit records, and GitHub issue/PR history.

Current sources:

- `audits/PHONE_DEPLOYMENT_WEEKEND_PROOF_2026-08-09.md`
- `CONTINUITY_CURRENT.md`
- `AI_START_HERE.md`
- `CHAT_HANDOFF_BOTA.md`
- `DECISIONS.md`
- `ERRORS.md`
- GitHub issue #9

## Current status

```text
DEPLOYED_RELEASE=f52f326cdbc9e9a16dd60666808a35fb839f10ad
DEPLOYED_TO_PHONE=PASS
RUNTIME_PARITY=PASS
ACTIVE_WRAPPER_MODE=755
CONTROL_PLANE=HEALTHY_7_OF_7
ACTIVE_WATCHER_CRON=0
PAIRS=EURUSD GBPUSD USDJPY
TIMEFRAMES=M15
LIVE_CLOSED_MARKET_CYCLE=PASS
ISOLATED_MONDAY_HARNESS=PASS
PROFITLAB_CURSOR=PRESERVED_AT_EOF
LOCAL_CLOCK=DRIFT_WARN
OPEN_MARKET_THREE_PAIR_LIVE_PROOF=PENDING
MONDAY_READY=NO
```

## Canonical error index

### E001 — Scope branching
Repository, runtime, documentation, deployment, and strategy work were mixed.

**Prevention:** one phase, evidence domain, and acceptance gate per package. Keep current-state files synchronized with actual deployed truth.

### E002 — Release/worktree identity confusion
GitHub `main`, phone worktree HEAD, and deployed runtime can be different states.

**Prevention:** immutable approved SHA + bounded deployed blob/mode parity + runtime config + active-wrapper proof + live-cycle evidence. Never infer production solely from Git branch/HEAD.

### E003 — Duplicate execution sources
Cron, runit, boot files, and wrappers can own the same component.

**Current proof:** watcher direct cron count `0`; seven runit services running under one manager.

**Prevention:** re-prove current unique owner during the real open-market gate.

### E004 — Dead manager with surviving/orphaned supervisors
Process presence can look healthy after control-plane ownership has failed.

**Current status:** resolved in the verified post-deployment topology.

**Prevention:** count manager, required services, orphaned rows, and duplicate owners explicitly.

### E005 — Clock-domain mixing
Android wall clock can diverge from server UTC and monotonic clocks.

**Current warning:** approximately `-3621s` wall-clock drift; trusted server clock healthy.

**Prevention:** server epoch for market/lifecycle semantics; CLOCK_BOOTTIME/monotonic for same-boot freshness; fail closed on untrusted time. Keep cron scheduling risk visible.

### E006 — Partial pair observability
Health can falsely pass while a production pair disappears.

**Current fix:** three-pair EURUSD/GBPUSD/USDJPY M15 observability contract with safe defaults.

**Remaining proof:** first real open-market cycle must show all three current decisions.

### E007 — Pre-journal dedup / lost decision evidence
Delivery state previously interfered with full decision journaling.

**Prevention:** persist completed decision evidence independently from Telegram/Supabase dedup/delivery state.

### E008 — Inner watcher failure hidden by semantic aggregation
Existing/partial decision evidence can look healthy even when the current watcher execution failed.

**Prevention:** nonzero inner execution dominates semantic aggregate and surfaces operational failure.

### E009 — Watcher cycle without terminal outcome
Heartbeat/process liveness is not sufficient evidence of useful pipeline progress.

**Current fix:** gated cycle, coherent cycle ID, append-only ledger, authoritative terminal outcome.

**Post-deployment proof:** `MARKET_CLOSED / MARKET_CLOSED_SUNDAY` recorded using `server_epoch`.

### E010 — Moving `main` during deployment
A branch-name deployment can silently change underneath the operator.

**Observed:** release-pin mismatch caused a safe pre-mutation abort.

**Prevention:** immutable SHA and final remote-pin recheck immediately before mutation.

### E011 — Non-executable runit wrapper
Correct contents with Git mode `100644` made `bota-watcher` unable to start.

**Observed containment:** activation failed; rollback restored the prior runtime.

**Fix:** PR #81 changed `ops/runit/bota-watcher.run` to `100755`.

**Prevention:** release parity includes executable modes, not hashes only.

### E012 — Wrong runit service-root assumption
A verification script assumed `crond` lived under `${HOME}/.config/bota-sv`.

**Observed containment:** pre-deployment gate aborted before mutation.

**Current rule:** enumerate services through `$PREFIX/var/service`; resolve the active watcher wrapper separately to its physical path.

### E013 — Deployment manifest drift
Generated deployment instructions can diverge from the authoritative parity audit.

**Prevention:** exact audited manifest, expected file count, immutable source verification, and only explicitly approved phone-config changes.

### E014 — ProfitLab cursor replay risk
Re-bootstrap after activation could replay historical alert rows.

**Current proof:** `offset=897734`, `alerts_size=897734`, `pending_bytes=0`.

**Prevention:** preserve cursor; do not run `--bootstrap` on current production.

### E015 — Persisted state schema label lag
Live compact state can preserve an older top-level schema label while new events use the current event schema.

**Current observation:** compact state label `1.0`, new watcher event `1.1`.

**Classification:** bookkeeping debt, not a weekend readiness blocker.

### E016 — Stale event mistaken for current failure
An old component failure can remain in compact state after deployment.

**Current example:** shadow failure record predates the successful deployment while the live shadow service is running.

**Prevention:** compare event/cycle timestamps with deployment time and demand fresh component evidence when the market opens.

### E017 — Stale overlapping PRs
Old-base readiness work can remain open and look actionable after the production architecture has moved.

**Current containment:** PR #77 closed unmerged and documented as superseded by the merged/deployed PR #78 + PR #81 path.

**Prevention:** close superseded PRs explicitly; do not merge stale implementations wholesale.

## Historical strategy evidence — preserved, not a current operational error

```text
PUBLISHED_OUTCOMES=13
WINS=3
LOSSES=9
CANCELLED=1
TOTAL_PIPS=-71.40
MATCHED_OUTCOMES=9
UNMATCHED_OUTCOMES=4
UNEXPLAINED_GAP_COUNT=0
```

The historical signal-quality evidence justified controlled strategy investigation and Policy B, but missing live runtime evidence must never be “fixed” by lowering thresholds.

## Current unresolved risks

```text
ANDROID_WALL_CLOCK_DRIFT=OPEN_WARN
OPEN_MARKET_THREE_PAIR_PROOF=PENDING
SIGNAL_CLOSER_LIFECYCLE=SEPARATE_WORK
H1_ADX_OVERRIDE_CONTRACT=SEPARATE_APPROVAL
SESSION_SCORE_CLOCK_SOURCE=SEPARATE_APPROVAL
LEGACY_PROVIDER_REFRESH_CLEANUP=SEPARATE_APPROVAL
COMPACT_STATE_SCHEMA_NORMALIZATION=DEFERRED_CLEANUP
```

## Exactly one next proof

Wait for the first genuine `MARKET_OPEN` production cycle and verify current same-cycle EURUSD:M15, GBPUSD:M15, and USDJPY:M15 decisions, fresh updater/shadow evidence, one persisted terminal watcher outcome, and current unique watcher ownership with no active direct watcher cron or second owner.

Three legitimate rejected decisions are acceptable. A Telegram signal is not required.
