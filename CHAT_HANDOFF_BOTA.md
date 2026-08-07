# BotA Chat Handoff

Last updated: 2026-08-07 18:09 UTC

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

## Accepted -> Telegram funnel

Retained logs classify 106 strategy-accepted events:

```text
61 sent
38 cooldown-suppressed
6 Telegram score-gated
1 send failure
```

Four accepted CSV rows have no matched retained log event.

## Cooldown audit — 2026-08-07 17:54 UTC

```text
EXACT_DUPLICATE=0
NOT_EXACT_DUPLICATE=38
DIRECTION_CHANGED=0
SCORE_IMPROVED_5PLUS=7
ENTRY_CHANGED_3PLUS_PIPS=26
```

All 38 were same-direction updates. The cooldown is coarse, but 38 independent new trades were not proven.

## Recent signal quality — highest priority

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

## Local ledger inventory — 2026-08-07 18:09 UTC

The phone has `data/ledger.csv`:

```text
LEDGER_ROWS=51
WIN=13
LOSS=38
WIN_RATE=25.49%
FIRST_TIMESTAMP=2026-03-09T21:45:07+02:00
LAST_TIMESTAMP=2026-03-10T15:15:07+02:00
```

This ledger is real but stale and narrow: only about 17.5 hours of March data. It cannot be treated as current strategy evidence. Its best use is an offline join to matching 25-column alert rows to test whether score components behaved differently on its 13 wins versus 38 losses.

## Scoring hypotheses under test

Current `scoring_engine.sh` gives RSI up to +15 points based on absolute distance from 50. Thus more oversold SELLs and more overbought BUYs can score higher even if entry quality is deteriorating. Current code also uses a 1.0 ATR pullback buffer despite a comment describing ±0.3 ATR. Neither is approved for mutation until outcome correlation is measured.

## Closed/non-dominant causes

- zero entry/SL/TP: HOLD-only symptom;
- `macro6=3`: neutral;
- RR text: advisory;
- H4+D1: only four tradeable rejects;
- Telegram transport: functioning;
- cooldown: coarse but no direction-reversal suppression observed.

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

Do not manufacture more signals while recent delivered quality is negative.

## Exactly one next proof

Join `data/ledger.csv` to `logs/alerts.csv` and report how many of the 51 March outcomes have extended score components. Then compare WIN versus LOSS by score bucket, RSI extremity, MACD saturation, ADX band, H1 state, pair, and direction. Keep March evidence separate from the recent June-August Supabase evidence.

## Working discipline

1. Inspect before changing.
2. Keep commands small and pager-proof.
3. Validate schemas before analysis.
4. Separate runtime, strategy, delivery, and outcome quality.
5. Date every material finding in UTC.
6. Full-file replacement only for approved mutations.
7. Branch -> complete content -> verified diff -> PR; never direct-main fallback.
