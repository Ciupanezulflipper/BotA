# BotA AI Start Here

Last updated: **2026-10-15 UTC**

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
DEPLOYED_RELEASE=98b93ce5e0c57330b9b2630340ddc448776da1e3
DEPLOYED_TREE=d09337fbe4536975477867a4f11c49fcdf3cc152
TARGET_RUNTIME_INSTANCE_ID=459efa86-4678-4f61-bbff-06f62af3326d
BOTA_SERVICE=active
BOTA_SERVICE_ENABLED=enabled
PROVIDER_CONTRACT=YAHOO
THREE_PAIR_M15_SCAN=RUNNING
SIGNAL_CLOSER=RUNNING
PROFITLAB_DELIVERY_PATH=ARMED
LIVE_DELIVERY_CONTRACT=PASS

WEEKEND_REPORT_CLASSIFIER_FIX=PASS
MARKET_PHASE_HETZNER_FIX=PASS
POST_FIX_FULL_MARKET_OPEN_SESSION=PASS
OCT14_MARKET_OPEN_WATCHER_CYCLES=156
OCT14_EACH_PAIR_SCANS=156
OCT14_QUALIFIED_SIGNALS=0
OCT14_RUNTIME_STATUS=NORMAL

TELEGRAM_CREDENTIAL_VALIDATED=YES
SUPABASE_SERVICE_CREDENTIAL_VALIDATED=YES
REAL_TELEGRAM_NON_TRADING_DELIVERY_POST_ACTIVATION=PASS
REAL_TELEGRAM_TRADING_SIGNAL_POST_ACTIVATION=NOT_YET_OBSERVED
REAL_PROFITLAB_SIGNAL_POST_ACTIVATION=NOT_YET_OBSERVED
DELIVERY_NOT_OBSERVED_REASON=NO_NATURAL_QUALIFIED_SIGNAL_YET

ANDROID_ACTIVE_SCANNER=NO
ANDROID_ROLE=CONTROL_AND_OBSERVATION_ONLY
STRATEGY_TUNING=NO
PAIR_CHANGES=NO
TIMEFRAME_CHANGES=NO
FORCED_SIGNAL_GENERATION=NO

CURRENT_PHASE=OBSERVE_STORE_COLLECT_ANALYZE
NEXT_ACTION=OBSERVE_NEXT_NATURAL_GREEN_AND_PROVE_DUAL_SINK_LIFECYCLE
FURTHER_BROAD_AI_REVIEW=STOP
```

Current operational handoff:

`CONTINUITY_CURRENT.md`

Latest post-fix evidence is recorded directly in this file and in `CONTINUITY_CURRENT.md`.

Historical activation baseline:

`audits/BOTA_HETZNER_PRODUCTION_ACTIVATION_2026-10-06.md`

## Production runtime interpretation

The Oct 6 activation baseline release was `4424518e7b42ecf2a070967d626a9ac86bf04d53`.

Current production is newer:

```text
DEPLOYED_RELEASE=98b93ce5e0c57330b9b2630340ddc448776da1e3
RUNTIME_INSTANCE=459efa86-4678-4f61-bbff-06f62af3326d
```

Post-activation bounded corrections:
- weekend daily-report classifier;
- Hetzner market-phase invocation through `bash`.

No strategy thresholds or scope were changed.

A full Oct 14 market-open session completed with 156 watcher cycles and 156 scans for each of EURUSD, GBPUSD and USDJPY, with zero qualified setups and final `BOTA • STATUS: NORMAL`.

Do not misstate zero qualified setups as a delivery or runtime failure.

## Delivery proof boundary

Already proven:

```text
TELEGRAM_API_CREDENTIAL=VALID
TELEGRAM_CHAT_ROUTE=VALID
SUPABASE_SERVICE_CREDENTIAL=VALID
LIVE_DELIVERY_SECRET_CONTRACT=PASS
TELEGRAM_NON_TRADING_EXTERNAL_DELIVERY=PASS
PROFITLAB_DELIVERY_PATH=ARMED
```

Not yet empirically proven after activation:

```text
ONE_REAL_QUALIFIED_SIGNAL_TO_TELEGRAM
SAME_SIGNAL_TO_PROFITLAB
POST_ACTIVATION_REAL_CLOSURE_TO_TELEGRAM
POST_ACTIVATION_REAL_CLOSURE_UPDATE_TO_PROFITLAB
LIVE_DUPLICATE_FREE_RETRY_RESTART_LIFECYCLE
```

Reason: no natural qualified GREEN has occurred yet.

Do not force a production trading signal merely to satisfy acceptance.

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

## Current production diagnostics that must survive handoff

### macro6
`NEWS_ON=0` makes `macro6=3` neutral/informational. It is not an active production blocker.

### H1 override drift
Historical documentation referenced H1 override 75 while current effective default is 85 because the runtime config omits the override keys.

Read-only post-Oct6 counterfactual:
- rows in 75–84.99 neutral-H1 override band: 0;
- proven suppressed signals from 85 vs 75: 0.

Do not change this threshold based on current evidence.

### ADX tension
Scoring can award +10 when ADX >= 30, while final Policy B requires ADX < 30.

Historical evidence supported keeping the ADX < 30 guard. Do not remove or retune it merely because strong market movement is visible on higher-timeframe charts.

### market phase
The prior Termux shebang caused direct invocation of `market_open.sh` from scoring to fail on Hetzner, creating `phase=Unknown` and an illegitimate -5 penalty.

Current release `98b93ce...` fixes both scoring invocations by calling `bash market_open.sh`.

## Oct 14 post-fix rejection audit

The latest read-only ledger decomposition found 75 tradeable BUY/SELL rows across 41 unique market states.

```text
SCORE_LT_65_REJECTIONS=72
H1_NEUTRAL_VETO_ROWS=3
ENTRY_INVALID_ROWS=0
RR_NONPOSITIVE_ROWS=0
ADX_GE_30_ROWS=27

EURUSD_MAX_SCORE=59.2
GBPUSD_MAX_SCORE=72.1
USDJPY_MAX_SCORE=63.3
```

The only rows above 70 were three repeated observations of one GBPUSD SELL state at score 72.1, ADX 46.3, `phase=Open`, with H1 neutral veto.

Do not reinterpret this as a reason to loosen the strategy. Current evidence supports continued clean post-fix observation.

## Strategy boundary

Current production/runtime work does not authorize changes to:
- Policy B;
- ADX/RSI/score rules;
- pair/timeframe scope;
- higher-timeframe confirmation logic;
- TP/SL strategy logic;
- baseline trading rules.

The correct next evidence is clean post-fix observation, not tuning.

## ProfitLab

```text
PROFITLAB_PUBLIC_PRODUCT=NO
PROFITLAB_PRIVATE_ANALYTICS=YES
PROFITLAB_SOURCE_OF_TRUTH=NO
BOTA_EVIDENCE_SOURCE_OF_TRUTH=YES
```

As of 2026-10-15, no new post-Oct14 natural BotA signal exists in `public.signals`.

The `public.bot_runtime_health` row is stale legacy Termux observability and must not be used as current Hetzner runtime truth.

## Operating mode

```text
OBSERVE=YES
STORE=YES
COLLECT=YES
ANALYZE=YES
STRATEGY_CHANGE=NO
RUNTIME_CHANGE=NO_UNLESS_NEW_DEFECT_PROVEN
```

## Exactly one current action

Observe the next natural qualified GREEN and prove its complete dual-sink lifecycle. Until then, continue passive evidence collection and analysis.
