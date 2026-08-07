# BotA March Component Outcome Audit

Recorded: 2026-08-07 18:15 UTC

## Scope

Read-only join of `data/ledger.csv` to the extended 25-column rows in `logs/alerts.csv` for the historical March 2026 ledger sample.

No runtime, strategy, provider, Telegram, Supabase, threshold, cooldown, pair-list, or service mutation was performed.

## Join coverage

```text
LEDGER_ROWS=51
JOINED=51
UNMATCHED=0
JOIN_RATE=100.00%
JOINED_WITH_COMPONENTS=51
```

This gives complete component coverage for the local ledger sample.

Important limitation: the ledger covers only about 17.5 hours from 2026-03-09T21:45:07+02:00 through 2026-03-10T15:15:07+02:00. It is a historical diagnostic sample, not current June-August production validation.

## Overall result

```text
WINS=13
LOSSES=38
WIN_RATE=25.49%
TOTAL_PIPS=-264.1
```

## Score calibration

```text
<70:   n=11 W=2 L=9  WR=18.2% PIPS=-83.5
70-74: n=4  W=2 L=2  WR=50.0% PIPS=+2.1
75-84: n=19 W=6 L=13 WR=31.6% PIPS=-44.8
85+:   n=17 W=3 L=14 WR=17.6% PIPS=-137.9
```

The highest score bucket performed worst by both win rate and total pips. This is direct evidence that, in this March sample, score magnitude was not calibrated monotonically to outcome quality.

## RSI entry state

Classification used:

- SELL extreme: RSI <=30
- SELL stretched: RSI 30-35
- SELL moderate: RSI >35
- BUY extreme: RSI >=70
- BUY stretched: RSI 65-70
- BUY moderate: RSI <65

Results:

```text
EXTREME:   n=18 W=2 L=16 WR=11.1% PIPS=-229.2
STRETCHED: n=11 W=5 L=6  WR=45.5% PIPS=+69.4
MODERATE:  n=22 W=6 L=16 WR=27.3% PIPS=-104.3
```

The extreme-RSI group was catastrophically poor. The middle `STRETCHED` zone was the only RSI-state group with positive pips.

Current scoring source rewards absolute RSI distance from 50. Therefore, in this sample, the score increases as the entry moves from the better-performing stretched zone into the much worse extreme zone. This is a strong calibration warning.

## RSI component saturation

```text
NOT_SATURATED: n=51 W=13 L=38 WR=25.5% PIPS=-264.1
SATURATED_15: n=0
```

None of these March rows hit the exact +15 RSI cap. The relevant finding is raw RSI extremity, not exact component saturation.

## MACD component

```text
NOT_SATURATED: n=14 W=2 L=12 WR=14.3% PIPS=-138.1
SATURATED_15: n=37 W=11 L=26 WR=29.7% PIPS=-126.0
```

MACD saturation did not explain the losses by itself. Saturated MACD was still negative, but materially better than non-saturated MACD in this sample.

## ADX band

```text
ADX 20-29: n=17 W=9 L=8  WR=52.9% PIPS=+98.0
ADX 30-39: n=26 W=2 L=24 WR=7.7%  PIPS=-319.1
ADX 40+:   n=8  W=2 L=6  WR=25.0% PIPS=-43.0
```

This is the strongest component split in the sample. Moderate ADX 20-29 was profitable; ADX 30-39 was severely negative.

Current production scoring increases ADX contribution monotonically from 0 to 10 and awards the maximum 10 points for ADX >=30. In this March sample, that mapping is directionally opposite to realized trade quality.

## H1 state

```text
neutral: n=51 W=13 L=38 WR=25.5% PIPS=-264.1
```

H1 provides no within-sample discrimination because every row is neutral. This likely reflects the historical configuration in use during the March ledger window and cannot be used to judge the current H1 confirmation/veto policy.

## Pair

```text
EURUSD: n=27 W=7 L=20 WR=25.9% PIPS=-107.6
GBPUSD: n=24 W=6 L=18 WR=25.0% PIPS=-156.5
```

Both pairs were poor. The defect is not isolated to one pair in this sample.

## Direction

```text
BUY:  n=46 W=13 L=33 WR=28.3% PIPS=-187.9
SELL: n=5  W=0  L=5  WR=0.0%  PIPS=-76.2
```

SELL is too small a sample for a broad direction conclusion. BUY dominates the sample and is still materially negative.

## Combined RSI + MACD saturation

```text
NOT_BOTH=51
BOTH_SATURATED=0
```

No conclusion is available from this combined exact-saturation test.

## Cross-check against recent June-July component evidence

The retained recent component sample already showed high-score losses at ADX values around 29.9, 35.8, 36.0 and 40.6, while the one confidently aligned winner in that small set had ADX 26.2. This is directionally consistent with the March ADX split, though the recent sample is too small to prove an exact threshold.

Recent extreme-RSI high-score losses also existed (for example SELL RSI 17.2 and 21.2). That is directionally consistent with the March extreme-RSI result.

## Current interpretation

The scoring system appears to reward trend intensity after the relationship with entry quality has become non-linear.

The two strongest evidence-backed concerns are:

1. **ADX calibration:** current code gives its maximum ADX score at >=30, while this March sample shows 30-39 as the worst outcome band.
2. **RSI calibration:** current code rewards greater absolute distance from 50, while the March sample shows extreme RSI as much worse than the intermediate stretched zone.

This supports the working hypothesis that BotA measures trend strength more strongly than entry timing/late-entry risk.

## What is not yet proven

- The exact production replacement formula is not proven.
- An ADX >=30 hard reject is not yet justified solely from this one narrow March window.
- The current H1 policy is not tested by this sample because all March rows are H1 neutral.
- MACD is not established as the root cause.
- Pair-specific or direction-specific changes are not justified.

## Mutation status

```text
STRATEGY_MUTATION_ALLOWED=NO
THRESHOLD_MUTATION_ALLOWED=NO
COOLDOWN_MUTATION_ALLOWED=NO
PAIR_LIST_MUTATION_ALLOWED=NO
```

## Next exact proof

Run a read-only counterfactual evaluation on the 51 joined rows and the recent component-matched published signals. Compare simple candidate policies without changing production, especially:

- reject or penalize extreme RSI rather than reward it;
- reduce or reverse the ADX bonus above 30;
- combine both conditions;
- measure retained signal count, win rate, and total pips.

The goal is to identify a minimal scoring correction that improves outcome quality before any live code mutation.
