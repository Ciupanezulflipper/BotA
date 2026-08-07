# BotA ADX / RSI Counterfactual Audit

Recorded: 2026-08-07 18:38 UTC

## Scope

Read-only historical counterfactual using the 51-row local March ledger joined 100% to extended `logs/alerts.csv` score-component rows.

No runtime, strategy, provider, Telegram, Supabase, threshold, cooldown, pair-list, or service mutation was performed.

## Baseline

```text
N=51
W=13
L=38
WR=25.5%
PIPS=-264.1
```

## Counterfactual policies

```text
BASELINE:
N=51 W=13 L=38 WR=25.5% PIPS=-264.1

SCORE>=70:
N=40 W=11 L=29 WR=27.5% PIPS=-180.6

NO_EXTREME_RSI:
N=33 W=11 L=22 WR=33.3% PIPS=-34.9

ADX<30:
N=17 W=9 L=8 WR=52.9% PIPS=+98.0

ADX<30 + NO_EXTREME:
N=12 W=7 L=5 WR=58.3% PIPS=+94.8

SCORE>=70 + ADX<30:
N=12 W=9 L=3 WR=75.0% PIPS=+174.2

SCORE>=70 + ADX<30 + NO_EXTREME:
N=7 W=7 L=0 WR=100.0% PIPS=+171.0
```

## ADX x RSI interaction

```text
20-29 / MODERATE:  n=9  W=4 L=5  WR=44.4% PIPS=+11.0
20-29 / STRETCHED: n=3  W=3 L=0  WR=100%  PIPS=+83.8
20-29 / EXTREME:   n=5  W=2 L=3  WR=40.0% PIPS=+3.2

30-39 / MODERATE:  n=8  W=0 L=8  WR=0.0%  PIPS=-122.4
30-39 / STRETCHED: n=8  W=2 L=6  WR=25.0% PIPS=-14.4
30-39 / EXTREME:   n=10 W=0 L=10 WR=0.0%  PIPS=-182.3

40+ / MODERATE:    n=5  W=2 L=3  WR=40.0% PIPS=+7.1
40+ / EXTREME:     n=3  W=0 L=3  WR=0.0%  PIPS=-50.1
```

## Interpretation

The strongest result is not the 7/7 subset; that subset is too small and was selected on the same data used to discover the rule, so it is highly vulnerable to overfitting.

The robust directional evidence is broader:

1. `ADX<30` alone flips the 51-row sample from -264.1 pips to +98.0 pips while retaining 17 trades.
2. ADX 30-39 is consistently poor across RSI states, including 0/8 moderate and 0/10 extreme.
3. Removing extreme RSI materially improves the sample but remains slightly negative by itself.
4. Combining score >=70 with ADX<30 looks strong in-sample, but this must be validated out-of-sample before production use.

The current score therefore appears miscalibrated around trend-strength / entry-timing interaction. Stronger ADX is being rewarded as if it always improves entry quality, while this sample suggests ADX >=30 often corresponds to mature/late trend entries.

## What is NOT proven

- Do not claim `ADX<30` is the final production rule.
- Do not claim the 7/7 subset implies a 100% strategy.
- Do not tune further on the same 51 rows.
- Do not change live thresholds from this sample alone.
- Do not infer H1 effects from this sample because all 51 rows were H1 neutral.

## Required next validation

Use a separate historical period not used to discover these rules. Replay or classify later M15 signals using fixed candidate policies decided before viewing their outcomes:

```text
Candidate A: score >=70 AND ADX <30
Candidate B: score >=70 AND ADX <30 AND no extreme RSI
Candidate C: current production logic baseline
```

Acceptance must compare retained signal count, wins/losses, total pips, and preferably MAE/MFE on an out-of-sample window.

## Status

```text
COUNTERFACTUAL_COMPLETED=YES
MUTATION_PERFORMED=NO
PRODUCTION_RULE_APPROVED=NO
OVERFIT_RISK=HIGH_FOR_SMALL_SUBSETS
NEXT_ACTION=OUT_OF_SAMPLE_REPLAY
RECORDED_DATE=2026-08-07
```
