# BotA Errors and Silent-Failure Register

Last updated: 2026-08-07 17:11 UTC

Purpose: preserve verified failure classes, current open risks, and prevention rules without repeating broad audits.

Current signal evidence:

- `audits/SIGNAL_FUNNEL_STAGE_COUNTS_2026-08-07.md`
- `audits/SIGNAL_FUNNEL_FORENSICS_2026-08-07.md`
- `CONTINUITY_CURRENT.md`
- `CHAT_HANDOFF_BOTA.md`
- `audits/ERROR_LOG.md`

## Current verdict — 2026-08-07

```text
PRODUCTION_VALIDATION=FAILED_HISTORICAL
CURRENT_NATIVE_MANAGER_PID=31140
CURRENT_CONTROL_PLANE=DEGRADED_6_OWNED_1_ORPHAN
CURRENT_REQUIRED_RUNNING=7_OF_7
LIVE_WATCHER=RUNNING
VALID_ENTRY_ROWS=1495
BUY_SELL_VALID_ROWS=1427
BUY_SELL_ACCEPTED=110
BUY_SELL_REJECTED=1317
BUY_SELL_REJECTION_RATE=92.29_PERCENT
REJECTED_SCORE_GATE=903
REJECTED_H1_NEUTRAL=410
REJECTED_H4_D1_OPPOSE=4
ZERO_ENTRY_ROOT_CAUSE=NO
TELEGRAM_DELIVERY_OF_ACCEPTED=UNPROVEN
STRATEGY_MUTATION_ALLOWED=NO_PENDING_CURRENT_THRESHOLD_AND_DELIVERY_PROOF
AUTOMATIC_RECOVERY_REENABLE_ALLOWED=NO
```

## Current signal-throughput finding

The direction engine is not dead. The 1427 valid BUY/SELL rows decompose as:

```text
1427 valid BUY/SELL
  -> 903 rejected by M15 score gate
  -> 524 survive M15 score gate
  -> 410 rejected by H1-neutral veto
  -> 114 survive H1
  -> 4 rejected by H4+D1 opposition
  -> 110 accepted
```

The dominant strategy bottlenecks are therefore score gating and H1-neutral gating. H4/D1 opposition is negligible in the current corpus.

## Score history warning

The corpus contains `score<62`, `score<65`, and `score<70`, proving historical threshold changes. Aggregate history must not be used to infer the current phone threshold. Read current configuration/environment before mutation.

## Macro and RR interpretation

`macro6=3` appears in every accepted and rejected valid BUY/SELL row in the inspected corpus. Current fusion code treats macro6=3 as neutral and applies zero score adjustment. It is not the hard reject.

RR strings are advisory in current `quality_filter.py`; they co-occur with score/H1 gates and are not the primary rejection cause here.

## Closed hypothesis — zero entry caused lost tradeable signals

```text
ZERO_ENTRY_BUY_SELL_ROWS=0
ZERO_ENTRY_ROOT_CAUSE=NO
```

All zero-entry/SL/TP rows were HOLD score-0 rows. Do not trace zero entry further unless new BUY/SELL evidence contradicts this.

## CSV schema drift — open observability defect

Observed on 2026-08-07:

```text
HEADER_COLUMNS=13
ROWS_WITH_25_COLUMNS=2509
```

Legacy header:

```text
timestamp,pair,tf,direction,score,confidence,entry,sl,tp,provider,rejected,filter_str,reasons
```

Current watcher appends a newer 25-column format without migrating the existing header. The first 13 positions remain aligned, preserving the current funnel audit. Newer consumers that expect `filter_rejected` and `filter_reasons` by header name can misclassify rows. Treat this as an observability/reporting defect, separate from signal strategy and Telegram delivery.

## Telegram delivery remains a separate failure domain

The 110 accepted rows must still pass:

```text
TELEGRAM_MIN_SCORE
TELEGRAM_TIER_YELLOW_MIN
TELEGRAM_COOLDOWN_SECONDS
delivery dedup
Telegram transport
```

Accepted strategy rows are not equivalent to user-visible signals.

## Runtime ownership incident — 2026-08-07

Earlier two managers existed. Native Termux manager PID 31140 remains and its pidfile matches. Latest observed topology is six manager-owned required supervisors and one PID-1 orphan (`crond`), with all seven required services running and no duplicate rows.

Exact executor attribution for the manager-start and detached-manager termination remains unproven. Keep this separate from the signal-throughput proof unless runtime safety requires action.

## Historical failure classes retained

- duplicate execution ownership between cron/runit/boot paths;
- manager death with PID-1 orphan supervisors;
- canonical documentation lagging phone truth;
- strict shell mode terminating interactive Termux;
- recursive scans entering runit FIFOs;
- expected zero matches aborting under `pipefail`;
- wall-clock/monotonic confusion;
- inaccessible `/proc/uptime` on this Android build;
- service presence mistaken for useful progress;
- D1 timeframe mismatch;
- active service path assumed to equal repository path;
- broad runtime work obscuring the signal-throughput goal;
- oversized terminal packages causing pager/output loss;
- ad-hoc CSV analysis using the wrong field name.

## Runtime and signal lessons

- Runtime health and signal effectiveness are separate acceptance gates.
- A BUY/SELL direction is not an accepted signal.
- An accepted strategy row is not a delivered Telegram signal.
- Filter reason text may contain informational/advisory tags; presence alone does not prove causal rejection.
- Historical threshold strings do not prove current effective threshold values.
- Validate CSV schemas before field-based analysis.
- Keep runtime, strategy, Telegram, dedup, provider, and persistence failures distinct.

## Operational rules

- Small pager-proof evidence packages only.
- Validate schemas before analysis.
- Preserve phone state before mutation.
- One evidence domain and one acceptance gate per package.
- Complete-file replacement only for approved code mutation.
- Define rollback before mutation.
- Record explicit UTC date after every material finding.
- Never push directly to `main`; use branch -> content -> diff -> PR.

## Exactly one next investigation

Read current phone score/H1/Telegram threshold values and classify retained accepted-row delivery outcomes. No strategy or Telegram mutation until that proof is complete.
