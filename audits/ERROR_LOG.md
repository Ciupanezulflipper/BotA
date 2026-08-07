# BotA Runtime Error Log

Last updated: 2026-08-07 17:38 UTC

This is the canonical compact error and prevention index. Historical full text remains in Git history, `ERRORS.md`, dated audit records, and GitHub issue/PR history.

Current signal evidence:

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
TELEGRAM_TIER_YELLOW_MIN=70
TELEGRAM_TIER_GREEN_MIN=75
TELEGRAM_COOLDOWN_SECONDS=1800
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
A broad scan traversed `supervise` named pipes and hung.
Prevention: whitelist regular files and exclude supervise directories.

### E009 — `pipefail` converted zero matches into abort
Expected `pgrep`/`grep` zero results terminated packages.
Prevention: explicitly tolerate expected zero matches.

### E012 — Deadman stale while services appeared running
PID presence was mistaken for useful progress.
Prevention: health must prove monotonic forward progress.

### E015 — Active wall-clock dependencies
Cadence and health used Android/ship wall time.
Prevention: server UTC for market semantics; monotonic/boottime for cadence and health.

### E017 — Inaccessible `/proc/uptime`
Android denied access.
Prevention: never depend on `/proc/uptime` on this device.

### E021 — Continuity lagged runtime truth
Canonical files remained stale after material changes.
Prevention: update handoff/error/deployment records with an explicit UTC date after each gate.

### E022 — Oversized package burdened Termux
Too many evidence domains were combined and output exceeded practical terminal capture limits.
Prevention: bounded, pager-proof packages and smaller direct proofs.

### E027 — Control-plane regression after prior closure
One manager owned only part of the service set.
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
Status: CLOSED for that wrapper path. Later incidents still require exact ownership verification.

### E045 — Strict shell mode left active in interactive Termux
A direct `set -euo pipefail` in the parent shell caused Termux to exit after an expected failed assertion.
Prevention: strict mode only inside a bounded child process.

### E046 — Active service path assumed to be repository path
The active runit directory and repository copy could be separate physical files.
Prevention: compare realpath, mode, and checksum for both paths before deployment.

### E047 — Runtime work obscured the signal-throughput acceptance criterion
Recorded: 2026-08-07.

Current direct evidence:

```text
1427 valid BUY/SELL
903 rejected by M15 score gate
410 rejected by H1-neutral veto
4 rejected by H4+D1 opposition
110 strategy-accepted
```

Prevention: maintain separate acceptance gates for runtime health, raw direction generation, strategy filtering, Telegram eligibility, transport, and persistence.

### E048 — Zero-entry symptom almost promoted to root cause
Recorded: 2026-08-07.

```text
all_zero_entry_sl_tp=1014
all_zero_rows_direction=HOLD
all_zero_rows_score=0.00
zero_entry_buy_sell_rows=0
```

Verdict: zero entry is a HOLD symptom in this corpus, not the root cause of lost BUY/SELL signals.

### E049 — Ad-hoc CSV audit used the wrong field name
Recorded: 2026-08-07.

Legacy header uses `rejected` and `filter_str`. One exploratory script looked up `filter_rejected` and therefore produced empty filter-status values.

Prevention: print and validate required headers before analysis; fail if a required field is absent.

### E050 — Pager captured a large Git forensic command
Recorded: 2026-08-07.

A broad Git evidence package entered `less` and made the result impractical to capture.
Prevention: disable pagers and keep output bounded.

### E051 — Legacy alerts header with newer 25-column rows
Recorded: 2026-08-07.

```text
HEADER_COLUMNS=13
ROWS_WITH_25_COLUMNS=2509
```

The watcher appends a newer 25-column row layout under an existing 13-column legacy header. The first 13 positions align for the current audit, but newer named-field consumers can silently misclassify rows.

Prevention: explicit schema/version migration or a new versioned decision ledger.

### E052 — Documentation connector wrote a placeholder directly to main
Recorded: 2026-08-07.

A connector retry created a placeholder audit directly on `main` in commit `6cf8538dbc6bd64746cc3f32052291d5ebe27a0e` after a branch-not-found error. It was immediately corrected through PR #48.

Prevention: after any branch-not-found write error, stop and create/verify the branch before retrying. Never use `main` as a temporary fallback.

