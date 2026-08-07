# BotA Runtime Error Log

Last updated: 2026-08-07 17:54 UTC

This is the canonical compact error and prevention index. Historical full text remains in Git history, `ERRORS.md`, dated audit records, and GitHub issue/PR history.

Current signal evidence:

- `audits/COOLDOWN_AND_SIGNAL_QUALITY_2026-08-07.md`
- `audits/SIGNAL_DELIVERY_FUNNEL_2026-08-07.md`
- `audits/SIGNAL_FUNNEL_STAGE_COUNTS_2026-08-07.md`
- `audits/SIGNAL_FUNNEL_FORENSICS_2026-08-07.md`
- `CONTINUITY_CURRENT.md`
- `CHAT_HANDOFF_BOTA.md`

## Current status — 2026-08-07

```text
PRODUCTION_VALIDATION=FAILED_HISTORICAL
CURRENT_NATIVE_MANAGER_PID=31140
CURRENT_CONTROL_PLANE=DEGRADED_6_OWNED_1_ORPHAN
CURRENT_REQUIRED_RUNNING=7_OF_7
LIVE_WATCHER=RUNNING
LIVE_PAIRS=EURUSD_GBPUSD_ONLY
FILTER_SCORE_MIN_ALL=65
H1_VETO_OVERRIDE_SCORE=75
TELEGRAM_MIN_SCORE=70
TELEGRAM_COOLDOWN_SECONDS=1800
BUY_SELL_VALID_ROWS=1427
BUY_SELL_ACCEPTED=110
BUY_SELL_REJECTED=1317
REJECTED_SCORE_GATE=903
REJECTED_H1_NEUTRAL=410
REJECTED_H4_D1_OPPOSE=4
TELEGRAM_SENT=61
TELEGRAM_COOLDOWN=38
TELEGRAM_SCORE_GATE=6
TELEGRAM_FAILED=1
COOLDOWN_EXACT_DUPLICATES=0
COOLDOWN_DIRECTION_REVERSALS=0
RECENT_DELIVERED_SINCE_2026_06_01=13
RECENT_WINS=3
RECENT_LOSSES=9
RECENT_CANCELLED=1
RECENT_TOTAL_PIPS=-71.40
STRATEGY_MUTATION_ALLOWED=NO_PENDING_COMPONENT_OUTCOME_AUDIT
```

## Canonical error index

### E001 — Scope branching
Repository, runtime, documentation, deployment, and strategy work were mixed.
Prevention: one phase, evidence domain, and acceptance gate per package.

### E003 — Duplicate execution sources
Cron, runit, boot files, and wrappers could own the same component.
Prevention: prove one execution source for every component.

### E004 — Dead manager with orphaned supervisors
A manager died while child `runsv` processes survived under PID 1.
Prevention: verify manager, parentage, ownership, and restart capability together.

### E007 — Recursive scan entered runit FIFOs
Prevention: whitelist regular files and exclude supervise directories.

### E009 — `pipefail` converted zero matches into abort
Prevention: explicitly tolerate expected zero matches.

### E012 — Deadman stale while services appeared running
Prevention: health must prove monotonic forward progress.

### E015 — Active wall-clock dependencies
Prevention: server UTC for market semantics; monotonic/boottime for cadence and health.

### E017 — Inaccessible `/proc/uptime`
Prevention: never depend on `/proc/uptime` on this device.

### E021 — Continuity lagged runtime truth
Prevention: update canonical docs with explicit UTC date after each material gate.

### E022 — Oversized package burdened Termux
Prevention: bounded, pager-proof packages and small direct proofs.

### E027 — Control-plane regression after prior closure
Prevention: ownership gate before deeper diagnosis.

### E031 — `supervise/pid` misidentified as `runsv`
Prevention: service PID -> PPID -> `runsv` -> manager chain.

### E032 — Manager existed while supervisors were orphans
Prevention: manager existence and service ownership are separate gates.

### E039 — Continuous guard associated with repeated Termux restarts
Prevention: no continuous recovery without executable-path proof, locking, backoff, kill switch, failure injection, and restart observation.

### E040 — D1 mismatch survived broad discovery
Status: CLOSED. `tf_minutes("D1")` now returns 1440 on the phone.

### E043 — Supervisor wrapper contradicted disabled-recovery policy
Status: CLOSED for that wrapper path.

### E045 — Strict shell mode left active in interactive Termux
Prevention: strict mode only inside a bounded child process.

### E046 — Active service path assumed to be repository path
Prevention: compare realpath, mode, and checksum before deployment.

### E047 — Runtime work obscured the signal-throughput acceptance criterion
Recorded: 2026-08-07.

```text
1427 valid BUY/SELL
903 rejected by M15 score gate
410 rejected by H1-neutral veto
4 rejected by H4+D1 opposition
110 strategy-accepted
```

Prevention: separate runtime health, raw directions, strategy filtering, delivery, and realized outcomes.

### E048 — Zero-entry symptom almost promoted to root cause
Recorded: 2026-08-07.

```text
all_zero_entry_sl_tp=1014
all_zero_rows_direction=HOLD
zero_entry_buy_sell_rows=0
```

