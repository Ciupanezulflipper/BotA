# BotA Chat Handoff

Last updated: 2026-08-07 17:38 UTC

Read this first in any new AI chat before proposing BotA changes.

## Current question

Why does BotA produce very few user-visible trade signals despite a live watcher and many months of runtime work?

## Current grounded answer — 2026-08-07

The bot does generate BUY/SELL decisions. The low user-visible throughput is caused by a layered funnel, not one mysterious runtime failure.

Historical valid-tradeable strategy funnel:

```text
1427 valid BUY/SELL
  -> 903 rejected by M15 score gate
  -> 524 survive M15 score gate
  -> 410 rejected by H1-neutral veto
  -> 114 survive H1
  -> 4 rejected by H4+D1 opposition
  -> 110 strategy-accepted
```

Rejected-stage percentages:

```text
M15 score gate=68.56%
H1 neutral=31.13%
H4+D1 opposition=0.30%
```

The strongest strategy bottlenecks are therefore the score floor and H1-neutral veto.

## Current live configuration — verified 2026-08-07 17:38 UTC

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

Important: the current watcher scans only EURUSD and GBPUSD. A third live pair is not configured.

Current layered policy:

```text
strategy score floor=65
H1-neutral override score=75
Telegram score floor=70
Telegram yellow floor=70
Telegram green floor=75
cooldown=30 minutes per pair/timeframe
```

A strategy-accepted H1-confirmed signal with score 65.00-69.99 can therefore be suppressed before Telegram delivery.

## Accepted -> Telegram evidence

Retained watcher log:

```text
ACCEPTED_EVENTS_PARSED=106
telegram_sent=61
telegram_cooldown=38
telegram_score_gate=6
telegram_failed=1
telegram_tier_gate=0
delivery_dedup=0
dry_run_or_disabled=0
telegram_backoff=0
accepted_no_terminal_evidence=0
```

Percent of parsed accepted events:

```text
sent=57.55%
cooldown=35.85%
Telegram score gate=5.66%
send failure=0.94%
```

The CSV contains 110 strategy-accepted BUY/SELL rows. Four have no matched retained watcher-log event in this audit and remain delivery-unknown.

Telegram transport itself is not the main problem: 61 retained accepted events were sent successfully and only one transport failure was observed. Post-acceptance suppression is dominated by the 30-minute cooldown, with a smaller second score gate at 70.

## Direction and pair evidence

Historical strategy-accepted split:

```text
BUY_ACCEPTED=61
SELL_ACCEPTED=49
EURUSD_ACCEPTED=56
GBPUSD_ACCEPTED=53
USDJPY_ACCEPTED=1
```

The historical USDJPY row reflects an older pair configuration. The current live `PAIRS` setting excludes USDJPY.

## Key non-causes now closed

### Zero entry

All zero entry/SL/TP rows in the audited corpus were HOLD score-0 rows. No BUY/SELL row had zero entry/SL/TP.

```text
ZERO_ENTRY_BUY_SELL_ROWS=0
ZERO_ENTRY_ROOT_CAUSE=NO
```

### macro6=3

`macro6=3` appears in accepted and rejected valid BUY/SELL rows. Current fusion code treats it as neutral and applies no score adjustment. It is not the hard rejection cause.

### RR text

RR strings are advisory in current `quality_filter.py`; they are not the dominant hard-reject cause.

### H4+D1

Only four valid BUY/SELL rows were rejected by H4+D1 opposition in this corpus. It is not the throughput bottleneck.

## CSV observability defect

Observed:

```text
HEADER_COLUMNS=13
ROWS_WITH_25_COLUMNS=2509
```

Legacy header:

```text
timestamp,pair,tf,direction,score,confidence,entry,sl,tp,provider,rejected,filter_str,reasons
```

The current watcher appends newer 25-column rows under the old header. The first 13 positions remain aligned for the current funnel audit, but newer named-field readers can misclassify rows. Treat this as a separate reporting/observability defect.

## Runtime context

Latest observed topology:

```text
manager_count=1
manager_pid=31140
owned=6/7
orphaned=1
running=7/7
duplicates=0
orphan=crond
```

The watcher was live and recording decisions. Keep runtime ownership work separate from signal-throughput work unless it actually interrupts the watcher.

## Practical interpretation

BotA currently has several stacked suppressors:

1. M15 score <65: strategy reject.
2. H1 neutral below override conditions: strategy reject.
3. H4+D1 opposition: rare strategy reject.
4. Strategy-accepted score <70: Telegram reject.
5. Same pair/timeframe within 30 minutes of a prior successful send: cooldown reject.
6. Only two live pairs are scanned.

This is substantially simpler than the previous broad infrastructure diagnosis.

## No-change rules until outcome proof

```text
STRATEGY_CHANGED=NO
FILTER_SCORE_CHANGED=NO
H1_THRESHOLD_CHANGED=NO
H4_D1_CHANGED=NO
PAIR_LIST_CHANGED=NO
TELEGRAM_SCORE_CHANGED=NO
COOLDOWN_CHANGED=NO
PROVIDER_CHANGED=NO
SUPABASE_CHANGED=NO
```

Do not remove protective H1 or score gates just to manufacture signal volume. First test whether already strategy-accepted signals suppressed only by Telegram score/cooldown were good or bad trades.

## Next exact proof

Classify historical outcomes of:

```text
strategy-accepted but Telegram-score-blocked signals
strategy-accepted but cooldown-blocked signals
```

Compare those outcomes with delivered signals. This is the least strategy-invasive place to look for a safe throughput improvement.

If a third pair is later required, treat that as a separate explicit pair-universe change after selecting and validating the pair.

## Working discipline

1. Inspect before changing.
2. Keep commands small and pager-proof.
3. Validate schemas before analyzing fields.
4. Separate strategy acceptance from Telegram delivery and runtime health.
5. Record every material finding with explicit UTC date.
6. Full-file replacement only for approved code mutations.
7. Never lower thresholds merely to force signal volume.
8. Use branch -> complete content -> verified diff -> PR; never direct-main fallback.