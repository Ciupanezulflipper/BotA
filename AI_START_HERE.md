# BotA AI Start Here

Last updated: **2026-10-06 UTC**

Read this before proposing any BotA strategy, deployment, Telegram, ProfitLab, Android/Termux, VPS/Hetzner, replay, historical-data, or runtime action.

## Current authoritative truth

```text
PROJECT=BotA
BOTA_EDGE_STATUS=UNVALIDATED
BOTA_SHADOW_RESEARCH=REOPENED_BY_OWNER
HISTORICAL_RETROSPECTIVE_VALIDATION_PROJECT=CLOSED
HISTORICAL_CORPUS_GATE_RESULT=FAIL_195_LT_400
LIVE_MONEY_TRADING=NO
COMMERCIAL_PROFITLAB=NO
PRIVATE_PROFITLAB_ANALYTICS=YES

PRIMARY_RUNTIME_TARGET=HETZNER
CURRENT_HETZNER_RUNTIME_STATE=ACTIVE
DEPLOYED_RELEASE=4424518e7b42ecf2a070967d626a9ac86bf04d53
BOTA_SERVICE=active
BOTA_SERVICE_ENABLED=enabled
PROVIDER_CONTRACT=YAHOO
THREE_PAIR_M15_SCAN=RUNNING
MARKET_DATA=UPDATING
SIGNAL_CLOSER=RUNNING
PROFITLAB_DELIVERY_WORKER=RUNNING
LIVE_DELIVERY_CONTRACT=PASS

TELEGRAM_CREDENTIAL_VALIDATED=YES
SUPABASE_SERVICE_CREDENTIAL_VALIDATED=YES
REAL_TELEGRAM_SIGNAL_POST_ACTIVATION=NOT_YET_OBSERVED
REAL_PROFITLAB_SIGNAL_POST_ACTIVATION=NOT_YET_OBSERVED
DELIVERY_NOT_OBSERVED_REASON=NO_QUALIFIED_SIGNAL_IN_SAMPLED_POST_ACTIVATION_CYCLES

ANDROID_ACTIVE_SCANNER=NO
ANDROID_ROLE=CONTROL_AND_OBSERVATION_ONLY
STRATEGY_TUNING=NO
PAIR_CHANGES=NO
TIMEFRAME_CHANGES=NO
FORCED_SIGNAL_GENERATION=NO

NEXT_ACTION=ONE_BOUNDED_DUAL_SINK_DELIVERY_PROOF_WITHOUT_STRATEGY_CHANGE
FURTHER_BROAD_AI_REVIEW=STOP
```

Current production activation evidence:

`audits/BOTA_HETZNER_PRODUCTION_ACTIVATION_2026-10-06.md`

Current operational handoff:

`CONTINUITY_CURRENT.md`

Historical strategy/research authority remains preserved in the dated records below.

## Production runtime interpretation

Hetzner is now proven active on exact release:

```text
4424518e7b42ecf2a070967d626a9ac86bf04d53
```

The production deployer completed with `healthy=true`, phase `COMPLETE`, and no rollback. The service is active and enabled.

Post-activation watcher evidence shows natural market-open cycles completing for EURUSD, GBPUSD and USDJPY M15. The sampled cycles were all `EVALUATED_REJECTED`, so Telegram and Supabase were correctly `not_attempted`.

Do not misstate this as a delivery failure. It means no qualified signal existed in the sampled post-activation window.

The parent orchestrator remains R5-shadowed/fail-closed. Approved child jobs receive scoped live credentials. Therefore parent `side_effects_enabled=false` does not mean the approved child delivery paths are disabled.

## Delivery proof boundary

Already proven:

```text
TELEGRAM_API_CREDENTIAL=VALID
TELEGRAM_CHAT_ROUTE=VALID
SUPABASE_SERVICE_CREDENTIAL=VALID
LIVE_DELIVERY_SECRET_CONTRACT=PASS
PROFITLAB_DELIVERY_CURSOR=ADVANCING_AND_CAUGHT_UP_AT_SAMPLE
SIGNAL_CLOSER_PROVIDER=YAHOO
SIGNAL_CLOSER_DRY_RUN=FALSE
```

Not yet empirically proven after the 2026-10-06 activation:

```text
ONE_REAL_QUALIFIED_SIGNAL_TO_TELEGRAM
SAME_SIGNAL_TO_PROFITLAB
POST_ACTIVATION_REAL_CLOSURE_TO_TELEGRAM
POST_ACTIVATION_REAL_CLOSURE_UPDATE_TO_PROFITLAB
```

