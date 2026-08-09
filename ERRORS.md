# BotA Errors and Silent-Failure Register

Last updated: **2026-08-09 UTC**

Purpose: preserve verified failure classes, current open risks, and prevention rules without letting old runtime snapshots masquerade as current production truth.

Canonical current sources:

- `CONTINUITY_CURRENT.md`
- `AI_START_HERE.md`
- `CHAT_HANDOFF_BOTA.md`
- `DECISIONS.md`
- `audits/PHONE_DEPLOYMENT_WEEKEND_PROOF_2026-08-09.md`
- `audits/ERROR_LOG.md`
- GitHub issue #9

Historical detailed evidence remains in Git history and dated audit files.

## Current verdict — 2026-08-09 UTC

```text
DEPLOYED_RELEASE=f52f326cdbc9e9a16dd60666808a35fb839f10ad
DEPLOYED_TO_PHONE=PASS
RUNTIME_FILE_PARITY=PASS
ACTIVE_RUNIT_WRAPPER=PASS
ACTIVE_WRAPPER_MODE=755
CONTROL_PLANE=HEALTHY_7_OF_7
ACTIVE_WATCHER_CRON=0
PAIRS=EURUSD GBPUSD USDJPY
TIMEFRAMES=M15
POLICY_B_ENABLED=1
POLICY_B_SCORE_MIN=70
POLICY_B_ADX_MAX=30
NEWS_ON=0
TELEGRAM_ENABLED=1
DRY_RUN_MODE=0
PROFITLAB_CURSOR_PRESERVED=PASS
LIVE_CLOSED_MARKET_CYCLE=PASS
ISOLATED_MONDAY_HARNESS=PASS
LOCAL_CLOCK=DRIFT_WARN
OPEN_MARKET_THREE_PAIR_LIVE_PROOF=PENDING
MONDAY_READY=NO
```

The current bottleneck is no longer “was the approved code deployed?” That gate passed. The remaining readiness question is whether the first genuine open-market cycle produces complete, fresh, same-cycle evidence for all three M15 pairs without hidden operational failure.

## E001 — Scope branching / mixed phases

**Failure class:** repository, runtime, documentation, deployment, and strategy work were mixed into one stream.

**Observed consequence:** old files continued describing pre-deployment/two-pair truth after the reviewed production candidate had changed.

**Prevention:**
- one phase/evidence domain/acceptance gate per package;
- distinguish code-ready, merged, deployed, runtime-parity, live-cycle, and Monday-ready states;
- current-state files must be updated when production truth changes;
- dated audits remain immutable evidence.

## E002 — Repository state mistaken for deployed runtime state

**Failure class:** assuming GitHub `main` or the phone Git checkout proves what the live process executes.

**Observed production fact:** phone local checkout remains on `deploy/repaired-core-20260802T215531Z@4339543...` while the bounded runtime manifest was deployed from `f52f326...`.

**Prevention:** deployment identity requires immutable approved SHA + deployed blob parity + executable modes + active-wrapper parity + runtime config + live-cycle evidence.

Do not `git reset --hard` or clean preserved untracked runtime evidence merely to make the worktree resemble production.

## E003 — Duplicate execution ownership

**Failure class:** cron, runit, boot files, wrappers, or multiple supervisors owning the same component.

**Current proof:** one runsvdir control plane, 7/7 required services running, active direct watcher cron count zero.

**Prevention:** re-prove current single ownership during the first open-market readiness cycle. Historical topology is not enough.

## E004 — Dead manager / orphaned service topology

**Failure class:** a manager can die while child `runsv` processes survive, producing misleading process observations.

**Current status:** resolved in the present topology; one manager and seven required services were proven running after deployment.

**Prevention:** count manager, required services, orphaned services, and duplicates explicitly rather than relying on one PID or one `sv status` line.

## E005 — Device wall-clock drift

**Failure class:** Android wall clock, trusted server UTC, monotonic time, and CLOCK_BOOTTIME can diverge.

**Current observation:**

```text
drift_seconds=-3621
local_clock_unsafe=true
server_clock_ok=true
server_sources_count=4
server_spread_seconds=1
status=DRIFT_WARN
```

**Prevention:** trusted server epoch for market/lifecycle truth; monotonic/CLOCK_BOOTTIME for same-boot cadence and freshness; fail closed on untrusted time.

**Residual risk:** wall-clock-driven cron schedules may still execute at the wrong real-world hour until device time is corrected or each schedule is proven safe.

## E006 — False health from partial pair scope

**Failure class:** health/reconciliation can appear green while USDJPY silently disappears if scope contracts lag production configuration.

**Current fix:** watcher/readiness observability defaults to EURUSD, GBPUSD, USDJPY M15 and fails safely on partial/malformed scope.

**Remaining proof:** a genuine post-deployment `MARKET_OPEN` cycle must show all three current decisions in the same cycle.

## E007 — Decision evidence written too late

**Failure class:** delivery/dedup logic previously ran before full decision journaling, damaging forensic reconstruction.

**Current prevention:** decision persistence and delivery state are distinct; terminal outcomes and pair/timeframe decisions must be observable even when delivery does not occur.

Do not use Telegram delivery as proof that the watcher evaluated every pair.

## E008 — Healthy-looking semantic result after inner execution failure

