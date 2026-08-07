# BotA Chat Handoff

Last updated: 2026-08-07 18:38 UTC

Read this first in any new AI chat before proposing BotA changes.

## Current grounded answer

BotA is not failing because it cannot generate BUY/SELL directions. The investigation has separated four layers:

1. strategy throughput is low because score and H1 gates reject most tradeable candidates;
2. delivery policy suppresses additional strategy-accepted candidates;
3. recent delivered M15 signal quality is poor, so sending more signals is not a valid repair;
4. historical component/outcome evidence indicates the score likely over-rewards trend intensity and under-prices late-entry/exhaustion risk.

## Current live configuration

```text
PAIRS=EURUSD GBPUSD
TIMEFRAMES=M15
FILTER_SCORE_MIN_ALL=65
H1_TREND_MIN_SCORE=40
H1_VETO_OVERRIDE_SCORE=75
TELEGRAM_MIN_SCORE=70
TELEGRAM_TIER_YELLOW_MIN=70
TELEGRAM_TIER_GREEN_MIN=75
TELEGRAM_COOLDOWN_SECONDS=1800
DRY_RUN_MODE=0
TELEGRAM_ENABLED=1
```

Only EURUSD and GBPUSD are live. A third pair is not currently scanned.

## Strategy funnel

```text
1427 valid BUY/SELL
  -> 903 rejected by M15 score gate
  -> 524 survive score
  -> 410 rejected by H1-neutral veto
  -> 114 survive H1
  -> 4 rejected by H4+D1 opposition
  -> 110 strategy-accepted
```

## Accepted -> Telegram funnel

```text
61 sent
38 cooldown-suppressed
6 Telegram score-gated
1 send failure
```

Telegram transport works. The delivery layer is not the only reason for low signal count.

## Recent signal quality

Read-only Supabase outcome data for BotA M15 signals created on or after 2026-06-01:

```text
TOTAL=13
WINS=3
LOSSES=9
CANCELLED=1
TOTAL_PIPS=-71.40
75-84_TOTAL_PIPS=-36.40
85+_TOTAL_PIPS=-35.00
```

High score has not protected recent signals from poor outcomes.

## March component evidence

The 51 local March outcomes joined 100% to extended score-component rows:

```text
51 rows
13 wins
38 losses
-264.1 pips
```

Key splits:

```text
ADX 20-29: +98.0 pips, 52.9% WR
ADX 30-39: -319.1 pips, 7.7% WR
ADX 40+: -43.0 pips, 25.0% WR
RSI extreme: -229.2 pips, 11.1% WR
RSI stretched: +69.4 pips, 45.5% WR
score 85+: -137.9 pips, 17.6% WR
```

## Counterfactual — 2026-08-07 18:38 UTC

```text
BASELINE: N=51 W=13 L=38 WR=25.5% PIPS=-264.1
SCORE>=70: N=40 W=11 L=29 WR=27.5% PIPS=-180.6
NO_EXTREME_RSI: N=33 W=11 L=22 WR=33.3% PIPS=-34.9
ADX<30: N=17 W=9 L=8 WR=52.9% PIPS=+98.0
ADX<30 + NO_EXTREME: N=12 W=7 L=5 WR=58.3% PIPS=+94.8
SCORE>=70 + ADX<30: N=12 W=9 L=3 WR=75.0% PIPS=+174.2
SCORE>=70 + ADX<30 + NO_EXTREME: N=7 W=7 L=0 WR=100.0% PIPS=+171.0
```

Do not call the final 7/7 subset a 100% strategy. It was found and measured on the same narrow sample and is highly vulnerable to overfitting.

The broad result is more important: `ADX<30` alone changes the 51-row sample from -264.1 to +98.0 pips while retaining 17 trades. ADX 30-39 is poor across all RSI states. Removing extreme RSI helps materially but is not sufficient by itself.

## What is not proven

- `ADX<30` is not yet an approved production gate.
- The 7/7 subset is not proof of perfect accuracy.
- Do not tune more thresholds on these same 51 rows.
- H1 effects cannot be learned from this March sample because all 51 rows were H1 neutral.
- Pair expansion and cooldown changes remain out of scope until signal quality is validated.

## No-change rules

```text
FILTER_SCORE_CHANGED=NO
H1_THRESHOLD_CHANGED=NO
TELEGRAM_SCORE_CHANGED=NO
COOLDOWN_CHANGED=NO
PAIR_LIST_CHANGED=NO
ADX_SCORING_CHANGED=NO
RSI_SCORING_CHANGED=NO
PROVIDER_CHANGED=NO
SUPABASE_CHANGED=NO
```

## Exactly one next proof

Use a separate historical period not used to discover the candidate rule. Freeze these policies before examining outcomes:

```text
A: current production baseline
B: score >=70 AND ADX <30
C: score >=70 AND ADX <30 AND no extreme RSI
```

Run an out-of-sample replay and compare retained signal count, wins/losses, pips, and preferably MAE/MFE. Only then consider a live strategy change.

## Working discipline

1. Inspect before changing.
2. Keep commands small and pager-proof.
3. Validate schemas and time coverage before analysis.
4. Separate runtime, strategy, delivery, and realized outcome quality.
5. Date every material finding in UTC.
6. Full-file replacement only for approved mutations.
7. Branch -> complete content -> verified diff -> PR; never direct-main fallback.
