# BotA Chat Handoff

Last updated: 2026-08-07 18:46 UTC

Read this first in any new AI chat before proposing BotA changes.

## Current grounded answer

BotA is not failing because it cannot generate BUY/SELL directions. The investigation now separates four layers:

1. strategy throughput is low because score and H1 gates reject most tradeable candidates;
2. delivery policy suppresses additional strategy-accepted candidates;
3. recent delivered M15 signal quality is poor, so simply sending more signals is not a valid repair;
4. both March component/outcome evidence and a later June-July matched subset point to ADX/late-entry score calibration as the strongest strategy concern.

## Current live configuration

```text
PAIRS=EURUSD GBPUSD
TIMEFRAMES=M15
FILTER_SCORE_MIN_ALL=65
H1_TREND_MIN_SCORE=40
H1_VETO_OVERRIDE_SCORE=75
H1_VETO_OVERRIDE_ADX=40
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

Telegram transport works. Delivery is not the primary strategy-quality problem.

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
BASELINE: N=51 W=13 L=38 PIPS=-264.1
ADX<30: N=17 W=9 L=8 PIPS=+98.0
SCORE>=70 + ADX<30: N=12 W=9 L=3 PIPS=+174.2
SCORE>=70 + ADX<30 + NO_EXTREME: N=7 W=7 L=0 PIPS=+171.0
```

The 7/7 result is in-sample and high-overfit risk. Do not treat it as a 100% strategy.

## June-July temporal cross-check — 2026-08-07 18:46 UTC

The March-derived rules were frozen and applied to a later published-outcome set. Nine of 13 outcomes matched retained local component rows:

```text
PUBLISHED=13
MATCHED=9
UNMATCHED=4
MATCH_RATE=69.2%
A_CURRENT_MATCHED_BASELINE: N=9 W=2 L=7 PIPS=-70.2
B_SCORE70_ADX_LT30: N=5 W=2 L=3 PIPS=+13.1
C_SCORE70_ADX_LT30_NO_EXTREME: N=4 W=2 L=2 PIPS=+28.9
ADX_30_39: N=3 W=0 L=3 PIPS=-57.4
ADX_40_PLUS: N=1 W=0 L=1 PIPS=-25.9
```

This later subset points in the same direction as March: all matched ADX >=30 signals lost. However, the match rate is only 69.2%, so this is not enough to change production.

## Four unmatched published outcomes

```text
2026-06-23 GBPUSD SELL score=79 entry=1.32179 WIN +33.1
2026-06-23 EURUSD SELL score=78 entry=1.13862 LOSS -13.3
2026-06-24 GBPUSD SELL score=77 entry=1.31448 LOSS -21.0
2026-06-26 EURUSD SELL score=75 entry=1.13892 CANCELLED 0.0
```

The next investigation must determine whether their local component rows are retained but outside the tight match tolerances, or absent from current local retention.

## Supabase timestamp caution

Exact Supabase `created_at` values were re-read on 2026-08-07 and do not directly equal several known local watcher decision timestamps. Do not join by Supabase `created_at` alone until publication/storage semantics are proven.

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

Inspect the nearest local `alerts.csv` candidates for the four unmatched June 23-26 published outcomes using relaxed matching and bounded output. If they cannot be recovered, record a retention gap and proceed to a true historical replay using raw candles and the live scoring path.

## Working discipline

1. Inspect before changing.
2. Keep commands small and pager-proof.
3. Validate schemas and time coverage before analysis.
4. Separate runtime, strategy, delivery, and realized outcome quality.
5. Date every material finding in UTC.
6. Full-file replacement only for approved mutations.
7. Branch -> complete content -> verified diff -> PR; never direct-main fallback.
