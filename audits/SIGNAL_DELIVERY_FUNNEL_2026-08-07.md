# BotA Accepted-to-Telegram Funnel — 2026-08-07

Recorded threshold/delivery evidence: 2026-08-07 17:38:40 UTC
Recorded cooldown quality evidence: 2026-08-07 17:54:16 UTC
Supabase outcome cross-check: 2026-08-07 UTC

Purpose: preserve the current effective phone configuration, retained accepted-to-Telegram outcomes, cooldown semantics, and outcome evidence needed before changing signal-volume policy.

## Current effective phone settings

```text
PAIRS=EURUSD GBPUSD
TIMEFRAMES=M15
FILTER_SCORE_MIN=65
FILTER_SCORE_MIN_ALL=65
FILTER_SCORE_MIN_M15=<unset>
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

Only EURUSD and GBPUSD are live.

## Strategy funnel

```text
1427 valid BUY/SELL
  -> 903 rejected by M15 score gate
  -> 524 survive M15 score gate
  -> 410 rejected by H1-neutral veto
  -> 114 survive H1
  -> 4 rejected by H4+D1 opposition
  -> 110 strategy-accepted
```

## Retained accepted -> Telegram outcomes

Source: `logs/cron.signals.log`.

```text
ACCEPTED_EVENTS_PARSED=106
telegram_score_gate=6
telegram_tier_gate=0
telegram_cooldown=38
delivery_dedup=0
dry_run_or_disabled=0
telegram_sent=61
telegram_backoff=0
telegram_failed=1
accepted_no_terminal_evidence=0
```

Thus:

```text
61 sent               57.55%
38 cooldown           35.85%
6 Telegram score gate  5.66%
1 send failure         0.94%
```

The CSV contains 110 accepted BUY/SELL rows; four have no matched retained log evidence and remain delivery-unknown.

## Current watcher gate order

Current source confirms:

```text
strategy acceptance
 -> TELEGRAM_MIN_SCORE
 -> tier floor
 -> telegram_cooldown_check(pair, tf)
 -> exact content delivery dedup(pair, tf, direction, score, entry, sl, tp)
 -> Telegram send
 -> cooldown mark + content hash mark after successful real send
```

The cooldown key is pair/timeframe only. It does not include direction, score, entry, SL, or TP.

## Cooldown suppression quality audit

The 38 cooldown-suppressed accepted rows were joined to `alerts.csv` and compared with the previous successful send for the same pair/timeframe:

```text
COOLDOWN_TOTAL=38
EXACT_DUPLICATE=0
NOT_EXACT_DUPLICATE=38
DIRECTION_CHANGED=0
SCORE_IMPROVED_5PLUS=7
ENTRY_CHANGED_3PLUS_PIPS=26
COOLDOWN_UNMATCHED_CSV=0
NO_PREVIOUS_SENT_MATCH=0
```

Correct interpretation:

- the cooldown is not acting as exact content dedup;
- all 38 rows changed at least one signal field;
- none reversed direction;
- 26 moved entry by at least 3 pips and 7 improved score by at least 5 points;
- nevertheless, because every row stayed in the same direction, the evidence does not prove 38 independent new trade opportunities;
- removing the cooldown entirely could expose repeated same-direction updates every M15 cycle.

The cooldown may deserve semantic redesign, but the current evidence is not sufficient to delete it.

## Supabase outcome cross-check

Read-only query of `public.signals` for M15 rows with rationale starting `BotA score=`:

```text
score <70:   n=6,  wins=1, losses=5, cancelled=0, total_pips=-45.50
score 70-74: n=3,  wins=2, losses=1, cancelled=0, total_pips=+59.60
score 75-84: n=33, wins=12, losses=17, cancelled=4, total_pips=+56.10
score 85+:   n=16, wins=4, losses=10, cancelled=2, total_pips=+25.10
```

The historical `<70` sample is small but strongly negative. This is direct evidence against lowering `TELEGRAM_MIN_SCORE=70` merely to surface the six strategy-accepted 65-69.99 events.

## Recent delivered quality since 2026-06-01

```text
TOTAL=13
WINS=3
LOSSES=9
CANCELLED=1
TOTAL_PIPS=-71.40
```

By score:

```text
75-84: n=11, wins=3, losses=7, cancelled=1, total_pips=-36.40
85+:   n=2, wins=0, losses=2, cancelled=0, total_pips=-35.00
```

This changes the investigation priority. Recent accepted/delivered quality is poor even at high score. The first objective is no longer simply to increase message count; it is to determine why the score is overconfident in losing recent setups.

## Current conclusions

1. Direction generation works.
2. Score and H1 gates cause most strategy rejection.
3. Telegram transport works.
4. The Telegram score floor of 70 has negative-outcome counter-evidence against lowering it.
5. The 30-minute cooldown is coarse but currently suppresses same-direction updates, not observed direction reversals.
6. Only two live pairs are configured.
7. Recent delivered M15 performance is negative; increasing frequency without fixing edge would be harmful.

## Next exact proof

Join delivered M15 events since 2026-06-01 to their 25-column alert rows and compare the following fields with verified Supabase outcomes:

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

Identify which component or regime is common to recent losing high-score signals before changing thresholds, cooldown, or pair count.

## Safety

```text
RECORDED_DATE=2026-08-07
PHONE_RUNTIME_MUTATION=NO
PHONE_GIT_MUTATION=NO
PROVIDER_CALL_FROM_PHONE=NO
TELEGRAM_SEND=NO
SUPABASE_MUTATION=NO
STRATEGY_CHANGED=NO
```
