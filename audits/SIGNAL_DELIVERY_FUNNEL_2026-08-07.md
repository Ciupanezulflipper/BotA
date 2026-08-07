# BotA Accepted-to-Telegram Funnel — 2026-08-07

Recorded: 2026-08-07 17:38:40 UTC

Purpose: preserve the current effective phone configuration and the retained watcher-log outcomes after strategy acceptance.

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

Important implication: the live watcher currently scans only two pairs, EURUSD and GBPUSD. It cannot generate a live USDJPY signal under the current `PAIRS` setting. Historical USDJPY rows reflect older configuration.

Current score policy is layered:

```text
M15 strategy hard score floor = 65
H1-neutral override score = 75
Telegram score floor = 70
Yellow tier floor = 70
Green tier floor = 75
Cooldown = 1800 seconds = 30 minutes per pair/timeframe
```

Therefore a strategy-accepted H1-confirmed signal with score 65.00-69.99 can still be suppressed by Telegram even though strategy filtering accepted it. H1-neutral M15 candidates normally require score >=75 and non-opposing H4 context to override the neutral veto.

## Retained accepted -> Telegram outcomes

Source: `logs/cron.signals.log`.

```text
LOG_LINES=27332
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

The 106 parsed accepted events classify completely:

```text
61 sent              = 57.55%
38 cooldown          = 35.85%
6 Telegram score gate = 5.66%
1 send failure        = 0.94%
```

No parsed accepted event was lost to delivery dedup, tier gate, dry-run/disabled mode, or network backoff.

The CSV contains 110 accepted BUY/SELL rows while only 106 matching accepted events were parsed from the retained watcher log. Four accepted CSV rows therefore have no matched retained log evidence in this audit and must remain `DELIVERY_UNKNOWN`, not silently classified.

Relative to all 110 accepted CSV rows:

```text
KNOWN_SENT=61      55.45%
KNOWN_COOLDOWN=38  34.55%
KNOWN_SCORE_GATE=6  5.45%
KNOWN_FAILED=1      0.91%
UNMATCHED_LOG=4     3.64%
```

## Recent examples

Verified retained examples include:

```text
2026-06-03 GBPUSD score=68.80 -> Telegram score gate
2026-06-03 GBPUSD score=70.10 -> Telegram send failure
2026-06-09 EURUSD score=80.80 -> cooldown
2026-06-09 GBPUSD score=91.30 -> cooldown
2026-06-17 EURUSD score=68.00 -> Telegram score gate
2026-06-17 GBPUSD score=66.50 -> Telegram score gate
2026-06-17 EURUSD score=65.20 -> Telegram score gate
```

The retained log also proves many accepted signals were delivered successfully, including scores in the 70s, 80s, and 90s.

## Current full signal funnel interpretation

The historical valid-tradeable filter funnel remains:

```text
1427 valid BUY/SELL
  -> 903 rejected by M15 score gate
  -> 524 survive M15 score gate
  -> 410 rejected by H1-neutral veto
  -> 114 survive H1
  -> 4 rejected by H4+D1 opposition
  -> 110 strategy-accepted
```

The retained delivery evidence then shows, for 106 matched accepted events:

```text
106 matched accepted
  -> 6 blocked by Telegram score floor
  -> 38 blocked by 30-minute cooldown
  -> 1 Telegram transport failure
  -> 61 sent
```

The signal drought is therefore not one mysterious runtime failure. It is the cumulative result of layered strategy and delivery gates.

## Strongest current findings

1. The bot does generate BUY/SELL decisions.
2. The dominant strategy reject is the M15 score floor.
3. H1-neutral veto is the second dominant strategy reject.
4. H4+D1 opposition is negligible in this corpus.
5. `macro6=3` is neutral, not causal.
6. Zero entry is a HOLD symptom, not a BUY/SELL defect.
7. After strategy acceptance, a second score floor at 70 can suppress otherwise accepted 65-69.99 signals.
8. A 30-minute per-pair/timeframe cooldown suppresses a large fraction of retained accepted events.
9. The live watcher currently has only two configured pairs.
10. Telegram transport itself is not the dominant failure: 61 retained accepted events were sent and only one transport failure was observed.

## What is not yet proven

This audit does not prove that loosening the strategy score floor, H1-neutral veto, Telegram score floor, or cooldown would improve trading performance. Historical rejected-candidate outcome evidence must be used before changing protective strategy gates.

The four unmatched accepted CSV rows require a separate small proof if exact delivery classification is needed.

## Safety

```text
RECORDED_DATE=2026-08-07
RUNTIME_MUTATION_PERFORMED=NO
PRODUCTION_FILES_CHANGED=NO
SERVICE_ACTION_PERFORMED=NO
PROVIDER_CALL_PERFORMED=NO
TELEGRAM_CALL_PERFORMED=NO
PHONE_GIT_MUTATION_PERFORMED=NO
STRATEGY_CHANGED=NO
```

## Next exact proof

Before changing any threshold, classify historical outcomes for candidates blocked only by:

1. Telegram score gate 65-69.99 after strategy acceptance;
2. 30-minute cooldown;
3. H1-neutral veto;
4. M15 score floor near the current threshold.

Prioritize the least strategy-invasive repair first: eliminate redundant delivery suppression only if outcome evidence shows those already strategy-accepted signals are worth surfacing.