# BotA Signal Funnel Stage Counts — 2026-08-07

Recorded: 2026-08-07 17:38:40 UTC

Purpose: preserve the exact valid-tradeable strategy funnel plus the current accepted-to-Telegram delivery funnel measured from the live Termux phone.

## Source and shape

Primary decision source: `logs/alerts.csv`.

Observed legacy header:

```text
timestamp,pair,tf,direction,score,confidence,entry,sl,tp,provider,rejected,filter_str,reasons
```

Observed row shape:

```text
HEADER_COLUMNS=13
ROWS_WITH_25_COLUMNS=2509
```

The current watcher appends a newer 25-column row format under the old 13-column header. The first 13 positions still align with the semantic fields used in this audit, so direction, score, entry/SL/TP, `rejected`, `filter_str`, and `reasons` remain classifiable. This schema drift is an observability defect and should be repaired separately.

## Current effective live settings

Verified at 2026-08-07 17:38:40 UTC:

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

The live watcher currently scans only EURUSD and GBPUSD. A third pair is not currently in scope.

## Valid tradeable strategy funnel

```text
VALID_ENTRY_ROWS=1495
BUY_SELL_VALID_ROWS=1427
BUY_SELL_ACCEPTED=110
BUY_SELL_REJECTED=1317
```

Acceptance among valid BUY/SELL rows:

```text
110 / 1427 = 7.71%
```

Rejection among valid BUY/SELL rows:

```text
1317 / 1427 = 92.29%
```

Direction split:

```text
BUY_ACCEPTED=61
BUY_REJECTED=407
SELL_ACCEPTED=49
SELL_REJECTED=910
```

Historical accepted by pair:

```text
EURUSD=56
GBPUSD=53
USDJPY=1
```

The one historical USDJPY row does not reflect current live scope; current `PAIRS` is only EURUSD GBPUSD.

## Exact rejected-stage decomposition

Rejected BUY/SELL rows classify cleanly into three terminal gate families:

```text
SCORE_GATE=903
H1_NEUTRAL=410
H4_D1_OPPOSE=4
TOTAL=1317
```

Percent of all rejected valid BUY/SELL rows:

```text
SCORE_GATE=68.56%
H1_NEUTRAL=31.13%
H4_D1_OPPOSE=0.30%
```

Current source flow makes this a meaningful sequential decomposition: `m15_h1_fusion.sh` returns immediately when the base M15 signal is already rejected, so score-gated M15 rows do not proceed into H1 fusion. Rows that pass the M15 filter can then be vetoed by H1, followed by the rare H4+D1 opposition veto.

Historical strategy funnel:

```text
1427 valid BUY/SELL
  -> 903 rejected by M15 score gate
  -> 524 survive M15 score gate
  -> 410 rejected by H1-neutral veto
  -> 114 survive H1 veto
  -> 4 rejected by H4+D1 opposition
  -> 110 strategy-accepted
```

## Exact filter strings among rejected BUY/SELL

```text
539 | score<65 | macro6=3
399 | macro6=3 | H1_trend_neutral
294 | score<70 | macro6=3
50  | score<62 | macro6=3
12  | score<70 | rr<1.80 | macro6=3
8   | score<70 | rr<1.66 | macro6=3
6   | rr<1.66 | macro6=3 | H1_trend_neutral
5   | rr<1.80 | macro6=3 | H1_trend_neutral
4   | macro6=3 | H4_D1_oppose
```

RR text is advisory in `quality_filter.py`; it co-occurs with score/H1 classifications and is not the hard-reject cause in these rows.

`macro6=3` appears in every rejected and every accepted valid BUY/SELL row in this corpus. Current `m15_h1_fusion.sh` treats macro6=3 as neutral and applies a zero score adjustment. Therefore `macro6=3` is not a hard-rejection cause here.

## Score distribution

Rejected valid BUY/SELL rows:

