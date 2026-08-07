# BotA June-July ADX/RSI Temporal Cross-Check

Recorded: 2026-08-07 18:46 UTC

Purpose: test the frozen March-derived ADX/RSI candidate rules against a later June-July 2026 production outcome set without changing BotA runtime or strategy.

## Source evidence

Read-only phone source:
- `logs/alerts.csv`

Read-only Supabase source:
- `public.signals`
- timeframe `M15`
- rationale prefix `BotA score=`
- date window June-July 2026

Supabase exact rows confirmed 13 published BotA signals in the period:

```text
TOTAL=13
WINS=3
LOSSES=9
CANCELLED=1
TOTAL_PIPS=-71.40
```

## Local component match coverage

The phone cross-check matched 9 of 13 published outcomes to accepted 25-column alert rows using pair, direction, date proximity, entry proximity, and score proximity.

```text
PUBLISHED=13
MATCHED=9
UNMATCHED=4
MATCH_RATE=69.2%
VERDICT=INSUFFICIENT_TEMPORAL_MATCH_COVERAGE
```

Unmatched published outcomes:

```text
2026-06-23 GBPUSD SELL score=79 entry=1.32179 WIN +33.1
2026-06-23 EURUSD SELL score=78 entry=1.13862 LOSS -13.3
2026-06-24 GBPUSD SELL score=77 entry=1.31448 LOSS -21.0
2026-06-26 EURUSD SELL score=75 entry=1.13892 CANCELLED 0.0
```

## Frozen policies

```text
A = current matched baseline
B = score >=70 AND ADX <30
C = score >=70 AND ADX <30 AND no extreme RSI
```

Extreme RSI definition used in the frozen test:
- BUY: RSI >=70
- SELL: RSI <=30

## Matched outcomes

```text
2026-06-09 EURUSD SELL LOSS -13.5 | score=80.7 | ADX=29.1 | RSI=38.7 | B=PASS  | C=PASS
2026-06-09 GBPUSD SELL LOSS -18.6 | score=75.7 | ADX=36.0 | RSI=38.0 | B=BLOCK | C=BLOCK
2026-06-17 EURUSD SELL LOSS -15.8 | score=85.2 | ADX=29.9 | RSI=17.2 | B=PASS  | C=BLOCK
2026-06-17 GBPUSD SELL LOSS -19.2 | score=87.5 | ADX=35.8 | RSI=21.2 | B=BLOCK | C=BLOCK
2026-06-22 EURUSD SELL WIN  +32.3 | score=77.6 | ADX=26.2 | RSI=37.9 | B=PASS  | C=PASS
2026-07-14 GBPUSD BUY  LOSS -25.9 | score=77.1 | ADX=40.6 | RSI=65.2 | B=BLOCK | C=BLOCK
2026-07-24 EURUSD SELL LOSS -11.1 | score=77.1 | ADX=26.4 | RSI=36.7 | B=PASS  | C=PASS
2026-07-27 EURUSD SELL WIN  +21.2 | score=77.9 | ADX=21.7 | RSI=35.0 | B=PASS  | C=PASS
2026-07-31 GBPUSD BUY  LOSS -19.6 | score=77.2 | ADX=38.0 | RSI=66.4 | B=BLOCK | C=BLOCK
```

## Frozen policy results on the 9 matched rows

```text
A_CURRENT_MATCHED_BASELINE: N=9 W=2 L=7 WR=22.2% PIPS=-70.2
B_SCORE70_ADX_LT30:        N=5 W=2 L=3 WR=40.0% PIPS=+13.1
C_SCORE70_ADX_LT30_NO_EXTREME: N=4 W=2 L=2 WR=50.0% PIPS=+28.9
```

ADX-only split:

```text
ADX_LT30:   N=5 W=2 L=3 WR=40.0% PIPS=+13.1
ADX_30_39:  N=3 W=0 L=3 WR=0.0%  PIPS=-57.4
ADX_40_PLUS:N=1 W=0 L=1 WR=0.0%  PIPS=-25.9
```

## Interpretation

The later-period matched subset points in the same direction as the March sample:
- matched ADX >=30 rows were 0W/4L and -83.3 pips;
- ADX <30 improved the matched subset from -70.2 pips to +13.1 pips;
- adding the frozen no-extreme-RSI condition improved the matched subset to +28.9 pips.

This is meaningful directional replication across a later period, but it is not yet sufficient production validation because only 9/13 published outcomes have matched local component rows.

The March result therefore moves from a single-window hypothesis to a cross-period hypothesis, but not yet to an approved production rule.

## Supabase timestamp caution

Exact Supabase `created_at` values were independently re-read on 2026-08-07. They do not align directly with the local watcher decision timestamps for several already-matched signals, so `created_at` must not be treated as the original decision timestamp without proving the publication-time semantics. Matching should continue to use signal identity fields rather than assuming timestamp equality.

## No-change decision

```text
ADX_SCORING_CHANGED=NO
RSI_SCORING_CHANGED=NO
FILTER_SCORE_CHANGED=NO
H1_THRESHOLD_CHANGED=NO
TELEGRAM_SCORE_CHANGED=NO
COOLDOWN_CHANGED=NO
PAIR_LIST_CHANGED=NO
PROVIDER_CHANGED=NO
SUPABASE_CHANGED=NO
```

## Next proof

Resolve the four unmatched June 23-26 published signals by inspecting the nearest local alert candidates without the current tight score/entry acceptance limits. If the four rows cannot be recovered from retained local data, record the retention gap and move to a true historical replay using raw candles and the live scoring path.
