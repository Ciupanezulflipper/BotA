# BotA Current Continuity State

Last updated: 2026-08-07 17:11 UTC

## Authoritative identifiers

```text
RECORDED_DATE=2026-08-07
PHONE_BRANCH=deploy/repaired-core-20260802T215531Z
PHONE_HEAD=73b2306b5843f3396823ce815e96051abf78cf50
CURRENT_NATIVE_MANAGER_PID=31140
CURRENT_SERVICE_DAEMON_PIDFILE=31140
```

## Current runtime state — 2026-08-07

Latest read-only control-plane observation:

```text
manager_count=1
manager_pid=31140
required=7
owned=6
running=7
orphaned=1
duplicate_service_rows=0
healthy=false
orphan_service=crond
```

The watcher is live and was observed through:

```text
runsv bota-watcher
  -> tools/run_signal_watcher_with_ledger.sh
  -> tools/signal_watcher_pro.sh --once
```

The ownership defect remains real but does not explain the current signal drought by itself because all seven required services are running and the watcher is actively recording decisions.

## Signal funnel — verified 2026-08-07

Source: `logs/alerts.csv`.

Observed file shape:

```text
HEADER_COLUMNS=13
ROWS_WITH_25_COLUMNS=2509
```

The header is the legacy 13-column schema:

```text
timestamp,pair,tf,direction,score,confidence,entry,sl,tp,provider,rejected,filter_str,reasons
```

Current watcher rows are 25 columns. The first 13 positions remain aligned with the fields used in the signal audit, so the tradeable funnel counts are valid. The mixed schema is a separate observability defect and may cause newer ledger readers that expect `filter_rejected`/`filter_reasons` column names to misclassify historical rows.

### Valid tradeable funnel

```text
VALID_ENTRY_ROWS=1495
BUY_SELL_VALID_ROWS=1427
BUY_SELL_ACCEPTED=110
BUY_SELL_REJECTED=1317
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

### Exact rejected-stage decomposition

The 1317 rejected valid BUY/SELL rows decompose exactly into:

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

Current source flow makes this decomposition meaningful. `m15_h1_fusion.sh` returns immediately when the M15 base signal is already filter-rejected, so score-gated M15 rows do not proceed to H1. The observed funnel is therefore:

```text
1427 valid BUY/SELL
  -> 903 rejected by M15 score gate
  -> 524 survive M15 score gate
  -> 410 rejected by H1-neutral veto
  -> 114 survive H1
  -> 4 rejected by H4+D1 opposition
  -> 110 accepted
```

This is now the strongest direct explanation of low strategy throughput.

## Macro and RR interpretation

`macro6=3` appears in all 1317 rejected and all 110 accepted valid BUY/SELL rows. Current fusion code treats macro6=3 as neutral and applies a zero news adjustment, so the tag itself is not a hard rejection cause.

RR text appears in 31 rejected rows and one accepted row. In current `quality_filter.py`, RR is advisory unless another hard gate rejects the row. Do not treat RR text as the primary cause of this corpus.

## Score history

Rejected valid BUY/SELL score buckets:

```text
<62=740
62-64.99=105
65-69.99=148
70-74.99=141
75+=183
```

Accepted valid BUY/SELL score buckets:

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

The corpus spans historical threshold changes, proven by `score<62`, `score<65`, and `score<70` strings. Do not infer the current effective phone threshold from the aggregate corpus. Read the current phone configuration/environment directly before any strategy mutation.

## Zero entry / SL / TP classification — closed hypothesis

Previous direct pass:

```text
ALL_ZERO_ENTRY_SL_TP_ROWS=1014
MIXED_ENTRY_SL_TP_ROWS=0
ZERO_ROWS_DIRECTION=HOLD_ONLY
ZERO_ROWS_SCORE=0.00_ONLY
ZERO_ENTRY_BUY_SELL_ROWS=0
```

Therefore:

```text
ZERO_ENTRY_VERDICT=HOLD_SYMPTOM_NOT_ROOT_CAUSE
```

Do not spend further time treating zero entry as the root defect unless new BUY/SELL evidence contradicts this classification.

## Telegram delivery remains unproven

The 110 accepted rows are filter survivors, not proof of user-visible signals. Current watcher code applies additional gates after acceptance:

```text
TELEGRAM_MIN_SCORE
TELEGRAM_TIER_YELLOW_MIN
TELEGRAM_COOLDOWN_SECONDS
delivery dedup
Telegram transport
```

The next proof must establish current effective threshold values and classify accepted rows against retained Telegram gate/send evidence.

## Historical runtime incident — retained

Earlier on 2026-08-07 two `runsvdir` managers existed. PID 16360 (`runsvdir -P`) owned the BotA supervisors while native Termux `service-daemon` manager PID 31140 initially owned none and its pidfile pointed to 31140. PID 16360 later died and the native manager progressively reacquired supervisors. Exact executor attribution remains unproven.

Do not restart broad provenance archaeology unless runtime safety requires it.

## Scope lock

No strategy threshold, H1/H4/D1, macro, RR, SL/TP, provider, Telegram, Supabase, dedup, or service-topology mutation is authorized yet.

The first potential strategy change must be based on current effective settings plus delivery evidence, not aggregate historical thresholds or frustration with signal frequency.

## Evidence

- `audits/SIGNAL_FUNNEL_FORENSICS_2026-08-07.md`
- `audits/SIGNAL_FUNNEL_STAGE_COUNTS_2026-08-07.md`
- `AI_START_HERE.md`
- `CHAT_HANDOFF_BOTA.md`
- `audits/ERROR_LOG.md`
- `ERRORS.md`
- historical runtime/deployment records dated 2026-08-01 through 2026-08-07

## Exactly one next action

Read only the current phone values for score/H1/Telegram thresholds and inspect retained watcher logs for accepted -> score/tier/cooldown/dedup/send outcomes. Do not change code or thresholds before that evidence is complete.
