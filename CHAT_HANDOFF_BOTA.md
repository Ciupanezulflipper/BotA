# BotA Chat Handoff

Last updated: 2026-08-07 17:11 UTC

Read this first in any new AI chat before proposing BotA changes.

## Current question

Why does BotA produce very few user-visible trade signals despite a live watcher and many months of runtime work?

## Current grounded answer — 2026-08-07

The direction engine is not dead. The valid BUY/SELL funnel is now measured:

```text
VALID_ENTRY_ROWS=1495
BUY_SELL_VALID_ROWS=1427
BUY_SELL_ACCEPTED=110
BUY_SELL_REJECTED=1317
BUY_SELL_ACCEPTANCE_RATE=7.71%
BUY_SELL_REJECTION_RATE=92.29%
```

Exact rejected-stage decomposition:

```text
SCORE_GATE=903       68.56% of rejected valid BUY/SELL
H1_NEUTRAL=410       31.13%
H4_D1_OPPOSE=4        0.30%
TOTAL=1317
```

Current source flow means these are sequential stages, not merely overlapping labels:

```text
1427 valid BUY/SELL
  -> 903 rejected by M15 score gate
  -> 524 survive score gate
  -> 410 rejected by H1-neutral veto
  -> 114 survive H1
  -> 4 rejected by H4+D1 opposition
  -> 110 accepted
```

The simple current explanation is therefore that score gating and H1-neutral gating remove nearly all valid tradeable candidates before Telegram is considered.

## Direction and pair evidence

```text
BUY_ACCEPTED=61
BUY_REJECTED=407
SELL_ACCEPTED=49
SELL_REJECTED=910
```

Accepted by pair:

```text
EURUSD=56
GBPUSD=53
USDJPY=1
```

The engine demonstrably produces and accepts tradeable directions. The next unresolved question is why those 110 accepted rows did or did not become Telegram signals.

## Score evidence

Rejected valid BUY/SELL:

```text
<62=740
62-64.99=105
65-69.99=148
70-74.99=141
75+=183
```

Accepted valid BUY/SELL:

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

The corpus spans historical configuration changes because rejection strings include `score<62`, `score<65`, and `score<70`. Do not infer today's effective score threshold from historical aggregate data.

## H1 evidence

```text
H1_NEUTRAL: REJECTED=410 ACCEPTED=94
H1_CONFIRMED: REJECTED=0 ACCEPTED=16
H1_OPPOSITE: REJECTED=0 ACCEPTED=0
```

The H1-neutral string match includes `H1_trend_neutral_overridden`; historical rows span different settings. Do not claim all 94 accepted neutral matches were raw neutral passes without exact filter-string proof.

The older May rejected-shadow evidence remains valid: a small sample of H1-blocked candidates later hit SL. That is still a reason not to remove H1 protection blindly. The new whole-corpus data, however, proves the current throughput split quantitatively.

## Macro and RR interpretation

`macro6=3` occurs in every rejected and accepted valid BUY/SELL row in the current corpus. Current fusion code treats macro6=3 as neutral and applies zero news score adjustment. It is not a hard rejection cause.

RR text occurs in some rows but current `quality_filter.py` treats RR as advisory unless another hard gate rejects the row. Do not tune RR based on these counts.

## Zero-entry hypothesis closed

All-zero entry/SL/TP rows were HOLD score-0 rows. No BUY/SELL row had zero entry/SL/TP.

```text
ZERO_ENTRY_BUY_SELL_ROWS=0
ZERO_ENTRY_ROOT_CAUSE=NO
```

Do not trace zero entry further unless new evidence contradicts this.

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

The current watcher appends newer 25-column rows under the old header. The first 13 positions still align, so the current funnel audit is valid. Newer ledger code that expects `filter_rejected`/`filter_reasons` header names may misclassify rows. This is a reporting/observability defect, not evidence that signal decisions themselves are broken.

## Telegram remains unproven

After strategy acceptance, current watcher code still applies:

```text
TELEGRAM_MIN_SCORE
TELEGRAM_TIER_YELLOW_MIN
TELEGRAM_COOLDOWN_SECONDS
delivery dedup
Telegram send
```

The 110 accepted rows are not proof of 110 Telegram deliveries.

## Current runtime context

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

The watcher was live and recording decisions. Keep runtime ownership work separate from strategy/delivery diagnosis unless it actually interrupts the watcher.

## No-change rules

```text
STRATEGY_CHANGED=NO
FILTER_SCORE_CHANGED=NO
H1_THRESHOLD_CHANGED=NO
H4_D1_CHANGED=NO
MACRO_CHANGED=NO
RR_CHANGED=NO
TELEGRAM_ELIGIBILITY_CHANGED=NO
DEDUP_CHANGED=NO
PROVIDER_CHANGED=NO
SUPABASE_CHANGED=NO
```

## Next exact proof

Read only the current phone values for score, H1 override, Telegram score/tier, cooldown, dry-run, and Telegram enabled state. Then inspect retained watcher logs and classify accepted rows into:

```text
telegram score gate
tier gate
cooldown
delivery dedup
sent
send failed
```

Only after that should any code or threshold change be proposed.

## Working discipline

1. Inspect before changing.
2. Keep commands small and pager-proof.
3. Validate schemas before analyzing fields.
4. Separate strategy acceptance from Telegram delivery and runtime health.
5. Record every material finding with explicit UTC date.
6. Full-file replacement only for approved code mutations.
7. Never lower thresholds merely to force signal volume.
