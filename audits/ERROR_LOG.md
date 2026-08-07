# BotA Runtime Error Log

Last updated: 2026-08-07 17:01 UTC

This is the canonical compact error and prevention index. Historical full text
remains in Git history, `ERRORS.md`, dated audit records, and GitHub issue/PR
history.

Current signal evidence:

- `audits/SIGNAL_FUNNEL_FORENSICS_2026-08-07.md`
- `CONTINUITY_CURRENT.md`
- `CHAT_HANDOFF_BOTA.md`

## Current status — 2026-08-07

```text
PRODUCTION_VALIDATION=FAILED_HISTORICAL
CURRENT_NATIVE_MANAGER_PID=31140
CURRENT_CONTROL_PLANE=DEGRADED_6_OWNED_1_ORPHAN
CURRENT_REQUIRED_RUNNING=7_OF_7
CURRENT_ORPHAN_SERVICE=crond
LIVE_WATCHER=RUNNING
SIGNAL_DECISION_ROWS=2507
SIGNAL_BUY_SELL_ROWS=1425
SIGNAL_ACCEPTED_ROWS=110
SIGNAL_REJECTED_ROWS=2397
SIGNAL_REJECTION_RATE≈95.61_PERCENT
ZERO_ENTRY_ROOT_CAUSE=NO
AUTOMATIC_RECOVERY_REENABLE_ALLOWED=NO
STRATEGY_MUTATION_ALLOWED=NO_PENDING_FUNNEL_PROOF
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
Too many evidence domains were combined and output exceeded practical terminal
capture limits.
Prevention: bounded, pager-proof packages and smaller direct proofs.

### E027 — Control-plane regression after prior closure
One manager owned only part of the service set.
Prevention: ownership gate before deeper diagnosis.

### E031 — `supervise/pid` misidentified as `runsv`
Prevention: service PID -> PPID -> `runsv` -> manager chain.

### E032 — Manager existed while supervisors were orphans
Prevention: manager existence and service ownership are separate gates.

### E035 — Placeholder/direct-main documentation commits
Prevention: branch -> content -> diff verification -> PR.

### E039 — Continuous guard associated with repeated Termux restarts
Prevention: no continuous recovery without executable-path proof, locking,
backoff, kill switch, failure injection, and restart observation.

### E040 — D1 mismatch survived broad discovery
Status: CLOSED. `tf_minutes("D1")` now returns 1440 on the phone.

### E043 — Supervisor wrapper contradicted disabled-recovery policy
Status: CLOSED by P7 for that wrapper path. Later incidents still require exact
ownership verification; closure of one wrapper defect does not prove permanent
control-plane health.

### E045 — Strict shell mode left active in interactive Termux
A direct `set -euo pipefail` in the parent shell caused Termux to exit after an
expected failed assertion.
Prevention: strict mode only inside a bounded child process.

### E046 — Active service path assumed to be repository path
The active runit directory and repository copy could be separate physical files.
Prevention: compare realpath, mode, and checksum for both paths before deployment.

### E047 — Runtime work obscured the signal-throughput acceptance criterion
Recorded: 2026-08-07.

Months of work repeatedly proved service, heartbeat, reporting, Telegram, and
control-plane properties while recent PR scopes explicitly avoided strategy and
signal-semantic changes. Runtime health was treated too often as a proxy for the
actual product goal: useful signals.

Current direct evidence:

```text
logs/alerts.csv rows=2507
HOLD=1082
SELL=959
BUY=466
accepted=110
rejected=2397
rejection_rate≈95.61%
```

Prevention: maintain separate acceptance gates for runtime health, raw direction
generation, filter acceptance, persistence, and Telegram delivery.

### E048 — Zero-entry symptom almost promoted to root cause
Recorded: 2026-08-07.

Initial filter strings frequently contained `entry_invalid_zero` and `rr<=0`.
A direct all-row classification then proved:

```text
all_zero_entry_sl_tp=1014
all_zero_rows_direction=HOLD
all_zero_rows_score=0.00
zero_entry_buy_sell_rows=0
```

Verdict: `entry=0/sl=0/tp=0` is a HOLD symptom in this corpus, not the root cause
of lost BUY/SELL signals.

Prevention: correlate suspected defects with tradeable/non-tradeable direction
before tracing downstream fields.

### E049 — Ad-hoc CSV audit used the wrong field name
Recorded: 2026-08-07.

The actual CSV header is:

```text
timestamp,pair,tf,direction,score,confidence,entry,sl,tp,provider,rejected,filter_str,reasons
```

One exploratory script looked up `filter_rejected` and silently received empty
values. Its filter-status section is invalid evidence. Its direction/entry
classification remains valid because those fields exist.

Prevention:

- print/validate required headers before analysis;
- fail closed when an expected field is missing;
- never treat empty fallback values as proof.

### E050 — Pager captured a large Git forensic command
Recorded: 2026-08-07.

A broad `git show/log` package entered `less`; the terminal displayed `less` help
instead of completing a capturable evidence package.

Prevention: set `GIT_PAGER=cat`, use `git --no-pager`, and keep output bounded.

## Current control-plane incident note — 2026-08-07

Native Termux `service-daemon` manager PID 31140 and its pidfile were created at
essentially the same instant, strongly attributing that manager to the native
`service-daemon/start-stop-daemon` path. Exact human/executor attribution is not
proven.

Earlier two managers existed. The detached `-P` manager PID 16360 later died and
supervisors progressively reconverged to PID 31140. Latest observed topology:

```text
manager_count=1
owned=6
orphaned=1
running=7
duplicates=0
orphan=crond
```

Do not manually kill PID 31140 or the remaining orphan during signal-funnel
analysis.

## Efficient protocol

1. Read the dated current handoff/audit files first.
2. State one narrow evidence question.
3. Use small pager-proof commands.
4. Validate schemas before field-based analysis.
5. Separate runtime health, strategy rejection, dedup/cooldown, persistence, and Telegram delivery.
6. Preserve phone state before mutation.
7. For approved code mutation: backup, rollback, complete-file replacement, checksum, exact commit scope, tests, and independent verification.
8. Record the UTC date on every material finding.

## Exactly one next action

Classify the 1493 valid-entry rows by the real `rejected` field, pair, direction,
score bucket, and exact `filter_str`; then inspect the 110 accepted rows for
Telegram eligibility and delivery. No strategy mutation before that proof.
