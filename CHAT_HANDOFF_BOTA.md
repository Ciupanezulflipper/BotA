# BotA Chat Handoff

Last updated: 2026-08-07 17:54 UTC

Read this first in any new AI chat before proposing BotA changes.

## Current grounded answer

BotA is not failing because it cannot generate BUY/SELL directions. The current problem has three separate layers:

1. strategy throughput is low because score and H1 gates reject most tradeable candidates;
2. delivery policy suppresses additional strategy-accepted candidates;
3. recent delivered M15 signal quality is poor, so simply sending more signals is not a valid repair.

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

The dominant strategy suppressors are score and H1-neutral protection.

## Accepted -> Telegram funnel

Retained logs classify 106 strategy-accepted events:

```text
61 sent
38 cooldown-suppressed
6 Telegram score-gated
1 send failure
0 tier-gated
0 delivery-deduped
```

Four accepted CSV rows have no matched retained log event.

Telegram transport works. The delivery layer is not the only reason for low signal count.

## Cooldown audit — 2026-08-07 17:54 UTC

The 38 cooldown-suppressed accepted events were compared with the previous successful send for the same pair/timeframe:

```text
EXACT_DUPLICATE=0
NOT_EXACT_DUPLICATE=38
DIRECTION_CHANGED=0
SCORE_IMPROVED_5PLUS=7
ENTRY_CHANGED_3PLUS_PIPS=26
```

All 38 were same-direction updates. Therefore the previous shorthand `38 distinct signals` is too strong. The cooldown is coarse because it ignores score/entry/SL/TP and runs before exact content dedup, but it is also clearly suppressing repeated same-direction alert updates. Do not remove it blindly.

## Signal quality cross-check — highest priority

Read-only Supabase outcome data for historical BotA M15 rows with rationale `BotA score=`:

```text
score <70:   n=6,  wins=1, losses=5, cancelled=0, total_pips=-45.50
score 70-74: n=3,  wins=2, losses=1, cancelled=0, total_pips=+59.60
score 75-84: n=33, wins=12, losses=17, cancelled=4, total_pips=+56.10
score 85+:   n=16, wins=4, losses=10, cancelled=2, total_pips=+25.10
```

The `<70` sample is small but poor, so lowering Telegram's score floor from 70 is not currently supported.

More important, signals created since 2026-06-01 are:

```text
TOTAL=13
WINS=3
LOSSES=9
CANCELLED=1
TOTAL_PIPS=-71.40
```

Recent score buckets:

```text
75-84: n=11, wins=3, losses=7, cancelled=1, total_pips=-36.40
85+:   n=2, wins=0, losses=2, total_pips=-35.00
```

This means high BotA score has not protected recent delivered signals from poor results. Before increasing frequency, identify which score component or market regime is producing false confidence.

## Closed/non-dominant causes

- zero entry/SL/TP: HOLD-only symptom;
- `macro6=3`: neutral;
- RR text: advisory;
- H4+D1: only four tradeable rejects;
- Telegram transport: 61 successful retained sends versus one failure;
- cooldown: coarse, but no direction-reversal suppression was observed in the 38-event sample.

## Runtime context

```text
manager_count=1
manager_pid=31140
owned=6/7
orphaned=1
running=7/7
duplicates=0
orphan=crond
```

Keep this separate from strategy-quality work unless watcher execution is actually interrupted.

## No-change rules

```text
FILTER_SCORE_CHANGED=NO
H1_THRESHOLD_CHANGED=NO
TELEGRAM_SCORE_CHANGED=NO
COOLDOWN_CHANGED=NO
PAIR_LIST_CHANGED=NO
PROVIDER_CHANGED=NO
SUPABASE_CHANGED=NO
```

Do not manufacture more signals while recent delivered signals are negative.

## Exactly one next proof

For delivered signals since 2026-06-01, extract and join the 25-column decision components:

```text
ema_comp
rsi_comp
macd_comp
adx_comp
adx_raw
rsi_raw
macd_hist_raw
h1_trend
tier
session
adx_regime
```

Compare them with verified Supabase outcomes and identify the component/regime common to recent losers. That is now the shortest path to a useful BotA rather than merely a noisy one.

## Working discipline

1. Inspect before changing.
2. Keep commands small and pager-proof.
3. Validate schemas before analysis.
4. Separate runtime, strategy, delivery, and outcome quality.
5. Date every material finding in UTC.
6. Full-file replacement only for approved mutations.
7. Branch -> complete content -> verified diff -> PR; never direct-main fallback.