Reason: no qualified signal occurred in the sampled natural cycles.

Do not force a production trading signal merely to satisfy acceptance. Use an existing supported non-trading delivery smoke-test path if one exists; otherwise wait for and observe the next natural qualified signal.

## Historical corpus result — preserve exactly

```text
DATASET_ID=oanda-warmup-20240101-20260801-20260807-r3
REPLAY_SOURCE_COMMIT=6b437179cc58021aa358b1d0b04c121d9304c660
EVALUATION_START_UTC=2025-12-03T22:00:00Z
EVALUATION_END_UTC_EXCLUSIVE=2026-08-01T00:00:00Z
DECISION_ROWS=32641
POLICY_A_ACCEPTED=478
POLICY_B_ACCEPTED=195
POLICY_C_ACCEPTED=164
PRE_REGISTERED_KILL_THRESHOLD=400
CORPUS_GATE=FAIL
```

Interpretation:

```text
EXISTING_HISTORICAL_CORPUS_SUFFICIENT_FOR_PRIOR_GATE=NO
STRATEGY_EDGE_VALIDATED=NO
STRATEGY_PROFITABILITY_PROVEN_NEGATIVE=NO
```

The 2026-09-03 closure stopped the then-active retrospective validation path. The owner later authorized a new prospective shadow-research path. This does not erase or rewrite the old result.

## Statistical correction that must survive handoff

A genuinely new, frozen, single-hypothesis prospective test does not automatically inherit the historical multiple-testing Bonferroni penalty.

Do not treat any of these as the final required sample size:

```text
N=400
N=500
N=682
N=1446
```

The confirmatory sample size and sequential stopping boundaries must be derived after the measurement pilot establishes the empirical Net-R distribution, execution-cost distribution, ambiguity rate and dependence structure.

Primary future scientific endpoint is expected to be **Net R after realistic execution costs**, not raw win rate. Exact hypothesis is not frozen yet.

`60%` win rate is a future business/product aspiration only, not the primary scientific edge gate.

## Execution/evidence corrections

Do not assume:

- decision/model price equals subscriber-executable price;
- spread is always 1 pip;
- every win is exactly +2R and loss exactly -1R;
- EURUSD and GBPUSD signals are independent;
- M15 OHLC can order TP and SL when both touch in the same candle;
- Telegram API success proves a human saw the message.

Repository evidence confirms that same-candle TP-first logic exists and has been documented as potentially optimistic.

## Existing measurement infrastructure — do not rewrite blindly

The repository already contains substantial controls:

- `tools/watcher_cycle_ledger.py` — bounded current-cycle reconciliation and terminal decision evidence;
- `tools/pipeline_ledger.py` — append-only event ledger with UUID event IDs, process-shared `flock`, UTC display time, monotonic/boot-aware time and atomic compact state updates;
- watcher stale-candle handling that fails closed on missing/unparseable/stale candle evidence.

Do not assume a rewrite is needed. Current Hetzner runtime is already proven active; inspect exact evidence first and change only a specifically proven gap.

## Strategy boundary

Current production/runtime work does not authorize changes to:

- Policy B;
- ADX/RSI/score rules;
- pair/timeframe scope;
- higher-timeframe confirmation logic;
- TP/SL strategy logic;
- baseline trading rules.

## Hetzner / VPS boundary

```text
VPS_ENGINEERING_ARTIFACT=PRESERVE
CURRENT_HETZNER_RUNTIME_STATE=ACTIVE
HETZNER_LIVE_MONEY_CUTOVER=NO
DEPLOYED_RELEASE=4424518e7b42ecf2a070967d626a9ac86bf04d53
```

Do not infer current host state from stale historical GitHub records. Start with `CONTINUITY_CURRENT.md` and the 2026-10-06 production activation audit, then verify live host state when a new action depends on it.

## ProfitLab

```text
PROFITLAB_PUBLIC_PRODUCT=NO
PROFITLAB_PRIVATE_ANALYTICS=YES
PROFITLAB_SOURCE_OF_TRUTH=NO
BOTA_EVIDENCE_SOURCE_OF_TRUTH=YES
```

ProfitLab delivery is armed and the delivery cursor advanced after activation. A new real post-activation qualified signal has not yet been observed publishing to it.

## Exactly one current action

Obtain one bounded dual-sink delivery proof without strategy changes.

Do not start another broad architecture audit, do not retune the strategy, and do not force a production trading signal solely to prove delivery.