Verdict: zero entry is a HOLD symptom, not the root cause of lost BUY/SELL signals.

### E049 — Ad-hoc CSV audit used the wrong field name
Recorded: 2026-08-07.

Legacy header uses `rejected` and `filter_str`; an exploratory script used `filter_rejected`.
Prevention: validate required headers and fail closed.

### E050 — Pager captured a large Git forensic command
Recorded: 2026-08-07.
Prevention: disable pagers and keep output bounded.

### E051 — Legacy alerts header with newer 25-column rows
Recorded: 2026-08-07.

```text
HEADER_COLUMNS=13
ROWS_WITH_25_COLUMNS=2509
```

Prevention: explicit schema/version migration or a versioned decision ledger.

### E052 — Documentation connector wrote a placeholder directly to main
Recorded: 2026-08-07.
Prevention: after branch-not-found, create/verify branch before any retry; never use `main` as fallback.

### E053 — Strategy acceptance and Telegram eligibility use different score floors
Recorded: 2026-08-07 17:38 UTC.

```text
FILTER_SCORE_MIN_ALL=65
TELEGRAM_MIN_SCORE=70
```

Six retained strategy-accepted events were blocked by Telegram score. Historical delivered `<70` BotA M15 rows later cross-checked as 1 win, 5 losses, total -45.50 pips, so lowering the Telegram floor is not supported by current evidence.

### E054 — Thirty-minute Telegram cooldown suppresses accepted events
Recorded: 2026-08-07 17:38 UTC.

```text
TELEGRAM_COOLDOWN_SECONDS=1800
TELEGRAM_COOLDOWN_EVENTS=38_OF_106_MATCHED_ACCEPTED
```

The cooldown is a major post-acceptance throughput gate.

### E055 — Live pair universe contains only two pairs
Recorded: 2026-08-07 17:38 UTC.

```text
PAIRS=EURUSD GBPUSD
TIMEFRAMES=M15
```

A third live pair is not currently scanned.

### E056 — Accepted CSV count exceeds matched retained delivery-log count
Recorded: 2026-08-07 17:38 UTC.

```text
CSV_ACCEPTED_BUY_SELL_TOTAL=110
MATCHED_ACCEPTED_LOG_EVENTS=106
UNMATCHED_ACCEPTED_ROWS=4
```

Keep four delivery outcomes UNKNOWN.

### E057 — Cooldown non-equality almost promoted to proof of new trades
Recorded: 2026-08-07 17:54 UTC.

Cooldown quality audit:

```text
COOLDOWN_TOTAL=38
EXACT_DUPLICATE=0
NOT_EXACT_DUPLICATE=38
DIRECTION_CHANGED=0
SCORE_IMPROVED_5PLUS=7
ENTRY_CHANGED_3PLUS_PIPS=26
```

The 38 rows are not exact field duplicates, but every one remained the same direction as the preceding sent signal. Therefore `38 independent new trades were blocked` is unproven.

Prevention: distinguish field-level change, same-opportunity update, and genuinely new trade intent. Lifecycle semantics are required before removing repeat-alert controls.

### E058 — Recent high scores do not imply recent positive edge
Recorded: 2026-08-07.

Read-only Supabase M15 BotA outcome cross-check for signals created since 2026-06-01:

```text
TOTAL=13
WINS=3
LOSSES=9
CANCELLED=1
TOTAL_PIPS=-71.40
75-84_TOTAL_PIPS=-36.40
85+_TOTAL_PIPS=-35.00
```

This is direct evidence that increasing signal volume is not sufficient. Recent accepted high-score signals are not demonstrating reliable edge.

Prevention: score calibration and regime/component outcome analysis must precede threshold loosening or pair expansion.

## Current exact funnel

Strategy:

```text
SCORE_GATE=903
H1_NEUTRAL=410
H4_D1_OPPOSE=4
TOTAL_REJECTED_VALID_BUY_SELL=1317
```

Delivery, matched accepted events:

```text
TELEGRAM_SENT=61
TELEGRAM_COOLDOWN=38
TELEGRAM_SCORE_GATE=6
TELEGRAM_FAILED=1
```

Outcome quality since 2026-06-01:

```text
13 delivered BotA M15
3 wins
9 losses
1 cancelled
-71.40 pips
```

## Current control-plane note

```text
manager_count=1
owned=6
orphaned=1
running=7
duplicates=0
orphan=crond
```

Keep runtime ownership separate from strategy-quality analysis unless watcher execution becomes impaired.

## Efficient protocol

1. Read dated current handoff/audits first.
2. One narrow evidence question per package.
3. Small pager-proof commands only.
4. Validate schemas before field analysis.
5. Separate runtime, strategy, delivery, and realized outcomes.
6. Preserve phone state before mutation.
7. Full-file replacement for approved mutation.
8. Date every material finding in UTC.
9. Branch -> verified diff -> PR; never direct-main fallback.

## Exactly one next action

Join recent delivered M15 signals to their 25-column decision components and compare those fields with Supabase outcomes. Identify which scoring component or market regime is associated with recent losing high-score signals before changing any threshold, cooldown, or pair universe.
