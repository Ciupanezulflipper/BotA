# BotA AI Start Here

Last updated: **2026-08-09 UTC**

Read this before proposing BotA commands, code, service, strategy, Telegram, provider, Supabase, replay, deployment, or Android/Termux changes.

## Current authoritative truth

```text
GITHUB_MAIN_AT_DEPLOYMENT=f52f326cdbc9e9a16dd60666808a35fb839f10ad
PHONE_DEPLOYED_RELEASE=f52f326cdbc9e9a16dd60666808a35fb839f10ad
DEPLOYED_TO_PHONE=PASS
RUNTIME_FILE_PARITY=PASS
ACTIVE_RUNIT_WRAPPER=PASS
ACTIVE_RUNIT_WRAPPER_MODE=755
THREE_PAIR_RUNTIME_SCOPE=PASS
PAIRS=EURUSD GBPUSD USDJPY
TIMEFRAMES=M15
TELEGRAM_ENABLED=1
DRY_RUN_MODE=0
SEVEN_SERVICES_RUNNING=PASS
WATCHER_CRON_DUPLICATE=NONE
PROFITLAB_CURSOR_PRESERVED=PASS
LIVE_CLOSED_MARKET_CYCLE=PASS
ISOLATED_MONDAY_HARNESS=PASS
OPEN_MARKET_THREE_PAIR_LIVE_PROOF=PENDING
MONDAY_READY=NO
```

BotA is **deployed and weekend-verified**, not yet Monday-ready.

The only remaining production-readiness gate is a genuine `MARKET_OPEN` cycle proving fresh EURUSD, GBPUSD, and USDJPY M15 decisions in the same authoritative watcher cycle, together with fresh supporting updater/shadow evidence. Three legitimate rejected decisions are acceptable; a Telegram signal is not required.

## Phone deployment model

The Android Git checkout is intentionally not the deployment identity:

```text
PHONE_LOCAL_BRANCH=deploy/repaired-core-20260802T215531Z
PHONE_LOCAL_HEAD=4339543551aae2e2bcbf727aefe96e3eb103b665
UNTRACKED_FILES_PRESERVED=782
```

Do not infer production version from the phone worktree HEAD. Production identity is the verified bounded runtime manifest from the immutable approved GitHub commit.

The active watcher wrapper is physically outside the repository worktree:

```text
/data/data/com.termux/files/home/.config/bota-sv/bota-watcher/run
```

It was verified against Git blob `25b240dc6913bf9cde82ab79a62ea6cddd73bc8e` with mode `755`.

## Latest real production evidence

Fresh post-deployment watcher event:

```text
cycle_id=b32a66a6-1a91-4b61-b759-c32851cbae6b:135481210634879
terminal_outcome=MARKET_CLOSED
market_reason=MARKET_CLOSED_SUNDAY
status=skipped_market_closed
time_source=server_epoch
server_epoch=1786236858
timestamp_utc=2026-08-09T00:54:18+00:00
```

This is stronger evidence than `sv status=run`: the deployed watcher actually executed the gated path and persisted an authoritative terminal outcome.

## Clock warning

The Android wall clock was about one hour behind trusted server time during the post-deployment audit:

```text
drift_seconds=-3621
local_clock_unsafe=true
server_clock_ok=true
server_sources_count=4
server_spread_seconds=1
status=DRIFT_WARN
```

The production watcher proof remains valid because it used trusted `server_epoch`, not the Android wall clock. Do not hide this warning: wall-clock-driven scheduled jobs may still be affected until device time is corrected or those jobs are independently shown to be insensitive to the drift.

## ProfitLab state

The independent ProfitLab worker remains active once per minute and its cursor was preserved:

```text
cursor_offset=897734
alerts_csv_size=897734
pending_bytes=0
```

Do **not** run `profitlab_delivery.py --bootstrap` on the current production state.

## Current strategy scope

The weekend production candidate intentionally uses:

