# BotA Chat Handoff

Last updated: **2026-08-09 UTC**

Read this first in any new AI session before proposing BotA changes.

## Current grounded answer

BotA is no longer merely a reviewed GitHub candidate. The approved Monday-readiness watcher release has been deployed to the Android/Termux phone and verified at runtime.

Current classification:

```text
DEPLOYED_AND_WEEKEND_VERIFIED=YES
MONDAY_READY=NO
REASON=REAL_OPEN_MARKET_THREE_PAIR_CYCLE_NOT_YET_PROVEN
```

Do not add another package simply because the weekend checks passed. Preserve the known-good runtime until the first genuine open-market proof.

## Production release identity

```text
APPROVED_AND_DEPLOYED_SHA=f52f326cdbc9e9a16dd60666808a35fb839f10ad
PHONE_LOCAL_BRANCH=deploy/repaired-core-20260802T215531Z
PHONE_LOCAL_HEAD=4339543551aae2e2bcbf727aefe96e3eb103b665
PHONE_UNTRACKED_FILES_PRESERVED=782
```

The phone Git worktree is not the deployment identity. It deliberately remains on an older local deployment branch so persistent runtime/audit files were not destroyed. Production parity was established by exact Git blob verification of the bounded runtime manifest.

## Live runtime configuration

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

Do not loosen score, ADX, H1/H4/D1, Telegram, cooldown, or eligibility rules to manufacture signal volume.

## Active watcher ownership

Production watcher is runit-owned.

Active physical wrapper:

```text
/data/data/com.termux/files/home/.config/bota-sv/bota-watcher/run
Git blob=25b240dc6913bf9cde82ab79a62ea6cddd73bc8e
mode=755
```

Post-deployment control plane:

```text
runsvdir_managers=1
services_running=7/7
active_direct_watcher_cron=0
active_profitlab_cron=1
```

Running services:

```text
bota-updater
bota-watcher
bota-closer
bota-shadow
bota-heartbeat
bota-supervisor
crond
```

Never assume the repository copy of a runit wrapper controls the live phone process. Resolve and verify the physical active wrapper.

## Real production proof already obtained

After the successful deployment, the restarted watcher emitted:

```text
cycle_id=b32a66a6-1a91-4b61-b759-c32851cbae6b:135481210634879
status=skipped_market_closed
terminal_outcome=MARKET_CLOSED
market_reason=MARKET_CLOSED_SUNDAY
time_source=server_epoch
server_epoch=1786236858
timestamp_utc=2026-08-09T00:54:18+00:00
```

This proves the approved runtime executed the gated watcher cycle and wrote an authoritative terminal outcome. Service liveness alone was not accepted as deployment proof.

## Isolated Monday-readiness proof

Post-deployment `tools/monday_readiness_check.py` returned `healthy=true`, RC 0, with 8/8 fixture scenarios matching the expected terminal outcomes.

It is safe evidence because it uses a temporary `BOTA_ROOT` and does not consult the live market, send Telegram, write Supabase, mutate strategy, restart runit, change crontab, or write fake production signals.

## ProfitLab

```text
cursor_offset=897734
alerts_csv_size=897734
pending_bytes=0
```

The cursor survived deployment unchanged. Do not run `profitlab_delivery.py --bootstrap`.

## Clock warning

The Android wall clock is currently unsafe relative to trusted server time:

```text
drift_seconds=-3621
local_clock_unsafe=true
server_clock_ok=true
server_sources_count=4
server_spread_seconds=1
status=DRIFT_WARN
```

The watcher is protected because its market decision used `server_epoch`. Do not silently dismiss the device-clock drift because cron-style schedules can still be shifted in real time.

## Residual observations

- The compact `pipeline_progress.json` top-level schema label remains `1.0` from prior persisted state, while new watcher events are schema `1.1`. This is bookkeeping debt, not a weekend blocker.
- Compact pair decisions are still old EURUSD/GBPUSD records; there is no post-deployment USDJPY decision yet because the real post-deploy cycle occurred while the FX market was closed.
- A recorded `shadow status=failed, exit_code=1` event predates the successful deployment. The live `bota-shadow` runit service is running; require fresh shadow evidence during the open-market proof.

Do not mutate the stable runtime solely to clean these labels/history before Monday.

## Deployment lessons now part of the operating model

The deployment sequence itself caught important failure modes:

1. Moving GitHub `main` caused a safe pre-mutation abort.
2. Git mode `100644` on the runit `run` file caused activation failure and automatic rollback; PR #81 fixed the mode to `100755`.
3. A verifier incorrectly assumed the `crond` service path; that attempt aborted before mutation and the topology logic was corrected.
4. The final deployment used the exact 12-file mismatch/missing manifest from the phone parity audit, corrected only the `PAIRS` assignment, and preserved persistent state.

Full evidence: `audits/PHONE_DEPLOYMENT_WEEKEND_PROOF_2026-08-09.md`.

## Historical evidence

The historical acquisition, deterministic replay, published-outcome matcher, and match-gap classification remain closed evidence. Do not rerun them without contradictory evidence.

Important prior result remains:

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

Policy B was selected from the controlled evidence and is already the deployed quality guard. Current work is operational validation, not another threshold-search exercise.

## What counts as Monday proof

The first genuine `MARKET_OPEN` production cycle must show, from current append-only evidence:

```text
EURUSD:M15 decision in current cycle
GBPUSD:M15 decision in current cycle
USDJPY:M15 decision in current cycle
fresh updater progress
fresh shadow progress
one authoritative watcher terminal outcome
no duplicate watcher owner
provider/data failures surfaced rather than hidden
```

If the strategy legitimately rejects all three pairs, that is acceptable. Do not require a Telegram signal to call the execution path healthy.

## Working discipline

1. Inspect before changing.
2. Separate GitHub state, phone worktree state, deployed runtime state, and live-cycle state.
3. Use immutable SHA + file hashes + executable modes for deployment identity.
4. Preserve persistent logs/state and unrelated cron.
5. One process owner per production job.
6. Every watcher cycle must have an observable terminal outcome.
7. Operational failure dominates healthy-looking business semantics.
8. Do not use Android local time for trading decisions when trusted server time is available.
9. Never push directly to `main`; use branch -> verified diff -> PR -> exact-head checks -> merge.
10. Do not change strategy to compensate for missing operational proof.

## Exactly one next action

Wait for the first genuine `MARKET_OPEN` production cycle and verify the three current M15 decisions plus fresh updater/shadow evidence and the authoritative watcher terminal outcome. If that gate passes, advance readiness. If it fails, diagnose the operational failure before changing strategy.