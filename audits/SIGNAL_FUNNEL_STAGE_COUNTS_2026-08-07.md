# BotA Signal Funnel Stage Counts — 2026-08-07

Recorded: 2026-08-07 17:11:13 UTC

Purpose: preserve the exact valid-tradeable funnel counts from the live Termux phone after correcting the CSV schema and closing the zero-entry hypothesis.

## Source and shape

Source: `logs/alerts.csv`.

Observed legacy header:

```text
timestamp,pair,tf,direction,score,confidence,entry,sl,tp,provider,rejected,filter_str,reasons
```

Observed row shape:

```text
HEADER_COLUMNS=13
ROWS_WITH_25_COLUMNS=2509
```

The current watcher appends a newer 25-column row format under the old 13-column header. The first 13 positions still align with the legacy semantic fields used in this audit, so direction, score, entry/SL/TP, `rejected`, `filter_str`, and `reasons` remain classifiable. This schema drift is an observability defect and should be repaired separately; it is not evidence that the watcher decision path itself is broken.

## Valid tradeable funnel

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

Accepted by pair:

```text
EURUSD=56
GBPUSD=53
USDJPY=1
```

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

The counts sum exactly to the 1317 rejected valid BUY/SELL rows.

Current source flow explains why this decomposition is meaningful: `m15_h1_fusion.sh` returns immediately when the base M15 signal is already rejected, so score-gated M15 rows do not proceed into H1 fusion. Rows that pass the M15 filter can then be vetoed by H1, followed by the rare H4+D1 opposition veto.

Therefore the live historical funnel is approximately:

```text
1427 valid BUY/SELL
  -> 903 rejected by M15 score gate
  -> 524 survive M15 score gate
  -> 410 rejected by H1-neutral veto
  -> 114 survive H1 veto
  -> 4 rejected by H4+D1 opposition
  -> 110 accepted
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

`macro6=3` appears in every rejected and every accepted valid BUY/SELL row in this corpus. Current `m15_h1_fusion.sh` appends `macro6=3` as a neutral tag and applies a score adjustment of zero for neutral macro. Therefore `macro6=3` is not a hard-rejection cause here.

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

The corpus spans historical configuration changes, proven by the presence of `score<62`, `score<65`, and `score<70` rejection strings. Do not infer the current effective threshold from the whole historical corpus. Current phone configuration/environment must be read directly before any strategy change.

## H1 interpretation

Tag counts:

```text
H1_NEUTRAL: REJECTED=410 ACCEPTED=94
H1_CONFIRMED: REJECTED=0 ACCEPTED=16
H1_OPPOSITE: REJECTED=0 ACCEPTED=0
```

The `H1_NEUTRAL` string match also catches historical `H1_trend_neutral_overridden` rows. Do not equate all 94 accepted matches with raw neutral vetoes without exact accepted-filter classification. The corpus spans multiple historical settings.

## Delivery remains unproven

The 110 accepted rows are strategy/filter survivors, not proof of Telegram delivery. Current watcher code still applies, in order:

```text
TELEGRAM_MIN_SCORE
TELEGRAM_TIER_YELLOW_MIN
TELEGRAM_COOLDOWN_SECONDS
delivery dedup
Telegram transport
```

The next proof must establish current effective thresholds and classify the 110 accepted rows against Telegram gate/delivery evidence before changing strategy.

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
