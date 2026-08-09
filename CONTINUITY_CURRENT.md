# BotA Current Continuity State

Last updated: **2026-08-09 UTC**

This file is the current operational handoff. Dated audit files preserve historical evidence; do not reconstruct current production state from older continuity snapshots.

## Current status

```text
CODE_READY=PASS
MERGED_TO_MAIN=PASS
DEPLOYED_TO_PHONE=PASS
RUNTIME_PARITY_VERIFIED=PASS
RUNIT_ACTIVATION=PASS
CLOSED_MARKET_LIVE_CYCLE=PASS
ISOLATED_MONDAY_HARNESS=PASS
PROFITLAB_STATE=PASS
OPEN_MARKET_THREE_PAIR_LIVE_PROOF=PENDING
MONDAY_READY=NO
```

BotA is **DEPLOYED_AND_WEEKEND_VERIFIED**. The remaining gate is live open-market proof, not more weekend coding.

## Authoritative release identity

```text
DEPLOYED_GITHUB_SHA=f52f326cdbc9e9a16dd60666808a35fb839f10ad
PHONE_LOCAL_BRANCH=deploy/repaired-core-20260802T215531Z
PHONE_LOCAL_HEAD=4339543551aae2e2bcbf727aefe96e3eb103b665
PHONE_TRACKED_DIRTY_BEFORE_DEPLOY=0
PHONE_UNTRACKED_PRESERVED=782
```

The phone Git checkout was intentionally not reset/cleaned to `main`. Runtime identity is proven from the bounded deployed file hashes, active wrapper hash/mode, runtime configuration, and live cycle evidence. Do not use the phone checkout HEAD as the production release identifier.

## Deployed runtime scope

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

Only the existing `PAIRS` assignment in `.env.runtime` was changed during the successful deployment. Secrets and unrelated runtime variables were preserved.

The active watcher wrapper is:

```text
/data/data/com.termux/files/home/.config/bota-sv/bota-watcher/run
blob=25b240dc6913bf9cde82ab79a62ea6cddd73bc8e
mode=755
```

## Service/control-plane proof

Post-deployment topology:

```text
runsvdir_managers=1
required_services_running=7/7
active_watcher_cron=0
active_profitlab_cron=1
```

Services verified running:

```text
bota-updater
bota-watcher
bota-closer
bota-shadow
bota-heartbeat
bota-supervisor
crond
```

The watcher is runit-owned. Do not restore a direct watcher cron entry.

## Live post-deployment watcher proof

Fresh real production terminal event:

```text
cycle_id=b32a66a6-1a91-4b61-b759-c32851cbae6b:135481210634879
status=skipped_market_closed
terminal_outcome=MARKET_CLOSED
market_reason=MARKET_CLOSED_SUNDAY
time_source=server_epoch
server_epoch=1786236858
timestamp_utc=2026-08-09T00:54:18+00:00
```

This proves the approved deployed wrapper executed `watcher_gated_cycle.sh` and persisted an authoritative terminal outcome after the service restart.

## Isolated readiness harness

Post-deployment `tools/monday_readiness_check.py` result:

```text
healthy=true
return_code=0
scenarios_passed=8/8
```

The harness verified closed-session reasons, clock-gate failures, and an isolated open-market rejected outcome. It uses a temporary `BOTA_ROOT`; it did not mutate production, send Telegram, write Supabase, restart services, or change crontab.

## ProfitLab state

```text
cursor_offset=897734
alerts_csv_size=897734
pending_bytes=0
```

ProfitLab state was preserved through deployment. Do not run `profitlab_delivery.py --bootstrap` on this production state.

## Clock warning

Post-deployment clock audit:

```text
local_utc=2026-08-08T23:55:00Z
server_utc=2026-08-09T00:55:21Z
drift_seconds=-3621
local_clock_unsafe=true
server_clock_ok=true
server_sources_count=4
server_spread_seconds=1
status=DRIFT_WARN
```

The watcher remains fail-closed and used `server_epoch`, so the live watcher proof is valid. Device wall-clock drift remains operational debt because cron-style schedules can still be shifted in real time.

## Residual state observations

These are recorded but are not reasons to churn the production release tonight:

- `state/pipeline_progress.json` retained a legacy top-level schema label `1.0` while new watcher events are schema `1.1`; current ledger code preserves an existing state label with `setdefault`.
- Compact decision state still contains pre-deployment EURUSD/GBPUSD decisions and no USDJPY decision because the only new real cycle was Sunday market-closed.
- The compact `shadow` event showing `status=failed, exit_code=1` predates the successful deployment; the current `bota-shadow` runit service was verified running. Fresh updater/shadow evidence is required when the market opens.

Do not cosmetically mutate production to erase these observations before the live gate.

## Deployment failures learned from, not hidden

The successful release was preceded by controlled failures that improved the deployment contract:

1. GitHub `main` moved after an earlier release pin; the deployer aborted before mutation.
2. The approved runit wrapper was stored as Git mode `100644`; activation failed and rollback restored the previous watcher. PR #81 corrected it to `100755`.
3. A verification script incorrectly looked for `crond` under `${HOME}/.config/bota-sv`; it aborted before mutation. Correct topology uses `$PREFIX/var/service`.
4. The final corrected deployment used the exact 12-file parity-audit manifest plus the one approved `.env.runtime` `PAIRS` correction.

Full evidence is in `audits/PHONE_DEPLOYMENT_WEEKEND_PROOF_2026-08-09.md`.

## Historical strategy evidence remains preserved

The June-July historical acquisition/replay/matching work remains closed evidence. Do not rerun it merely because production has now been deployed.

The controlled production candidate remains Policy B (`current acceptance AND score >=70 AND ADX <30`) with USDJPY pair-aware risk handling and `NEWS_ON=0`. Do not loosen thresholds to force signals.

## Current freeze

```text
DO_NOT_REDEPLOY_WITHOUT_NEW_CONTRADICTORY_EVIDENCE=YES
DO_NOT_RESTART_SERVICES_FOR_COSMETIC_STATE=YES
DO_NOT_BOOTSTRAP_PROFITLAB=YES
DO_NOT_FORCE_TELEGRAM_TEST_SIGNAL=YES
DO_NOT_LOWER_THRESHOLDS=YES
DO_NOT_DECLARE_MONDAY_READY_FROM_WEEKEND_PROOF=YES
```

## Exactly one next action

Preserve this known-good deployed state until the first genuine `MARKET_OPEN` production cycle. Then verify the append-only runtime evidence for the same current cycle:

```text
EURUSD:M15 decision present
GBPUSD:M15 decision present
USDJPY:M15 decision present
fresh updater progress present
fresh shadow progress present
watcher terminal outcome is legitimate and persisted
provider/data failure is visible if one occurred
delivery evidence is checked only if a signal genuinely qualifies
```

Three legitimate rejected decisions are a valid PASS. A Telegram signal is not required. A missing/stale pair, hidden operational failure, duplicate owner, or missing terminal outcome is a FAIL and must be diagnosed before any strategy mutation.