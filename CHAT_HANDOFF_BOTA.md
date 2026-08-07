# BotA Chat Handoff

Last updated: 2026-08-07 18:58 UTC

Read this first in any new AI chat before proposing BotA changes.

## Current grounded answer

BotA is not failing because it cannot generate BUY/SELL directions. The investigation now separates four layers:

1. strategy throughput is low because score and H1 gates reject most tradeable candidates;
2. delivery policy suppresses additional strategy-accepted candidates;
3. recent delivered M15 signal quality is poor, so simply sending more signals is not a valid repair;
4. both March component/outcome evidence and the recoverable June-July subset point to ADX/late-entry score calibration as the strongest strategy concern.

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

## June-July temporal cross-check

Nine of 13 published outcomes matched retained local component rows:

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

This later subset points in the same direction as March: all matched ADX >=30 signals lost. However, 69.2% match coverage is not enough to change production.

## Local retention gap — 2026-08-07 18:58 UTC

The four unmatched June 23-26 outcomes were searched with wider local tolerances.

```text
TARGETS_TOTAL=4
TARGETS_WITH_NEARBY_ROWS=1
TARGETS_WITH_RELAXED_MATCH=0
TARGETS_WITH_RELAXED_COMPONENT_MATCH=0
VERDICT=LOCAL_RETENTION_GAP_CONFIRMED
```

Three targets had no same-pair/same-direction M15 candidate rows within +/-2 days. The fourth had nearby rows but no plausible identity match. The missing component rows are absent from current local retention.

Therefore the full 13/13 component validation cannot be reconstructed from `logs/alerts.csv`. Stop tuning match tolerances; move to true replay.

## Supabase timestamp caution

Exact Supabase `created_at` values do not directly equal several known watcher decision timestamps. Do not join by Supabase `created_at` alone until publication/storage semantics are proven.

## Closed/non-dominant causes

- zero entry/SL/TP: HOLD-only symptom;
- `macro6=3`: neutral;
- RR text: advisory;
- H4+D1 opposition: rare;
- Telegram transport: functioning;
- cooldown: coarse but no direction-reversal suppression observed;
- missing June 23-26 component rows: confirmed local retention gap, not a matching-tolerance issue.

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

Do not use `tools/backtest_bota.py` as validation of the production strategy because its scoring/pullback implementation is not the live watcher path.

## Exactly one next proof

Run a true historical replay from raw candles through the live production scoring/fusion semantics with frozen policies:

```text
A: current production baseline
B: score >=70 AND ADX <30
C: score >=70 AND ADX <30 AND no extreme RSI
```

Compare signal count, wins/losses, pips, and preferably MAE/MFE. Only then consider a strategy mutation.

## Working discipline

1. Inspect before changing.
2. Keep commands small and pager-proof.
3. Validate schemas and time coverage before analysis.
4. Separate runtime, strategy, delivery, and realized outcome quality.
5. Date every material finding in UTC.
6. Full-file replacement only for approved mutations.
7. Branch -> complete content -> verified diff -> PR; never direct-main fallback.
