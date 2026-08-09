# BotA Phone Deployment and Weekend Runtime Proof

Recorded: **2026-08-09 UTC**

This audit records the first verified Android/Termux deployment of the reviewed Monday-readiness watcher release. It is a deployment/runtime evidence record, not a strategy-performance claim.

## Final verdict

```text
APPROVED_GITHUB_SHA=f52f326cdbc9e9a16dd60666808a35fb839f10ad
DEPLOYED_TO_PHONE=PASS
RUNTIME_FILE_PARITY=PASS
ACTIVE_RUNIT_WRAPPER=PASS
THREE_PAIR_RUNTIME_SCOPE=PASS
SEVEN_SERVICES_RUNNING=PASS
WATCHER_CRON_DUPLICATE=NONE
PROFITLAB_CURSOR_PRESERVED=PASS
LIVE_CLOSED_MARKET_CYCLE=PASS
ISOLATED_MONDAY_HARNESS=PASS
OPEN_MARKET_THREE_PAIR_LIVE_PROOF=PENDING
MONDAY_READY=PENDING
```

BotA is **DEPLOYED_AND_WEEKEND_VERIFIED**. Do not call it Monday-ready until a genuine `MARKET_OPEN` production cycle proves current EURUSD, GBPUSD, and USDJPY M15 decisions in the same cycle with fresh supporting runtime evidence.

## Approved release

The production release deployed to the phone is:

```text
f52f326cdbc9e9a16dd60666808a35fb839f10ad
```

This includes PR #78 Monday-readiness watcher observability and PR #81, which corrected `ops/runit/bota-watcher.run` from Git mode `100644` to `100755` without changing its contents.

## Deployment incident sequence

The deployment process caught three distinct operational hazards before accepting production state:

1. An earlier deployment attempt was pinned to `ebcf302239863b453eee4e3d9649bd966f310b55`. GitHub `main` moved before mutation, so the immutable-release guard aborted with `PRODUCTION_MUTATION=NO` and `SERVICE_RESTART=NO`.
2. A later attempt installed the reviewed wrapper while Git stored it as mode `100644`. `bota-watcher` could not start, the activation gate failed, and the deployment automatically restored the previous phone runtime. PR #81 corrected the Git mode to `100755`.
3. A subsequent verification script incorrectly assumed `crond` lived under `${HOME}/.config/bota-sv`. The gate stopped before mutation. The corrected topology check uses `$PREFIX/var/service` for all seven runit services while resolving the watcher wrapper to its real external path.

These failures are deployment-process evidence. None authorized a strategy change, and the final successful deployment did not require rollback.

## Phone worktree and deployment model

The Android Git checkout remains intentionally separate from the deployed release identity:

```text
PHONE_LOCAL_BRANCH=deploy/repaired-core-20260802T215531Z
PHONE_LOCAL_HEAD=4339543551aae2e2bcbf727aefe96e3eb103b665
TRACKED_DIRTY_COUNT_BEFORE_DEPLOY=0
UNTRACKED_COUNT_PRESERVED=782
```

The phone was not reset, cleaned, or hard-checked-out to `main`. Runtime convergence was proven by immutable Git blob parity for the bounded production manifest. Therefore the local checkout HEAD is not the deployment identity.

## Exact deployed runtime manifest

The following 12 files were staged from the immutable approved commit and verified byte-for-byte after installation:

| Path | Git blob |
|---|---|
| `tools/signal_watcher_pro.sh` | `66f6b610f392ff6c60179c92da9efc6396a762c7` |
| `tools/market_open.sh` | `202f0ea34d196a4f0516afb656259c79c20ad66b` |
| `tools/m15_h1_fusion.sh` | `a177541aa8dc9e193ce6f057dab02886c24a4f40` |
| `tools/production_signal_policy.py` | `1683204657e64e7242269cfdff846bcc796cafaf` |
| `tools/sync_d1_trend_cache.py` | `8b930a7009cb3e6edfe6af5ef48632ec1160f8f3` |
| `ops/runit/bota-watcher.run` | `25b240dc6913bf9cde82ab79a62ea6cddd73bc8e` |
| `tools/pipeline_health.py` | `58e7223e42fcde58d2472e8b189e62bcaf53dfda` |
| `tools/pipeline_ledger.py` | `1a6fbd682b3dddc81bdb02fa01166eaa59d5aecf` |
| `tools/run_signal_watcher_with_ledger.sh` | `e2c7224e8c53bec7a185fbdbbb8cdc5f65d50286` |
| `tools/watcher_cycle_ledger.py` | `52ceb1c5af35af784d452551222366bc44d411ec` |
| `tools/watcher_gated_cycle.sh` | `06d9609e13caf69c742200507ae46a3a4d722381` |
| `tools/monday_readiness_check.py` | `fcb3c5c3af6d1ff770153e9e5f9bb1ce6befc6fe` |

The active runit wrapper resolves to:

```text
/data/data/com.termux/files/home/.config/bota-sv/bota-watcher/run
```

and was verified as:

```text
ACTIVE_WRAPPER_BLOB=25b240dc6913bf9cde82ab79a62ea6cddd73bc8e
ACTIVE_WRAPPER_MODE=755
```

