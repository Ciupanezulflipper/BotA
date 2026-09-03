# BotA Final Strategy Closure — 2026-09-03

## Status

```text
FINAL_STRATEGY_VERDICT=CLOSE
ACTIVE_TRADING_STRATEGY_VALIDATION=STOP
PRODUCTION_CUTOVER_AUTHORIZED=NO
HETZNER_PRODUCTION_CUTOVER=BLOCKED
STRATEGY_TUNING_AUTHORIZED=NO
ADDITIONAL_HISTORY_ACQUISITION_AUTHORIZED=NO
PROFITLAB_DEPENDENCY_ON_BOTA=REMOVED
```

This record closes BotA as an **active trading-strategy validation project**. It does not assert that every BotA trade loses, and it does not delete the engineering work. The closure is a governance/sample-sufficiency decision made under a pre-registered kill gate.

## Pre-registered corpus gate

The decision thresholds were fixed before the final full frozen Policy-B count was known:

```text
POLICY_B_ACCEPTED < 400      -> KILL
400 <= POLICY_B_ACCEPTED < 600 -> continue only if economics are exceptional
600 <= POLICY_B_ACCEPTED < 800 -> borderline
POLICY_B_ACCEPTED >= 800     -> corpus gate PASS
```

Policy B is:

```text
current production acceptance
AND score >= 70
AND ADX < 30
```

## Exact deterministic corpus result

Canonical dataset:

```text
DATASET_ID=oanda-warmup-20240101-20260801-20260807-r3
RAW_START_UTC=2024-01-01T00:00:00Z
RAW_END_UTC_EXCLUSIVE=2026-08-01T00:00:00Z
PAIRS=EURUSD GBPUSD
TIMEFRAMES=M15 H1 H4 D1
```

Pinned replay source identity used for the corpus run:

```text
REPLAY_SOURCE_COMMIT=6b437179cc58021aa358b1d0b04c121d9304c660
MIN_WARMUP_BARS=500
```

Read-only Termux execution derived the earliest verifier-valid evaluation start from the local immutable dataset and then ran the pinned deterministic replay:

```text
EVALUATION_START_UTC=2025-12-03T22:00:00Z
EVALUATION_END_UTC_EXCLUSIVE=2026-08-01T00:00:00Z
REPLAY_STATUS=COMPLETE
REPLAY_GRADE=DETERMINISTIC_PRODUCTION_RULES_WITH_PROVIDER_SUBSTITUTION
DECISION_ROWS=32641
POLICY_A_ACCEPTED=478
POLICY_B_ACCEPTED=195
POLICY_C_ACCEPTED=164
REJECTION_STAGES={"ACCEPTED":478,"H1_CONFIRM":1841,"H4_D1_CONFIRM":65,"M15_SETUP_OR_SCORE":15296,"MARKET_CLOSED":14961}
PAIR_DECISION_ROWS={"EURUSD":16321,"GBPUSD":16320}
```

Mutation proof:

```text
REPOSITORY_STATE_UNCHANGED=YES
DATASET_MANIFEST_UNCHANGED=YES
PRODUCTION_CACHE_UNCHANGED=YES
PRODUCTION_STRATEGY_MUTATED=NO
```

The decisive comparison is therefore exact under the frozen contract:

```text
POLICY_B_ACCEPTED=195
PRE_REGISTERED_KILL_THRESHOLD=400
CORPUS_GATE=FAIL
```

## Warm-up correction

An earlier argument claimed that all 500 D1 bars were practically necessary because EMA/Wilder calculations retain recursive dependence on older observations. That argument is withdrawn as materially overstated.

The frozen replay does feed up to 500 completed candles into the indicator engine and the verifier requires 500 pre-evaluation candles. However, the D1 voting indicators are short-period EMA9/EMA21/RSI14/MACD 12/26/9. Old-state influence after roughly 200–300 bars is numerically negligible for normal Forex decision precision.

The honest reason not to replace 500 with 200 after seeing the result is **procedural**:

- 500 defines the frozen replay contract that produced the exact 195 result;
- changing it now creates a different sensitivity experiment;
- a 200-bar full-corpus replay has not been executed;
- earlier projections around 500–550 Policy-B accepts are withdrawn as unobserved extrapolations.

Therefore:

```text
500_BAR_RULE=PROTOCOL_CHOICE_NOT_PHYSICS
200_BAR_REPLAY=UNEXECUTED_SENSITIVITY
PROJECTED_200_BAR_POLICY_B_COUNT=UNKNOWN
195_COUNT_INVALIDATED_BY_WARMUP=NO
```

## Economic evidence — what is and is not known

The 195 replay candidates were counted; their complete frozen outcomes have **not** been resolved in this closure record. Therefore BotA is not being closed because the 195 trades were proven to lose.

Previously used economics were illustrative:

