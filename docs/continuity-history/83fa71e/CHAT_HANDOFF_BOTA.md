# BotA Chat Handoff

Last updated: **2026-10-15 UTC**

Read this first in any new AI session before proposing BotA work.

## Current grounded answer

```text
BOTA_EDGE_STATUS=UNVALIDATED
LIVE_MONEY_TRADING=NO
PRIMARY_RUNTIME_TARGET=HETZNER
CURRENT_HETZNER_RUNTIME_STATE=ACTIVE
DEPLOYED_RELEASE=98b93ce5e0c57330b9b2630340ddc448776da1e3
RUNTIME_INSTANCE=459efa86-4678-4f61-bbff-06f62af3326d
PROVIDER=YAHOO
PAIRS=EURUSD,GBPUSD,USDJPY
TIMEFRAME=M15
ANDROID_ACTIVE_SCANNER=NO

WEEKEND_REPORT_FIX=PASS
MARKET_PHASE_FIX=PASS
POST_FIX_FULL_SESSION=PASS
OCT14_CYCLES=156
OCT14_SCANS_PER_PAIR=156
OCT14_QUALIFIED=0
OCT14_STATUS=NORMAL

REAL_TELEGRAM_TRADING_SIGNAL_POST_ACTIVATION=NOT_YET_OBSERVED
REAL_PROFITLAB_SIGNAL_POST_ACTIVATION=NOT_YET_OBSERVED
WHY=NO_NATURAL_QUALIFIED_SIGNAL_YET

CURRENT_PHASE=OBSERVE_STORE_COLLECT_ANALYZE
STRATEGY_TUNING=NO
NEXT_ACTION=OBSERVE_NEXT_NATURAL_GREEN_AND_PROVE_DUAL_SINK_LIFECYCLE
FURTHER_BROAD_AI_REVIEW=STOP
```

Canonical current record:
`CONTINUITY_CURRENT.md`

Latest post-fix proof is recorded in `CONTINUITY_CURRENT.md`.

Historical activation baseline:
`audits/BOTA_HETZNER_PRODUCTION_ACTIVATION_2026-10-06.md`

## Current acceptance boundary

Already proven:
- Hetzner runtime active/enabled;
- Yahoo provider path;
- three-pair M15 scanning;
- market-phase fix;
- weekend report fix;
- Telegram non-trading external send;
- Supabase credential contract;
- full post-fix daily accounting.

Still pending:
- first natural GREEN to Telegram;
- same signal in ProfitLab;
- natural closure to both sinks;
- empirical retry/restart dedup on a real lifecycle.

Do not force a signal to close these gates.

## Latest Oct 14 audit

Read-only alert-ledger summary:

```text
TRADEABLE_ROWS=75
UNIQUE_STATES=41
ROWS_BELOW_SCORE_65=72
H1_NEUTRAL_ROWS=3
ENTRY_INVALID_ROWS=0
RR_NONPOSITIVE_ROWS=0
MAX_EURUSD=59.2
MAX_GBPUSD=72.1
MAX_USDJPY=63.3
```

The highest-scoring case was one repeated GBPUSD SELL state at 72.1 with ADX 46.3, open market phase, and neutral H1 context.

This is an observation record only. Current action remains continued collection and analysis.

## Oct 15 early-session H1 investigation

Fresh post-fix production evidence from 07:00–07:15 UTC showed:
- USDJPY BUY scored 65.5 at 07:00, 07:05 and 07:10;
- USDJPY BUY strengthened to 66.6 at 07:15;
- ADX remained inside the current Policy-B boundary at 24.1 then 22.4;
- market phase was `Open`;
- entry / SL / TP were populated;
- the decisive rejection was `H1_trend_opposite`.

The USDJPY H1 files were fresh at about 07:13 UTC and the indicator cache reported:
- `tf_ok=true`;
- `tf_actual_min=60`;
- `weak=false`;
- EMA9 below EMA21, consistent with bearish H1 context while M15 was BUY.

However, the H1 candle file also contained an extra live row at `2026-10-15 07:13:14` with identical open/high/low/close values, while `final_runner.py` computes indicators over all returned rows and selects `df.iloc[-1]`.

Therefore:

```text
H1_DATA_FRESH=YES
H1_OPPOSITE_CLASSIFICATION_PLAUSIBLE=YES
H1_FORMING_CANDLE_INFLUENCE=POSSIBLE_NOT_YET_PROVEN
CLOSED_BAR_INTEGRITY_DEFECT=NOT_YET_CONFIRMED
```

The next action is one read-only code-path inspection to determine whether the production H1 veto consumes the forming H1 row or only the last closed H1 candle. No strategy change is authorized.

## Oct 15 closed-bar integrity finding — CONFIRMED

The production H1 confirmation path is now proven end-to-end:

```text
Yahoo raw H1 payload
  -> tools/data_fetch_candles.sh
  -> cache/USDJPY_H1.json
  -> tools/build_indicators.py
  -> cache/indicators_USDJPY_H1.json
  -> tools/scoring_engine.sh USDJPY H1
  -> tools/m15_h1_fusion_legacy.sh
  -> H1_trend_opposite veto
```

