# BotA AI Start Here

Last updated: 2026-08-07 17:01 UTC

Read this before proposing BotA commands, code, cron, service, strategy,
notification, provider, Supabase, or deployment changes.

## Current authoritative truth

```text
RECORDED_DATE=2026-08-07
PHONE_BRANCH=deploy/repaired-core-20260802T215531Z
PHONE_HEAD=73b2306b5843f3396823ce815e96051abf78cf50
CURRENT_NATIVE_MANAGER_PID=31140
CURRENT_CONTROL_PLANE=DEGRADED_6_OWNED_1_ORPHAN
CURRENT_REQUIRED_RUNNING=7_OF_7
CURRENT_ORPHAN_SERVICE=crond
CURRENT_DUPLICATE_SERVICE_ROWS=0
LIVE_WATCHER=RUNNING
SIGNAL_DECISION_ROWS=2507
SIGNAL_HOLD_ROWS=1082
SIGNAL_SELL_ROWS=959
SIGNAL_BUY_ROWS=466
SIGNAL_ACCEPTED_ROWS=110
SIGNAL_REJECTED_ROWS=2397
SIGNAL_ACCEPTANCE_RATE≈4.39_PERCENT
SIGNAL_REJECTION_RATE≈95.61_PERCENT
ZERO_ENTRY_SL_TP_ROWS=1014
ZERO_ENTRY_BUY_SELL_ROWS=0
ZERO_ENTRY_VERDICT=HOLD_SYMPTOM_NOT_ROOT_CAUSE
STRATEGY_MUTATION_ALLOWED=NO_PENDING_FUNNEL_CLASSIFICATION
```

## Evidence order

1. `audits/SIGNAL_FUNNEL_FORENSICS_2026-08-07.md`
2. `CONTINUITY_CURRENT.md`
3. `CHAT_HANDOFF_BOTA.md`
4. `audits/DUPLICATE_MANAGER_FORENSICS_2026-08-07.md` when present/merged
5. `audits/P8_HEARTBEAT_PHONE_DEPLOYMENT_2026-08-03.md`
6. `audits/P7_SUPERVISOR_WRAPPER_CLOSURE_2026-08-02.md`
7. `audits/PHONE_DEPLOYMENT_2026-08-02.md`
8. `audits/INCIDENT_2026-08-01_VALIDATION_FAILURE.md`
9. `audits/ERROR_LOG.md`
10. `ERRORS.md`

## Current signal-throughput finding — 2026-08-07

The live watcher path was observed running:

```text
runsv bota-watcher
  -> tools/run_signal_watcher_with_ledger.sh
  -> tools/signal_watcher_pro.sh --once
```

The current `logs/alerts.csv` corpus contains 2507 decision rows:

```text
HOLD=1082
SELL=959
BUY=466
accepted=110
rejected=2397
```

This proves the direction engine can generate BUY and SELL decisions. The current
highest-value problem is downstream throughput: about 95.61% of recorded rows
are rejected.

Common filter strings contain score thresholds (`score<62`, `score<65`,
`score<70`), direction-not-tradeable, H1-neutral tags, RR advisory/rejection
text, and `macro6=3`. `H4_D1_oppose` is rare in the inspected corpus.

A separate direct classification proved that all 1014 rows with
`entry=0, sl=0, tp=0` are M15 HOLD rows with score 0.00. No BUY or SELL row had
zero entry/SL/TP. Therefore zero entry is a HOLD symptom, not the current root
cause.

The exact CSV schema is:

```text
timestamp,pair,tf,direction,score,confidence,entry,sl,tp,provider,rejected,filter_str,reasons
```

Do not use `filter_rejected` as a CSV field name in ad-hoc audits; it does not
exist in this file.

## Current runtime/control-plane finding — 2026-08-07

The native Termux `service-daemon` manager is PID 31140 and its pidfile matches.
Earlier in the incident there were two managers; the detached `-P` manager died
and supervisors progressively reconverged to PID 31140. The latest observed
state is:

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

Do not kill PID 31140 or manually kill the remaining orphan while signal-funnel
work is in progress. All required services are currently running.

## Scope lock

Do not change strategy thresholds, H1/H4/D1 behavior, macro filters, RR policy,
deduplication, SL/TP, provider semantics, Telegram eligibility, or Supabase
signal semantics until the current rejection funnel is classified precisely.

Do not resume broad manager-provenance archaeology unless the control-plane
condition directly interrupts watcher execution or creates duplicate service
rows.

Never push directly to `main`. Use branch -> complete content -> verified diff
-> PR.

## Evidence and time rules

- **VERIFIED** means current direct evidence proves the claim.
- **ASSUMED** means plausible but unproven.
- **UNKNOWN** means insufficient evidence and must not drive mutation.
- Trusted provider/server UTC controls market and candle semantics.
- Monotonic/boottime clocks control same-boot cadence and runtime health.
- Android/ship wall time is display-only for market decisions.
- Reject negative or future ages.
- Write and inspect complete decision evidence before dedup conclusions.
- Prefer small direct proofs over giant terminal dumps.

## Exactly one next action

Classify the 1493 rows with valid entry/SL/TP by `rejected`, pair, direction,
score bucket, and exact `filter_str`; separately inspect the 110 accepted rows
and determine whether they reached Telegram eligibility/delivery. Do not mutate
strategy or thresholds until that funnel is proven.
