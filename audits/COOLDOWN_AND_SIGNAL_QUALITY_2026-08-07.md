# BotA Cooldown and Signal Quality Audit — 2026-08-07

Recorded phone evidence: 2026-08-07 17:54:16 UTC
Supabase cross-check recorded: 2026-08-07 UTC

Purpose: determine whether the 30-minute Telegram cooldown is suppressing true new trade opportunities or repeated same-direction updates, and cross-check delivered BotA signal quality before loosening any gate.

## Current live settings

```text
PAIRS=EURUSD GBPUSD
TIMEFRAMES=M15
FILTER_SCORE_MIN_ALL=65
H1_VETO_OVERRIDE_SCORE=75
TELEGRAM_MIN_SCORE=70
TELEGRAM_TIER_YELLOW_MIN=70
TELEGRAM_TIER_GREEN_MIN=75
TELEGRAM_COOLDOWN_SECONDS=1800
DRY_RUN_MODE=0
TELEGRAM_ENABLED=1
```

## Cooldown suppression quality audit

The 38 retained strategy-accepted events suppressed by cooldown were matched exactly back to `logs/alerts.csv` and compared with the last successfully sent event for the same pair/timeframe.

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

Important interpretation:

- all 38 suppressed rows were field-level different from the preceding sent row;
- none reversed direction;
- 26 moved entry by at least 3 pips;
- 7 improved score by at least 5 points;
- because all 38 remained the same direction, the phrase `38 distinct new trades` is NOT proven;
- the cooldown is a coarse repeat-alert suppressor, not an exact duplicate detector;
- current exact content dedup occurs later in the watcher and therefore never sees rows blocked by cooldown.

Verified current watcher order:

```text
strategy accepted
 -> TELEGRAM_MIN_SCORE
 -> tier floor
 -> pair/timeframe cooldown
 -> exact content delivery dedup
 -> Telegram send
 -> cooldown mark + delivery hash after successful real send
```

The cooldown key is pair + timeframe only. It does not include direction, score, entry, SL, or TP.

## Supabase cross-check: historical delivered BotA M15 outcomes

Project `ozgkeslgjqbqfewojnmr` was queried read-only. Only rows with `timeframe='M15'` and rationale beginning `BotA score=` were included, excluding unrelated seeded/demo rows.

Historical score buckets:

```text
score <70:  n=6   wins=1  losses=5  cancelled=0  total_pips=-45.50
score 70-74: n=3 wins=2  losses=1  cancelled=0  total_pips=+59.60
score 75-84: n=33 wins=12 losses=17 cancelled=4  total_pips=+56.10
score 85+:   n=16 wins=4  losses=10 cancelled=2  total_pips=+25.10
```

The `<70` historical sample is small but materially negative. This is direct counter-evidence against simply removing the Telegram score floor of 70.

## Recent delivered signal quality since 2026-06-01

Read-only Supabase query of BotA M15 rows created on or after 2026-06-01:

```text
TOTAL=13
WINS=3
LOSSES=9
CANCELLED=1
TOTAL_PIPS=-71.40
```

By score bucket:

```text
75-84: n=11, wins=3, losses=7, cancelled=1, total_pips=-36.40
85+:   n=2,  wins=0, losses=2, cancelled=0, total_pips=-35.00
```

This is the most important new finding. Recent delivered performance is poor even at high scores. Therefore low signal volume is not the only product problem, and increasing message count by weakening score/H1/cooldown protections is not justified yet.

## Current interpretation

The investigation has separated three questions:

1. **Runtime:** watcher and Telegram transport function.
2. **Throughput:** score and H1 gates reject most tradeable candidates; delivery gates suppress additional accepted rows.
3. **Edge/quality:** recent delivered M15 signals are negative in the current Supabase outcome sample.

The third question now has priority. A bot that sends more negative-expectancy signals is not repaired.

## What not to change yet

```text
FILTER_SCORE_MIN_ALL=KEEP_PENDING_COMPONENT_OUTCOME_AUDIT
H1_PROTECTION=KEEP_PENDING_COMPONENT_OUTCOME_AUDIT
TELEGRAM_MIN_SCORE=KEEP_70_PENDING_MORE_EVIDENCE
TELEGRAM_COOLDOWN_SECONDS=KEEP_1800_PENDING_SEMANTIC_REDESIGN
PAIR_LIST=KEEP_CURRENT_PENDING_THIRD_PAIR_VALIDATION
```

The cooldown may deserve redesign because it is coarse, but removing it entirely would likely expose repeated same-direction updates. The historical `<70` delivered sample argues against lowering the Telegram score floor merely to surface more signals.

## Exactly one next proof

For delivered M15 signals since 2026-06-01, join each sent event to the 25-column alert row and inspect:

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

Then compare those components against the verified Supabase outcomes. The goal is to identify why recent accepted high-score signals lost and whether one component/regime is systematically misleading the score.

## Safety

```text
RECORDED_DATE=2026-08-07
PHONE_RUNTIME_MUTATION=NO
PHONE_GIT_MUTATION=NO
PROVIDER_CALL_FROM_PHONE=NO
TELEGRAM_SEND=NO
SUPABASE_MUTATION=NO
GITHUB_CHANGE=DOCUMENTATION_ONLY
```