```text
<62=740
62-64.99=105
65-69.99=148
70-74.99=141
75+=183
```

Accepted valid BUY/SELL rows:

```text
<62=0
62-64.99=5
65-69.99=13
70-74.99=8
75+=84
```

Accepted score range:

```text
MIN=62.80
MEDIAN=80.05
MAX=98.60
```

The corpus spans historical configuration changes, proven by `score<62`, `score<65`, and `score<70` strings. Current phone configuration is now directly verified above; use current values for present-policy conclusions.

## Current H1 interpretation

Current values:

```text
H1_TREND_MIN_SCORE=40
H1_VETO_OVERRIDE_SCORE=75
H1_VETO_OVERRIDE_ADX=40
```

Current fusion behavior means a neutral-H1 M15 candidate below score 75 will generally be vetoed unless another code path changes classification; at score >=75, neutral H1 may be overridden when H4 is not opposing.

Historical tag counts:

```text
H1_NEUTRAL: REJECTED=410 ACCEPTED=94
H1_CONFIRMED: REJECTED=0 ACCEPTED=16
H1_OPPOSITE: REJECTED=0 ACCEPTED=0
```

The H1-neutral string match includes `H1_trend_neutral_overridden`, so accepted neutral-tag matches are not raw veto passes.

## Accepted -> Telegram delivery funnel

Delivery source: retained `logs/cron.signals.log`.

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
TELEGRAM_SENT=61       57.55%
TELEGRAM_COOLDOWN=38   35.85%
TELEGRAM_SCORE_GATE=6   5.66%
TELEGRAM_FAILED=1       0.94%
```

There were no parsed accepted events lost to tier gate, delivery dedup, dry-run/disabled mode, backoff, or missing terminal evidence.

The CSV contains 110 accepted BUY/SELL rows while the retained log parser matched 106 accepted events:

```text
CSV_ACCEPTED_BUY_SELL_TOTAL=110
MATCHED_ACCEPTED_LOG_EVENTS=106
UNMATCHED_ACCEPTED_ROWS=4
```

Those four remain delivery-unknown.

Relative to all 110 accepted CSV rows:

```text
KNOWN_SENT=61       55.45%
KNOWN_COOLDOWN=38   34.55%
KNOWN_SCORE_GATE=6   5.45%
KNOWN_FAILED=1       0.91%
UNMATCHED_LOG=4      3.64%
```

## Current layered policy implication

Current score floors are not identical:

```text
FILTER_SCORE_MIN_ALL=65
TELEGRAM_MIN_SCORE=70
TELEGRAM_TIER_YELLOW_MIN=70
TELEGRAM_TIER_GREEN_MIN=75
```

Therefore an H1-confirmed strategy-accepted signal with score 65.00-69.99 can still be suppressed by Telegram. Retained logs prove this happened six times among the 106 matched accepted events.

Current cooldown:

```text
TELEGRAM_COOLDOWN_SECONDS=1800
```

Thirty-eight of 106 matched accepted events were suppressed by this 30-minute pair/timeframe cooldown. That is a major post-acceptance throughput gate, but its trading quality effect is not yet proven.

## Full current interpretation

Low user-visible signal count is now explained as a layered funnel:

```text
RAW BUY/SELL CANDIDATES
  -> strategy M15 score floor
  -> H1-neutral veto / override logic
  -> rare H4+D1 opposition
  -> strategy accepted
  -> Telegram score floor
  -> 30-minute per-pair/timeframe cooldown
  -> delivery transport
```

Telegram transport is not the dominant failure: 61 retained accepted events were sent successfully and only one send failure was observed.

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

Before weakening protective strategy gates, classify historical outcomes for strategy-accepted candidates suppressed by the Telegram score gate or cooldown. Compare them with delivered-signal outcomes. If those suppressed candidates are acceptable, delivery-policy alignment is the least strategy-invasive route to increasing user-visible signals.