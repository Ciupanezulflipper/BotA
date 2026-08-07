# BotA Signal Funnel Forensics — 2026-08-07

Recorded: 2026-08-07 17:11:13 UTC

Purpose: preserve the verified signal-throughput findings from the live Termux phone and stop repeating broad runtime archaeology when the current question is where trade candidates are being rejected.

Detailed exact stage counts are also recorded in:

- `audits/SIGNAL_FUNNEL_STAGE_COUNTS_2026-08-07.md`

## Live watcher path observed

```text
runsv bota-watcher
  -> tools/run_signal_watcher_with_ledger.sh
  -> tools/signal_watcher_pro.sh --once
```

Latest observed control-plane context:

```text
manager_count=1
manager_pid=31140
required=7
owned=6
orphaned=1
running=7
duplicate_service_rows=0
healthy=false
orphan_service=crond
```

This ownership defect remains operationally real, but it does not explain the signal drought by itself because the watcher is live and recording decisions.

## Alerts corpus and schema drift

Source: `logs/alerts.csv`.

Observed:

```text
HEADER_COLUMNS=13
ROWS_WITH_25_COLUMNS=2509
```

Legacy header:

```text
timestamp,pair,tf,direction,score,confidence,entry,sl,tp,provider,rejected,filter_str,reasons
```

The current watcher appends a newer 25-column row format under the old 13-column header. The first 13 positions remain aligned with the semantic fields used in this audit. Therefore the current direction, score, entry/SL/TP, rejection, filter-string, and reason classifications are usable. The schema drift is a separate observability defect and may confuse newer readers that expect `filter_rejected`/`filter_reasons` as header names.

## Zero-entry hypothesis — closed

Prior direct classification proved:

```text
ALL_ZERO_ENTRY_SL_TP_ROWS=1014
MIXED_ENTRY_SL_TP_ROWS=0
ZERO_ROWS_DIRECTION=HOLD_ONLY
ZERO_ROWS_SCORE=0.00_ONLY
ZERO_ENTRY_BUY_SELL_ROWS=0
```

Verdict:

```text
ZERO_ENTRY_IS_HOLD_SYMPTOM_NOT_ROOT_CAUSE
```

Do not trace zero entry further as the primary signal defect unless new BUY/SELL evidence contradicts this.

## Exact valid-tradeable funnel

Current read-only classification:

```text
VALID_ENTRY_ROWS=1495
BUY_SELL_VALID_ROWS=1427
BUY_SELL_ACCEPTED=110
BUY_SELL_REJECTED=1317
```

Rates:

```text
BUY_SELL_ACCEPTANCE_RATE=7.71%
BUY_SELL_REJECTION_RATE=92.29%
```

Direction split:

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

## Exact rejected-stage decomposition

The 1317 rejected valid BUY/SELL rows divide exactly into:

```text
SCORE_GATE=903
H1_NEUTRAL=410
H4_D1_OPPOSE=4
TOTAL=1317
```

Percent of rejected valid BUY/SELL rows:

```text
SCORE_GATE=68.56%
H1_NEUTRAL=31.13%
H4_D1_OPPOSE=0.30%
```

Current `m15_h1_fusion.sh` source makes the sequential interpretation strong: if the base M15 payload is already filter-rejected, the script returns it before H1 fusion. Rows that survive M15 can then be H1-vetoed, and only H1 survivors reach the H4+D1 opposition check.

Observed funnel:

```text
1427 valid BUY/SELL
  -> 903 rejected by M15 score gate
  -> 524 survive M15 score gate
  -> 410 rejected by H1-neutral veto
  -> 114 survive H1
  -> 4 rejected by H4+D1 opposition
  -> 110 accepted
```

This is the strongest direct explanation currently available for low strategy throughput.

## Rejected BUY/SELL exact filter strings

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

## Macro interpretation

Tag counts show:

```text
MACRO6_NEUTRAL: REJECTED=1317 ACCEPTED=110
```

Current fusion code converts `macro6=3` to zero direction-aware news adjustment. The neutral tag is appended to `filter_reasons`, but it is not itself a hard rejection cause.

## RR interpretation

```text
RR_TEXT: REJECTED=31 ACCEPTED=1
```

Current `quality_filter.py` records RR problems as advisory unless another hard gate rejects the row. RR is not the primary rejection cause in this corpus.

## H1 interpretation

```text
H1_NEUTRAL: REJECTED=410 ACCEPTED=94
H1_CONFIRMED: REJECTED=0 ACCEPTED=16
H1_OPPOSITE: REJECTED=0 ACCEPTED=0
```

The H1-neutral substring also matches `H1_trend_neutral_overridden`. The corpus spans historical settings. Do not describe all 94 accepted neutral matches as raw neutral passes without exact accepted-filter classification.

## Score distribution

Rejected:

```text
<62=740
62-64.99=105
65-69.99=148
70-74.99=141
75+=183
```

Accepted:

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

The historical corpus spans different score thresholds (`score<62`, `score<65`, `score<70`). Therefore the next step must read current phone configuration/environment directly; aggregate history does not prove the current threshold.

## Delivery remains unproven

The 110 accepted rows are strategy/filter survivors, not proof of Telegram delivery. Current watcher source applies after acceptance:

```text
TELEGRAM_MIN_SCORE
TELEGRAM_TIER_YELLOW_MIN
TELEGRAM_COOLDOWN_SECONDS
delivery dedup
Telegram transport
```

The next direct proof is accepted -> Telegram classification plus current effective thresholds.

## Safety / mutation record

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
