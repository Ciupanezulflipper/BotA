# BotA Runtime Error Log

Last updated: 2026-08-07 17:11 UTC

This is the canonical compact error and prevention index. Historical full text remains in Git history, `ERRORS.md`, dated audit records, and GitHub issue/PR history.

Current signal evidence:

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

Current direct evidence now narrows this further:

```text
1427 valid BUY/SELL
903 rejected by M15 score gate
410 rejected by H1-neutral veto
4 rejected by H4+D1 opposition
110 accepted
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

Observed:

```text
HEADER_COLUMNS=13
ROWS_WITH_25_COLUMNS=2509
```

The watcher currently appends a newer 25-column row layout under an existing 13-column legacy header. The first 13 positions align, so current funnel classification remains valid. However, newer structured consumers that expect `filter_rejected` and `filter_reasons` by header name can silently misclassify rows.

Prevention: add an explicit schema/version migration or write a new versioned decision ledger instead of silently extending row width under an old header.

### E052 — Documentation connector wrote a placeholder directly to main
Recorded: 2026-08-07.

While attempting to create the dated stage-count audit, the connector was invoked with `branch=main` after a branch-not-found error and created a placeholder file directly on `main` in commit `6cf8538dbc6bd64746cc3f32052291d5ebe27a0e`.

This violated the established branch -> content -> diff -> PR rule. A corrective branch `docs/signal-funnel-stage-counts-20260807` was immediately created to replace the placeholder with the complete dated audit and synchronize the canonical files through a PR.

Prevention: after any branch-not-found write error, stop and create/verify the branch before retrying any content write. Never use `main` as a temporary fallback.

## Current exact signal bottleneck — 2026-08-07

Rejected valid BUY/SELL rows:

```text
SCORE_GATE=903  (68.56%)
H1_NEUTRAL=410  (31.13%)
H4_D1_OPPOSE=4  (0.30%)
TOTAL=1317
```

The counts sum exactly. Current `m15_h1_fusion.sh` returns immediately when the base M15 signal is already rejected, so score-gated rows do not proceed into H1 fusion. This supports a sequential funnel interpretation rather than mere overlapping text tags.

`macro6=3` occurs in all accepted and rejected valid BUY/SELL rows and current fusion code treats it as neutral with zero score adjustment. RR text is advisory in current `quality_filter.py`.

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

Keep this separate from the proven strategy funnel unless watcher execution becomes impaired.

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

Read current phone score/H1/Telegram threshold values and classify retained accepted-row delivery outcomes. No strategy or Telegram mutation before that proof.
