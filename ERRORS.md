# BotA Errors and Silent-Failure Register

Last updated: 2026-08-07 17:38 UTC

Purpose: preserve verified failure classes, current open risks, and prevention rules without repeating broad audits.

Current signal evidence:

- `audits/SIGNAL_DELIVERY_FUNNEL_2026-08-07.md`
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
LIVE_PAIRS=EURUSD_GBPUSD_ONLY
LIVE_TIMEFRAME=M15
FILTER_SCORE_MIN_ALL=65
H1_VETO_OVERRIDE_SCORE=75
TELEGRAM_MIN_SCORE=70
TELEGRAM_TIER_YELLOW_MIN=70
TELEGRAM_TIER_GREEN_MIN=75
TELEGRAM_COOLDOWN_SECONDS=1800
VALID_ENTRY_ROWS=1495
BUY_SELL_VALID_ROWS=1427
BUY_SELL_ACCEPTED=110
BUY_SELL_REJECTED=1317
REJECTED_SCORE_GATE=903
REJECTED_H1_NEUTRAL=410
REJECTED_H4_D1_OPPOSE=4
ACCEPTED_LOG_EVENTS_PARSED=106
TELEGRAM_SENT=61
TELEGRAM_COOLDOWN=38
TELEGRAM_SCORE_GATE=6
TELEGRAM_FAILED=1
ACCEPTED_LOG_UNMATCHED=4
ZERO_ENTRY_ROOT_CAUSE=NO
STRATEGY_MUTATION_ALLOWED=NO_PENDING_OUTCOME_PROOF
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
  -> 110 strategy-accepted
```

The dominant strategy bottlenecks are therefore score gating and H1-neutral gating. H4/D1 opposition is negligible in the current corpus.

## Current live configuration finding

Verified current phone values:

```text
PAIRS=EURUSD GBPUSD
TIMEFRAMES=M15
FILTER_SCORE_MIN=65
FILTER_SCORE_MIN_ALL=65
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

The bot currently scans only two live pairs. If a three-pair design is intended, that requirement is not satisfied by current configuration.

The score policy is also stacked. Strategy acceptance can occur at score >=65 when H1 confirms, while Telegram refuses accepted signals below 70. Neutral-H1 candidates generally require score >=75 plus non-opposing H4 context to override the veto.

## Accepted -> Telegram finding

Retained watcher logs classify 106 accepted events completely:

```text
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

The CSV contains 110 accepted BUY/SELL rows. Four have no matched retained watcher-log event in this audit and remain delivery-unknown.

Telegram transport itself is functioning and is not the dominant failure domain: 61 retained accepted events were sent and only one transport failure was observed.

## Closed/non-dominant hypotheses

### Zero entry

```text
ZERO_ENTRY_BUY_SELL_ROWS=0
ZERO_ENTRY_ROOT_CAUSE=NO
```

All zero-entry/SL/TP rows were HOLD score-0 rows.

### macro6=3

Neutral in current fusion code; present in accepted and rejected rows; not the hard reject.

### RR

Advisory in current `quality_filter.py`; not the dominant hard gate.

### H4+D1 opposition

Only four valid BUY/SELL rejections in the inspected corpus.

## CSV schema drift — open observability defect

Observed:

```text
HEADER_COLUMNS=13
ROWS_WITH_25_COLUMNS=2509
```

Legacy header:

```text
timestamp,pair,tf,direction,score,confidence,entry,sl,tp,provider,rejected,filter_str,reasons
```

Current watcher appends newer 25-column rows without migrating the old header. The first 13 positions remain aligned for the current audit, but newer named-field consumers can misclassify rows.

## Runtime ownership incident — 2026-08-07

Earlier two managers existed. Native Termux manager PID 31140 remains and its pidfile matches. Latest observed topology is six manager-owned required supervisors and one PID-1 orphan (`crond`), with all seven required services running and no duplicate rows.

Exact executor attribution remains unproven. Keep this separate from signal-throughput tuning unless runtime safety requires action.

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
- ad-hoc CSV analysis using the wrong field name;
- legacy 13-column CSV header with 25-column rows;
- connector direct-main fallback violation during documentation work.

## Runtime and signal lessons

- Runtime health and signal effectiveness are separate acceptance gates.
- A BUY/SELL direction is not an accepted signal.
- An accepted strategy row is not necessarily a delivered Telegram signal.
- A second downstream score floor can silently suppress a strategy-accepted trade.
- Long cooldowns can materially reduce user-visible signal count even when strategy throughput is unchanged.
- Pair-universe configuration can cap signal opportunity before strategy logic is considered.
- Filter reason text may contain informational/advisory tags; presence alone does not prove causal rejection.
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

Before weakening protective strategy gates, classify historical outcomes for strategy-accepted candidates suppressed only by Telegram score or the 30-minute cooldown. Compare them with delivered-signal outcomes. If those suppressed candidates perform acceptably, the least invasive throughput repair is in delivery policy rather than core strategy.