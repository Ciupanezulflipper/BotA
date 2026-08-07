# BotA Current Continuity State

Last updated: 2026-08-07 17:01 UTC

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

The current control-plane defect remains real, but it is not sufficient to
explain the signal drought because all seven required services are running and
the watcher is actively recording decisions.

## Signal funnel — verified 2026-08-07

Source:

```text
logs/alerts.csv
```

Verified CSV schema:

```text
timestamp,pair,tf,direction,score,confidence,entry,sl,tp,provider,rejected,filter_str,reasons
```

Decision corpus:

```text
TOTAL_ROWS=2507
HOLD=1082
SELL=959
BUY=466
ACCEPTED=110
REJECTED=2397
ACCEPTANCE_RATE≈4.39%
REJECTION_RATE≈95.61%
```

This proves the direction engine produces BUY and SELL decisions. The current
highest-value bottleneck is downstream filtering/eligibility, not absence of
raw trade directions.

Frequent filter strings include score thresholds (`score<62`, `score<65`,
`score<70`), `direction_not_tradeable`, H1 neutral tags, RR text, and
`macro6=3`. `H4_D1_oppose` was rare in the inspected corpus.

## Zero entry / SL / TP classification

A direct read-only pass over all 2507 rows found:

```text
ALL_VALID_ENTRY_SL_TP_ROWS=1493
ALL_ZERO_ENTRY_SL_TP_ROWS=1014
MIXED_ENTRY_SL_TP_ROWS=0
```

All 1014 zero rows were:

```text
DIRECTION=HOLD
SCORE=0.00
TIMEFRAME=M15
GBPUSD=519
EURUSD=490
USDJPY=5
ZERO_ENTRY_BUY_SELL_ROWS=0
```

Therefore:

```text
ZERO_ENTRY_VERDICT=HOLD_SYMPTOM_NOT_ROOT_CAUSE
```

Do not spend further time treating `entry=0` as the root defect unless new
BUY/SELL evidence contradicts this classification.

## Audit correction

One exploratory Python snippet attempted to read a non-existent
`filter_rejected` CSV key and therefore printed empty filter-status values. The
correct field is `rejected`. The earlier acceptance/rejection totals based on
CSV column 11 remain valid.

## Historical runtime incident — retained

Earlier on 2026-08-07 two `runsvdir` managers existed. PID 16360 (`runsvdir -P`)
owned the BotA supervisors while native Termux `service-daemon` manager PID
31140 owned none and its pidfile pointed to 31140. PID 16360 later died and the
native manager progressively reacquired supervisors. Exact executor attribution
for the native-manager start and detached-manager termination remains unproven.

Do not restart that broad provenance hunt unless it becomes necessary for
runtime safety.

## Scope lock

No strategy, threshold, H1/H4/D1, macro, RR, SL/TP, provider, Telegram,
Supabase, dedup, or service-topology mutation is authorized by the signal audit
alone.

The next strategy decision must be evidence-driven from the valid-entry funnel,
not from frustration with signal frequency.

## Evidence

- `audits/SIGNAL_FUNNEL_FORENSICS_2026-08-07.md`
- `AI_START_HERE.md`
- `CHAT_HANDOFF_BOTA.md`
- `audits/ERROR_LOG.md`
- `ERRORS.md`
- open PR #46 for duplicate-manager provenance work
- historical deployment/heartbeat records dated 2026-08-01 through 2026-08-03

## Exactly one next action

Classify the 1493 valid-entry rows by `rejected`, pair, direction, score bucket,
and exact `filter_str`, then inspect the 110 accepted rows for Telegram
eligibility/delivery. Do not change code before that evidence is complete.