```text
PAIRS=EURUSD GBPUSD USDJPY
TIMEFRAMES=M15
POLICY_B_ENABLED=1
POLICY_B_SCORE_MIN=70
POLICY_B_ADX_MAX=30
NEWS_ON=0
```

Do not loosen score, ADX, H1/H4/D1, Telegram, cooldown, or eligibility rules to manufacture signals. The next gate is operational proof, not strategy optimization.

## Historical evidence remains frozen

The June-July forensic dataset, deterministic replay, outcome matcher, and match-gap classification remain preserved evidence. Do not rerun or rewrite them unless their canonical evidence is proven invalid.

Key prior facts remain:

```text
PUBLISHED_OUTCOMES=13
WINS=3
LOSSES=9
CANCELLED=1
TOTAL_PIPS=-71.40
MATCHED_OUTCOMES=9
UNMATCHED_OUTCOMES=4
UNEXPLAINED_GAP_COUNT=0
POLICY_B_RECONSTRUCTED_SUBSET=N5_W3_L2_PIPS_PLUS54.50
```

These historical findings do not substitute for current live runtime proof.

## Read first

1. `CONTINUITY_CURRENT.md` — current status and exactly one next action.
2. `audits/PHONE_DEPLOYMENT_WEEKEND_PROOF_2026-08-09.md` — immutable deployment/runtime proof.
3. `ANDROID_TERMUX_TOOLCHAIN.md` — Android/Termux engineering-tool baseline and usage boundaries.
4. `audits/WEEKEND_PRODUCTION_READINESS_2026-08-08.md` — pre-deployment production-candidate contract.
5. `audits/REPLAY_OUTCOME_MATCH_GAP_RESULT_2026-08-08.md` — frozen historical replay/outcome evidence.
6. `docs/FORENSIC_OPERATING_MODEL.md` — connector-first operating model.

Older dated audits remain evidence. Current-state files may supersede their operational status but must not rewrite historical results.

## Mandatory source hierarchy

```text
GitHub connector   -> code, commits, PRs, docs, tests
Supabase connector -> published signal/outcome/database truth
Phone/Termux       -> runtime-only state, credentials, local persistent state/results
```

Do not ask for phone probes for facts already available through connectors. Use the phone only for runtime facts that GitHub cannot prove.

## Deployment discipline

Never equate these states:

```text
CODE_READY
MERGED_TO_MAIN
DEPLOYMENT_READY
DEPLOYED_TO_PHONE
RUNTIME_PARITY_VERIFIED
LIVE_PIPELINE_VERIFIED
MONDAY_READY
```

Each is a separate gate.

For production deployment:

- pin an immutable GitHub SHA;
- recheck `main` before mutation;
- verify exact file blobs and executable modes;
- back up every overwritten runtime file and phone-specific config;
- preserve logs, state, untracked runtime evidence, and unrelated cron;
- restart only the service that must change;
- verify the actual external runit wrapper, not merely the repository copy;
- require runtime evidence after service activation;
- rollback on activation/parity failure.

Never push directly to `main`. Use branch -> complete-file writes -> verified diff -> PR -> exact-head gates -> merge.

## Current freeze

```text
DO_NOT_REDEPLOY_SAME_RELEASE_WITHOUT_CONTRADICTORY_EVIDENCE=YES
DO_NOT_RESTART_SERVICES_FOR_COSMETIC_REASONS=YES
DO_NOT_BOOTSTRAP_PROFITLAB=YES
DO_NOT_LOWER_THRESHOLDS=YES
DO_NOT_FORCE_SIGNAL_COUNT=YES
DO_NOT_DECLARE_MONDAY_READY_FROM_WEEKEND_PROOF=YES
```

## Exactly one next action

Preserve the current deployed state until the first genuine `MARKET_OPEN` production cycle. Then verify, from the append-only runtime evidence, that the same current cycle contains EURUSD:M15, GBPUSD:M15, and USDJPY:M15 decisions; that updater and shadow evidence is fresh; and that the watcher ends in a legitimate terminal outcome.

If those conditions pass, advance the readiness gate. If any pair/evidence is missing or stale, classify the operational failure before changing strategy.