**Failure class:** reconciliation could potentially aggregate existing semantic evidence while the inner watcher execution had actually failed.

**Current fix:** non-zero inner watcher execution dominates semantic aggregation and must surface as operational failure (`INTERNAL_ERROR` or applicable failure outcome).

## E009 — Cycle without authoritative terminal outcome

**Failure class:** liveness/heartbeat can continue while a scheduled watcher cycle disappears without a terminal record.

**Current fix:** gated cycle + shared cycle ID + append-only pipeline ledger + terminal-outcome enum.

**Proven post-deployment example:** `MARKET_CLOSED / MARKET_CLOSED_SUNDAY` persisted with trusted server epoch after watcher restart.

**Prevention:** service liveness alone never satisfies runtime readiness.

## E010 — Moving GitHub release target during deployment

**Failure class:** deploy against a branch name while `main` changes underneath the operation.

**Observed 2026-08-08/09:** an early deployment attempt detected `main` had moved from its approved SHA and aborted before mutation.

**Prevention:** immutable commit pin plus a second `main` check immediately before production mutation.

## E011 — Runit `run` file stored without executable mode

**Failure class:** file contents can be correct while Git mode makes the service unstartable.

**Observed:** `ops/runit/bota-watcher.run` was mode `100644`; deployment preserved the mode, watcher activation failed, rollback restored the prior runtime.

**Fix:** PR #81 changed only the Git mode to `100755`.

**Prevention:** verify file modes as part of release parity, not only hashes/content.

## E012 — Wrong service-path assumption in deployment tooling

**Failure class:** assuming every runit service directory lives under `${HOME}/.config/bota-sv`.

**Observed:** verification incorrectly looked for `crond` there and aborted before mutation.

**Current truth:** canonical service topology is under `$PREFIX/var/service`; the active watcher `run` file resolves through that service to an external physical wrapper under `${HOME}/.config/bota-sv/bota-watcher/run`.

**Prevention:** query/resolve actual service paths rather than generalizing from one component.

## E013 — Deployment manifest drift

**Failure class:** a generated deploy command can accidentally substitute files that were already in parity and omit files/config changes identified by the authoritative phone audit.

**Prevention:** the deploy manifest must come directly from the parity audit, have an expected file count, and be revalidated against the immutable approved commit before mutation.

The successful deployment used exactly the 12 divergent/missing runtime files plus the approved `.env.runtime` `PAIRS` correction.

## E014 — ProfitLab historical replay risk

**Failure class:** resetting/bootstrap of the independent delivery cursor after activation could replay historical alert rows.

**Current state:**

```text
cursor_offset=897734
alerts_csv_size=897734
pending_bytes=0
```

**Prevention:** do not run `profitlab_delivery.py --bootstrap` on the current production state; preserve cursor state through deployments.

## E015 — Persisted state schema label lags new event contract

**Observation:** live `pipeline_progress.json` retained top-level `schema_version=1.0` while new watcher events are schema `1.1`.

**Classification:** bookkeeping debt, not evidence that the post-deployment watcher used the old event contract.

**Reason:** current ledger initialization preserves an existing state label via `setdefault`.

**Prevention:** do not mutate known-good production solely for cosmetic state normalization before the open-market proof. Address later in a bounded state-migration/cleanup change if still useful.

## E016 — Stale component state mistaken for post-deployment failure

**Observation:** compact `shadow` state showed an older `status=failed, exit_code=1` event that predates the successful deployment, while the current runit service is running.

**Prevention:** classify evidence by timestamp/cycle relative to deployment. Require fresh updater/shadow evidence during the real open-market gate instead of treating old state as current failure or silently ignoring it.

## E017 — Stale PR/readiness implementation drift

**Failure class:** overlapping readiness PRs on old bases can remain open and look like current work.

**Observed:** PR #77 was based on `d371ef4...` and overlapped/diverged from the readiness path later merged through PR #78 and PR #81.

**Current status:** PR #77 closed unmerged as superseded.

**Prevention:** close superseded branches/PRs with a written reason; do not merge stale implementations wholesale.

## Historical strategy-quality evidence remains separate

The June-July outcome/replay evidence remains preserved:

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

This evidence supported the controlled Policy-B candidate, but current readiness is an operational proof problem. Do not respond to missing runtime evidence by changing strategy thresholds.

## Current open risks requiring separate work

These are not reasons to disturb the current weekend-verified deployment before the market-open gate:

- Android wall-clock drift and its effect on wall-clock schedules;
- signal-closer lifecycle correctness (stale draft PR #7 must not be merged wholesale);
- H1/ADX override contract mismatch;
- session-score clock source if any strategy path still depends on unsafe local time;
- redundant/legacy provider refresh behavior;
- compact state-schema normalization.

Each requires a separately scoped change if/when scheduled.

## Exactly one next proof

On the first genuine `MARKET_OPEN` production cycle, require current evidence that:

```text
EURUSD:M15 decision present
GBPUSD:M15 decision present
USDJPY:M15 decision present
same cycle identity proven
fresh updater evidence present
fresh shadow evidence present
terminal watcher outcome persisted
no active direct watcher cron
no second watcher owner
provider/data failure visible if present
```

Three legitimate rejected decisions are acceptable. A Telegram signal is not required.