### E053 — Strategy acceptance and Telegram eligibility use different score floors
Recorded: 2026-08-07 17:38 UTC.

Verified current values:

```text
FILTER_SCORE_MIN_ALL=65
TELEGRAM_MIN_SCORE=70
TELEGRAM_TIER_YELLOW_MIN=70
```

Effect: a strategy-accepted H1-confirmed M15 signal with score 65.00-69.99 is still suppressed before Telegram. Retained watcher logs prove six accepted events were blocked by this second score gate.

This is not automatically a bug if intentional product policy, but it is a real throughput suppressor and must be treated separately from strategy rejection.

Prevention: document whether "strategy accepted" means "eligible for user alert." If yes, align the delivery floor with strategy acceptance or make the distinction explicit in the product state model.

### E054 — Thirty-minute Telegram cooldown suppresses accepted events
Recorded: 2026-08-07 17:38 UTC.

Verified current value:

```text
TELEGRAM_COOLDOWN_SECONDS=1800
```

Retained watcher-log classification:

```text
ACCEPTED_EVENTS_PARSED=106
TELEGRAM_COOLDOWN=38
```

Thus 35.85% of parsed strategy-accepted events were suppressed by cooldown. This does not prove the cooldown is wrong; it proves it is a major post-acceptance throughput gate.

Prevention: evaluate the outcomes and semantic similarity of cooldown-suppressed candidates before shortening the window. Do not call them duplicates unless the evidence actually proves duplicate trade intent.

### E055 — Live pair universe contains only two pairs
Recorded: 2026-08-07 17:38 UTC.

Verified current setting:

```text
PAIRS=EURUSD GBPUSD
TIMEFRAMES=M15
```

Effect: the live watcher cannot currently generate a signal for a third pair. Historical USDJPY rows come from older configuration and do not change current live scope.

Prevention: keep live pair-universe requirements explicit and test them as configuration acceptance criteria.

### E056 — Accepted CSV count exceeds matched retained delivery-log count
Recorded: 2026-08-07 17:38 UTC.

```text
CSV_ACCEPTED_BUY_SELL_TOTAL=110
ACCEPTED_EVENTS_PARSED_FROM_RETAINED_LOG=106
UNMATCHED_ACCEPTED_ROWS=4
```

Do not invent delivery outcomes for those four rows. They remain unknown until exact timestamp/log-path evidence is checked.

Prevention: use a durable per-decision lifecycle ledger keyed by stable decision ID rather than reconstructing lifecycle from separate CSV and free-text logs.

## Current exact signal bottleneck

Strategy stage:

```text
SCORE_GATE=903
H1_NEUTRAL=410
H4_D1_OPPOSE=4
TOTAL_REJECTED_VALID_BUY_SELL=1317
```

Delivery stage, retained matched accepted events:

```text
TELEGRAM_SENT=61
TELEGRAM_COOLDOWN=38
TELEGRAM_SCORE_GATE=6
TELEGRAM_FAILED=1
TOTAL_MATCHED_ACCEPTED=106
```

The current signal drought is therefore layered. Telegram transport is not the dominant failure: 61 sends succeeded and only one failed.

## Current control-plane incident note

Native Termux manager PID 31140 remains with matching pidfile. Latest observed topology:

```text
manager_count=1
owned=6
orphaned=1
running=7
duplicates=0
orphan=crond
```

Keep this separate from the proven signal funnel unless watcher execution becomes impaired.

## Efficient protocol

1. Read dated current handoff/audit files first.
2. State one narrow evidence question.
3. Use small pager-proof commands.
4. Validate schemas before field-based analysis.
5. Separate runtime, strategy rejection, Telegram eligibility, cooldown/dedup, transport, and persistence.
6. Preserve phone state before mutation.
7. For approved code mutation: backup, rollback, complete-file replacement, checksum, exact commit scope, tests, and independent verification.
8. Record explicit UTC date on every material finding.
9. Never fall back to direct-main writes after connector/branch errors.

## Exactly one next action

Classify the historical trade outcomes of strategy-accepted candidates suppressed by Telegram score and cooldown. Compare them with delivered-signal outcomes before changing strategy, Telegram thresholds, or cooldown. This is the least strategy-invasive path to deciding whether more user-visible signals can be safely surfaced.