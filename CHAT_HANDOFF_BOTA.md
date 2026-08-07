# BotA Chat Handoff

Last updated: 2026-08-07 18:15 UTC

Read this first in any new AI chat before proposing BotA changes.

## Current grounded answer

BotA is not failing because it cannot generate BUY/SELL directions. The investigation has separated four layers:

1. strategy throughput is low because score and H1 gates reject most tradeable candidates;
2. delivery policy suppresses additional strategy-accepted candidates;
3. recent delivered M15 signal quality is poor, so sending more signals is not a valid repair;
4. historical component/outcome evidence now points to score calibration that may reward late/exhausted trend entries.

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

## March ledger x component audit — 2026-08-07 18:15 UTC

The 51 local March outcomes joined 100% to extended score-component rows:

```text
LEDGER_ROWS=51
JOINED=51
UNMATCHED=0
JOINED_WITH_COMPONENTS=51
WINS=13
LOSSES=38
TOTAL_PIPS=-264.1
```

Score bucket:

```text
<70:   WR=18.2% PIPS=-83.5
70-74: WR=50.0% PIPS=+2.1
75-84: WR=31.6% PIPS=-44.8
85+:   WR=17.6% PIPS=-137.9
```

The highest score bucket was the worst.

RSI entry state:

```text
EXTREME:   n=18 WR=11.1% PIPS=-229.2
STRETCHED: n=11 WR=45.5% PIPS=+69.4
MODERATE:  n=22 WR=27.3% PIPS=-104.3
```

ADX band:

```text
20-29: n=17 WR=52.9% PIPS=+98.0
30-39: n=26 WR=7.7%  PIPS=-319.1
40+:   n=8  WR=25.0% PIPS=-43.0
```

This is the strongest score-component evidence so far. Current scoring gives maximum ADX points at >=30 even though ADX 30-39 was the worst historical band in this sample. Current RSI scoring rewards greater distance from 50 even though extreme RSI was far worse than the intermediate stretched zone.

The evidence supports a non-linear entry-quality problem: stronger trend intensity does not necessarily mean a better M15 entry and may indicate late/exhausted entry timing.

## What is not proven

- Do not infer an exact new ADX threshold from only 17.5 hours of March data.
- Do not hard-reject every ADX >=30 yet.
- Do not change current H1 policy from this sample because all 51 March rows had H1 neutral.
- MACD saturation was not the dominant discriminator.
- Pair-specific changes are not supported; both EURUSD and GBPUSD were poor.

## Closed/non-dominant causes

- zero entry/SL/TP: HOLD-only symptom;
- `macro6=3`: neutral;
- RR text: advisory;
- H4+D1 opposition: rare;
- Telegram transport: functioning;
- cooldown: coarse but no direction-reversal suppression observed.

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

Run an offline/read-only counterfactual on the 51 joined March rows and the recent component-matched published outcomes. Compare minimal candidate changes such as penalizing extreme RSI, reducing/reversing the ADX bonus above 30, and combining both. Report retained signal count, win rate, and pips before any production mutation.

## Working discipline

1. Inspect before changing.
2. Keep commands small and pager-proof.
3. Validate schemas and time coverage before analysis.
4. Separate runtime, strategy, delivery, and realized outcome quality.
5. Date every material finding in UTC.
6. Full-file replacement only for approved mutations.
7. Branch -> complete content -> verified diff -> PR; never direct-main fallback.