```text
ILLUSTRATIVE_TRUE_WIN_RATE=40%
PAYOFF_MODEL=+2R winner / -1R loser
GROSS_EXPECTANCY_AT_40%=+0.20R/trade
AVERAGE_RISK_ASSUMPTION=16.56 pips
BASELINE_COST_ASSUMPTION=1 pip
ILLUSTRATIVE_NET_EXPECTANCY≈+0.14R/trade
ADDITIONAL_EDGE_ERASURE≈2.3 pips/trade
```

The 40% win rate is hypothetical, not an observed result for the 195 corpus. The prior 13-trades/month example was also illustrative and must not be presented as the observed corpus frequency. A simple count divided by the roughly eight-month evaluation span is about 24 Policy-B accepts/month, but that does not establish realized profitability, independence, or executable live frequency.

The economics therefore support only this bounded statement:

> Even an optimistic modest edge would have limited execution margin under Telegram -> human -> XTB manual entry, but the closure itself rests on the pre-registered corpus gate, not on a measured 40% win rate.

## External adversarial audit

The same evidence package was reviewed by Kimi, Perplexity, Grok, DeepSeek and Gemini. All returned `CLOSE` with stated confidence between 87% and 95%.

That agreement is **not independent evidence** because all models received the same framing document. The useful audit value is in the substantive challenges they surfaced:

- exact 195 count is valid under the frozen contract;
- 500 vs 200 is a legitimate sensitivity/protocol issue, not a fatal flaw in 195;
- the 200-bar candidate count is unknown until executed;
- 195 signals must not be treated as 195 independent Bernoulli trials without checking clustering;
- actual outcomes of the 195 candidates are unresolved;
- the 40% win-rate economic case is hypothetical;
- the 13/month figure was not the observed corpus rate.

A final Claude executive review agreed with closure while explicitly warning that shared-prompt model consensus should not be treated as independent convergence.

## Closure governance

The pre-registered rule is honored:

```text
195 < 400 -> CLOSE
```

No strategy rescue work is authorized, including:

- lowering thresholds;
- changing Policy B;
- new GEMs;
- new indicators or filters;
- changing warm-up to obtain a larger sample and treating it as the original experiment;
- acquiring several more years of data to reopen validation;
- building another open-ended PnL/replay project;
- using market-open timing as a reason to continue;
- promoting the Hetzner R5 shadow to Production.

## Optional outcome resolution — death certificate only

A one-time read-only resolution of the 195 frozen Policy-B candidates may be performed later for historical completeness **only if the following constraint remains locked before execution**:

```text
OUTCOME_RESOLUTION_PURPOSE=HISTORICAL_CLOSING_RECORD_ONLY
OUTCOME_RESULT_CAN_REOPEN_BOTA=NO
STRATEGY_CHANGE=NO
PROTOCOL_CHANGE=NO
PRODUCTION_DEPLOYMENT=NO
```

A strong outcome result would be historically interesting but does not retroactively change the failed pre-registered corpus gate.

## Hetzner / VPS disposition

The VPS migration lane had reached R5 no-side-effect shadow operation, not Production cutover. BotA is now closed before Production migration.

```text
VPS_R5_HISTORICAL_ENGINEERING_VALUE=PRESERVE
VPS_PRODUCTION_CUTOVER=DO_NOT_PROCEED
PR120_MERGE_AUTHORITY=REVOKED_BY_PROJECT_CLOSURE
MARKET_OPEN_LIVE_ACCEPTANCE=NO_LONGER_REQUIRED
```

Stopping or removing any already-running shadow service is an operational cleanup action and must be performed separately with host evidence; this documentation change does not claim to have mutated Hetzner.

## ProfitLab disposition

ProfitLab is not validated as a business merely because its subscription/auth/payment shell works. BotA is no longer an authorized signal dependency.

```text
PROFITLAB_SHELL=PRESERVE_AS_INFRASTRUCTURE
PROFITLAB_BOTA_SIGNAL_DEPENDENCY=PARKED
PROFITLAB_VALIDATED_BUSINESS=NO
```

Any future use of the ProfitLab shell requires a separate product thesis and evidence. It must not silently become a reason to restart BotA.

## Final statement

```text
BOTA_STRATEGY_PROJECT=CLOSED
REASON=PRE_REGISTERED_CORPUS_GATE_FAILED
EXACT_POLICY_B_CORPUS=195
KILL_THRESHOLD=400
STRATEGY_PROFITABILITY_PROVEN_NEGATIVE=NO
STRATEGY_EDGE_VALIDATED=NO
HETZNER_PRODUCTION_DEPLOYMENT=NO
REOPEN_WITH_MORE_TUNING_OR_DATA=NO
```

Historical engineering artifacts, runtime reliability work, deterministic replay tooling and lessons learned are retained for reuse. They are not authorization to resume BotA trading-strategy validation.