## Runtime scope

Only the `PAIRS` assignment in `.env.runtime` was changed during deployment. Secrets and unrelated runtime values were preserved.

```text
PAIRS="EURUSD GBPUSD USDJPY"
TIMEFRAMES="M15"
TELEGRAM_ENABLED=1
DRY_RUN_MODE=0
```

The reviewed runit wrapper pins the non-secret production controls, including Policy B and `NEWS_ON=0`. No threshold was loosened to manufacture signals.

## Process ownership and service topology

After activation:

```text
runsvdir_managers=1
required_services=7
running_services=7
active_watcher_cron_count=0
active_profitlab_cron_count=1
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

The watcher is runit-owned. The historical direct watcher cron remains migrated/commented and is not an active duplicate owner.

## ProfitLab preservation

The existing ProfitLab cursor was not bootstrapped or reset:

```text
PROFITLAB_CURSOR_OFFSET=897734
ALERTS_CSV_SIZE=897734
PENDING_BYTES=0
```

The independent once-per-minute ProfitLab cron remained active. Deployment did not mutate the cursor or replay historical alerts.

## Real post-deployment watcher proof

The restarted production watcher emitted a fresh authoritative terminal event:

```text
cycle_id=b32a66a6-1a91-4b61-b759-c32851cbae6b:135481210634879
status=skipped_market_closed
terminal_outcome=MARKET_CLOSED
market_reason=MARKET_CLOSED_SUNDAY
time_source=server_epoch
server_epoch=1786236858
timestamp_utc=2026-08-09T00:54:18+00:00
```

This proves the deployed runit wrapper executed the gated cycle and persisted a terminal outcome using trusted server time. A running service alone would not have been sufficient proof.

## Isolated Monday-readiness harness

`tools/monday_readiness_check.py` was executed after deployment and returned:

```text
healthy=true
return_code=0
scenarios=8/8 matched
```

Verified fixture-only outcomes:

```text
MARKET_CLOSED_SATURDAY        -> MARKET_CLOSED
MARKET_CLOSED_SUNDAY          -> MARKET_CLOSED
MARKET_CLOSED_FRIDAY_POST_2000-> MARKET_CLOSED
MARKET_CLOSED_ASIAN_PRE_0700  -> MARKET_CLOSED
MARKET_CLOSED_POST_NY         -> MARKET_CLOSED
CLOCK_UNAVAILABLE             -> CLOCK_GATE_FAILED
MARKET_GATE_ERROR             -> CLOCK_GATE_FAILED
MARKET_OPEN dry-run           -> EVALUATED_REJECTED
```

The harness runs in an isolated temporary `BOTA_ROOT`. It does not consult the live market, send Telegram, write Supabase, mutate runit/crontab, change strategy, or create fake production journal entries.

## Clock warning

The Android wall clock was approximately one hour behind trusted server time during the post-deployment audit:

```text
local_utc=2026-08-08T23:55:00Z
server_utc=2026-08-09T00:55:21Z
drift_seconds=-3621
drift_abs_seconds=3621
local_clock_unsafe=true
server_clock_ok=true
server_sources_count=4
server_spread_seconds=1
status=DRIFT_WARN
```

This is an operational warning. It does not invalidate the watcher proof because the market gate and production watcher event used `server_epoch`. Wall-clock-driven jobs can still be affected by device-clock error, so this warning must remain visible until corrected or explicitly proven harmless for each scheduled job.

## Residual observations that are not yet blockers

`state/pipeline_progress.json` retained a legacy top-level `schema_version` value of `1.0` while the new watcher event is schema `1.1`. `pipeline_ledger.py` preserves an existing state schema label through `setdefault`; this is bookkeeping debt, not evidence that the new event used the old contract. Do not mutate production solely to relabel this state before Monday proof.

The compact decision state still showed historical EURUSD and GBPUSD records from before the three-pair deployment. That is expected because the only post-deployment real cycle was market-closed. USDJPY must appear in the first genuine open-market decision cycle before Monday readiness can pass.

The compact `shadow` component state showed an older `status=failed, exit_code=1` event timestamped before the successful deployment. The current `bota-shadow` runit service was running after deployment. Fresh open-market shadow/updater evidence remains part of the Monday proof.

## Frozen next gate

Do not add another runtime package merely because the weekend gates passed. Preserve the known-good deployment.

The next decisive proof is one genuine `MARKET_OPEN` production cycle that shows:

```text
EURUSD:M15 current decision = present
GBPUSD:M15 current decision = present
USDJPY:M15 current decision = present
same authoritative cycle = proven
fresh updater evidence = present
fresh shadow evidence = present
terminal watcher outcome = legitimate enum value
provider/data failures = visible if present
Telegram/Supabase delivery evidence = evaluated only if a signal genuinely qualifies
```

Three valid rejected decisions are acceptable. A Telegram signal is not required to pass readiness. Missing pairs, stale data disguised as healthy, duplicate ownership, or a cycle without a terminal outcome are failures.

Until that proof exists:

```text
MONDAY_READY=NO
RUNTIME_CHURN_ALLOWED=NO_UNLESS_NEW_CONTRADICTORY_EVIDENCE
```