Observed production evidence at 07:13 UTC contained an extra USDJPY H1 row timestamped `2026-10-15 07:13:14` with identical OHLC values while the 07:00-08:00 H1 candle was still forming.

`build_indicators.py` does not discard forming bars. It normalizes all provider rows, then computes EMA/RSI/MACD/ADX from the complete list and stores the last derived values. `scoring_engine.sh` reads that indicator bundle for the requested timeframe, and the M15/H1 fusion uses the H1 scorer output directly.

Therefore:

```text
H1_FORMING_CANDLE_INFLUENCE=CONFIRMED
H1_CLOSED_BAR_INTEGRITY_DEFECT=CONFIRMED
USDJPY_0700_0715_H1_VETO_POTENTIALLY_CONTAMINATED=YES
STRATEGY_TUNING_AUTHORIZED=NO
PRODUCTION_FIX_AUTHORIZED=NO
```

Important scope warning: the same shared indicator builder serves M15, H1, H4 and D1. Before changing code, verify whether forming-row contamination is present on each production timeframe so the repair boundary is correct and not H1-specific by assumption.

## Oct 15 forming-bar counterfactual — material impact confirmed

A read-only comparison rebuilt production indicators twice from the same candle CSVs: once with all provider rows, and once with only candles whose full timeframe had completed by the current UTC time.

Results:

```text
FORMING_BAR_CONTAMINATION_SCOPE=EURUSD,GBPUSD,USDJPY / M15,H1,H4,D1
MATERIAL_DECISION_IMPACT=CONFIRMED

USDJPY_M15_CURRENT_BIAS=SELL
USDJPY_M15_CLOSED_ONLY_BIAS=HOLD

USDJPY_H1_CURRENT_BIAS=SELL
USDJPY_H1_CLOSED_ONLY_BIAS=SELL

PRIOR_0700_0715_H1_VETO_FLIP=NOT_PROVEN
```

The current USDJPY M15 example proves the shared forming-row defect can change a live directional classification, not merely indicator decimals.

At the sampled time:
- M15 datasets had one incomplete/live row removed;
- H1 and H4 datasets had two rows removed, showing both a current timeframe bar and an additional live snapshot row could enter calculations;
- D1 had one incomplete/current row removed.

The H1 bias happened to remain SELL in this snapshot, so this evidence does not prove that the earlier 07:00–07:15 USDJPY H1 veto would have flipped under closed-bar-only semantics.

A second blind spot also surfaced: H4 rebuilt with only 28 total / 26 closed rows, below `build_indicators.py` minimum of 60 bars, producing zeroed indicator values in this read-only calculation. Direct production H4 cache status must be verified before repair design.

```text
CLOSED_BAR_REPAIR_REQUIRED=YES
REPAIR_SCOPE=SHARED_INDICATOR_PATH_NOT_H1_ONLY
H4_DATA_SUFFICIENCY_STATUS=VERIFY_NEXT
STRATEGY_TUNING=NO
PRODUCTION_WRITE=NO
```

## Oct 15 H4 production health — defect confirmed

Read-only production indicator health inspection showed the same H4 failure on all three active pairs:

```text
EURUSD_H4 error=insufficient_data weak=true ema9=0 ema21=0 adx=0
GBPUSD_H4 error=insufficient_data weak=true ema9=0 ema21=0 adx=0
USDJPY_H4 error=insufficient_data weak=true ema9=0 ema21=0 adx=0
```

The production fetcher currently requests Yahoo H4 with a `5d` range while `build_indicators.py` requires at least 60 normalized candles. The observed H4 datasets contain only about 28 rows, so the H4 indicator bundle cannot become healthy.

Operational effect:
- H4 trend context is unavailable across EURUSD, GBPUSD and USDJPY;
- the M15/H1 fusion sees zeroed H4 EMA context as HOLD rather than a usable H4 trend;
- any H4 confirmation/opposition logic is therefore weakened or inactive until the data horizon is repaired.

Combined repair scope is now proven:

```text
DEFECT_1=FORMING_UNCLOSED_CANDLES_ENTER_SHARED_INDICATOR_PATH
DEFECT_2=H4_FETCH_HORIZON_TOO_SHORT_FOR_60_BAR_MINIMUM
AFFECTED_PAIRS=EURUSD,GBPUSD,USDJPY
AFFECTED_TF=M15,H1,H4,D1 for defect 1; H4 for defect 2
MATERIAL_DECISION_IMPACT=CONFIRMED
STRATEGY_TUNING=NO
PRODUCTION_WRITE=NO
NEXT_ACTION=ISOLATED_LOCAL_REPAIR_CANDIDATE
```

## ProfitLab note

ProfitLab is a consumer, not trading-logic authority.
Current `public.bot_runtime_health` is stale Termux-era data and must not override current Hetzner evidence.

## Strategy boundary

No change to Policy B, score/ADX/RSI thresholds, pairs, timeframe, H1 confirmation, or TP/SL logic.

Higher-timeframe visual market movement is not itself proof that a valid M15 Policy-B setup existed.

## Exactly one next action

Observe, store, collect and analyze clean post-fix evidence until the next natural qualified GREEN appears, then reconcile the complete Telegram + ProfitLab lifecycle.
