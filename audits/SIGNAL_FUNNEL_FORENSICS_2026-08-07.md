# BotA Signal Funnel Forensics — 2026-08-07

Recorded: 2026-08-07 17:01:29 UTC

Purpose: preserve the verified signal-throughput findings from the live Termux phone and stop repeating broad runtime archaeology when the current question is where trade candidates are being rejected.

## Live watcher path observed

The live watcher process chain observed on 2026-08-07 was:

```text
runsv bota-watcher
  -> tools/run_signal_watcher_with_ledger.sh
  -> tools/signal_watcher_pro.sh --once
```

All seven required services were running at the time of the read-only discovery. The control plane was not fully reconciled: one native manager existed, six required supervisors were manager-owned, and `crond` remained a PID-1 orphan.

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

This control-plane condition is still an operational defect, but it does not explain the signal drought by itself because the watcher process was live and actively evaluating decisions.

## Signal decision corpus

Source:

```text
logs/alerts.csv
```

Rows excluding header:

```text
TOTAL_DECISION_ROWS=2507
```

Decision distribution:

```text
HOLD=1082
SELL=959
BUY=466
```

Verified conclusion: the signal engine is generating BUY and SELL directions. The primary problem is therefore not that the strategy engine is incapable of producing tradeable directions.

## Filter acceptance

Using the CSV `rejected` column:

```text
ACCEPTED=110
REJECTED=2397
ACCEPTANCE_RATE≈4.39%
REJECTION_RATE≈95.61%
```

This is the strongest current evidence that the signal-throughput bottleneck is in the downstream filtering/gating pipeline rather than the basic direction generator.

## Dominant filter strings

Most common `filter_str` values in the inspected corpus:

```text
794  direction_not_tradeable | score<65 | entry_invalid_zero | rr<=0 | macro6=3
537  score<65 | macro6=3
450  macro6=3 | H1_trend_neutral
294  score<70 | macro6=3
145  direction_not_tradeable | score<65 | entry_invalid_zero | rr<=0 | atr<=0 | macro6=3
50   score<62 | macro6=3
43   direction_not_tradeable | score<62 | rr<=0 | macro6=3
42   macro6=3 | H1_trend_neutral_overridden
33   direction_not_tradeable | score<70 | entry_invalid_zero | rr<=0 | macro6=3
21   direction_not_tradeable | score<65 | rr<=0 | macro6=3
20   direction_not_tradeable | score<70 | entry_invalid_zero | rr<=0 | atr<=0 | macro6=3
18   direction_not_tradeable | score<62 | entry_invalid_zero | rr<=0 | macro6=3
16   macro6=3 | H1_trend_confirmed
12   score<70 | rr<1.80 | macro6=3
8    score<70 | rr<1.66 | macro6=3
7    rr<1.66 | macro6=3 | H1_trend_neutral
5    rr<1.80 | macro6=3 | H1_trend_neutral
4    macro6=3 | H4_D1_oppose
```

Important interpretation:

- score thresholds appear in a very large portion of rejected rows;
- `macro6=3` appears very frequently but is not yet proven to be a hard rejection cause rather than an informational tag;
- `H4_D1_oppose` is rare in this corpus and is not the dominant throughput killer;
- H1 neutral appears frequently enough to remain relevant, but it is not yet proven to be the single dominant cause across all rejected rows because many rows fail earlier score/direction gates.

## Entry / SL / TP classification

A direct read-only classification of all 2507 rows found:

```text
ENTRY_SL_TP_ALL_VALID=1493
ENTRY_SL_TP_ALL_ZERO=1014
MIXED_ENTRY_SL_TP_ROWS=0
```

The 1014 all-zero rows were classified as:

```text
DIRECTION=HOLD for all 1014 rows
SCORE=0.00 for all 1014 rows
TIMEFRAME=M15 for all 1014 rows
GBPUSD=519
EURUSD=490
USDJPY=5
ZERO_ENTRY_BUY_SELL_ROWS=0
```

Therefore:

```text
VERDICT=ZERO_ENTRY_IS_HOLD_SYMPTOM_NOT_ROOT_CAUSE
```

`entry=0`, `sl=0`, and `tp=0` are not currently evidence of a broken level-generation stage because no BUY/SELL decision in this corpus had zero entry/SL/TP. The zero values are downstream characteristics of non-tradeable HOLD rows.

## Important audit-script correction

The live CSV schema was verified as:

```text
timestamp,pair,tf,direction,score,confidence,entry,sl,tp,provider,rejected,filter_str,reasons
```

A later exploratory Python snippet attempted to read a non-existent `filter_rejected` field and therefore printed empty filter-status values. Do not use that snippet's filter-status section as evidence. The earlier acceptance/rejection counts based on CSV column 11 (`rejected`) remain valid.

## Current working hypothesis

The current evidence supports this order of investigation:

1. classify the 1493 valid-entry rows by `rejected`, pair, direction, score bucket, and exact `filter_str`;
2. determine how many BUY/SELL rows are rejected only by score thresholds versus H1/MTF/RR gates;
3. determine whether `macro6=3` is causal or informational;
4. inspect the 110 accepted rows and prove whether they reached Telegram eligibility/delivery;
5. only then consider changing thresholds or strategy behavior.

No threshold, strategy, provider, Telegram, Supabase, or service mutation is justified by this audit alone.

## Safety / mutation record

```text
RECORDED_DATE=2026-08-07
RUNTIME_MUTATION_PERFORMED=NO
PRODUCTION_FILES_CHANGED=NO
SERVICE_ACTION_PERFORMED=NO
PROVIDER_CALL_PERFORMED=NO
TELEGRAM_CALL_PERFORMED=NO
PHONE_GIT_MUTATION_PERFORMED=NO
```
