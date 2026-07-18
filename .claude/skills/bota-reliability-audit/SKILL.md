---
name: bota-reliability-audit
description: Run a forensic BotA reliability audit across Termux runtime, cron, watcher, market-data freshness, decision journaling, rejection gates, Telegram delivery, Supabase publishing, and silent-failure paths. Use when signals are missing, runtime health is questioned, or the user asks for the next BotA validation package.
user-invocable: true
---

# BotA Reliability Audit

Use this skill to determine whether BotA failed operationally, correctly rejected trades, or lacks enough evidence to classify the period. This is a reliability and data-integrity workflow, not a strategy-optimization workflow.

## Authority and scope

1. Verify the live repository and Termux runtime before trusting older diagnoses.
2. Read `BOTLOG.md` before touching files.
3. Inspect the active branch, exact head, worktree, cron, process state, and current logs.
4. Treat repository, runtime, provider responses, logs, Telegram outcomes, and database evidence as stronger than chat assertions.
5. Do not claim a valid signal was missed unless preserved evidence proves that claim.

## Protected strategy boundary

Do not change any of these without a separate explicit founder instruction:

- score thresholds;
- ADX or RSI gates;
- H1/H4/D1 veto logic;
- watched pairs or timeframes;
- SL, TP, risk, cooldown, or daily trade cap;
- session or news filters;
- provider priority for the live strategy;
- cron cadence;
- Telegram tier rules;
- Supabase eligibility or publishing behavior.

Signal scarcity is not evidence that thresholds should be loosened. First prove the runtime and decision pipeline.

## Audit sequence

### 1. Freeze the evidence pack

Capture:

- repository, branch, local head, remote head, and main;
- clean or dirty worktree;
- current UTC time and device clock health;
- active cron entries and scheduler health;
- watcher and controller processes;
- relevant file hashes and mtimes;
- last successful and failed cycles;
- exact investigation period and watched universe.

Stop on wrong repository, dirty worktree, unexplained head drift, unsafe clock, or missing investigation scope. Do not repair those conditions silently.

### 2. Prove the runtime path

Inspect the real path in execution order:

1. scheduler or cron trigger;
2. market-open gate;
3. provider fetch and freshness checks;
4. candle and indicator generation;
5. scoring engine;
6. fusion and veto logic;
7. quality filter;
8. decision journal;
9. rejection, score, tier, cooldown, and dedup gates;
10. Telegram send result;
11. Supabase publish result when applicable;
12. signal lifecycle or closer behavior.

At every hop verify required payload fields. Do not assume a function uses an argument merely because it accepts it.

### 3. Separate outcomes

Classify each completed cycle independently:

- runtime did not start;
- runtime started but provider failed;
- provider succeeded but data was stale or malformed;
- indicators or scorer failed;
- valid HOLD or WAIT decision;
- rejected BUY or SELL candidate;
- alert-grade candidate blocked by cooldown or dedup;
- Telegram attempted and failed;
- Telegram delivered;
- Supabase attempted and failed;
- Supabase published;
- evidence missing.

Do not collapse these into one status such as "no signal".

### 4. Decision-journal checks

Treat `logs/alerts.csv` as the completed-decision journal only after verifying the installed watcher still writes every parsed decision before rejection and delivery exits.

Check:

- row growth across natural cycles;
- pair and timeframe coverage;
- timestamps and clock consistency;
- direction, score, confidence, provider, rejection flag, and reasons;
- duplicate rows versus legitimate repeated decisions;
- missing intervals;
- schema consistency;
- corruption, truncation, or manual edits;
- whether historical gaps predate the observability repair.

Delivery hash and `last_sent` state must represent confirmed delivery, not candidate evaluation. Verify compare-before-send and mark-after-success ordering.

### 5. Market-data checks

For each provider used by the active runtime verify:

- request actually executed;
- HTTP or library status;
- non-empty response;
- required keys and candle count;
- latest timestamp and age;
- timezone normalization;
- pair and timeframe identity;
- fallback behavior after error, empty response, parse failure, or stale data.

Never treat empty or stale data as provider success. Do not use demo keys or synthetic data as proof of live readiness.

### 6. Telegram and database checks

Telegram:

- distinguish not eligible, not attempted, attempted, failed, and delivered;
- preserve message ID or delivery proof where available;
- verify one canonical sender;
- verify delivery dedup did not suppress journaling.

Supabase:

- distinguish not eligible, not attempted, failed, and published;
- verify exact project and table when relevant;
- do not mutate Production merely to prove connectivity;
- preserve separation between decision, Telegram, and database outcomes.

### 7. Historical investigation discipline

For historical periods:

- use point-in-time evidence only;
- record data-source coverage and gaps;
- hash acquired datasets and manifests when building a forensic sidecar;
- prevent look-ahead with truncation and poison-canary tests;
- distinguish operational outage from strategy rejection;
- state when omitted historical decisions cannot be reconstructed.

Do not optimize the strategy during a forensic investigation.

## Termux write discipline

- Audit existing files before replacement.
- Use full-file replacement only; no partial patch fragments.
- Use `~/` for temporary files, never `/tmp/`.
- Avoid fragile `set -e`; capture return codes and gate later actions explicitly.
- Do not use force-push or amend pushed commits.
- Run the repository's current sanity command before and after a change; discover the expected check count instead of hard-coding an old `18/18` value.
- Update `BOTLOG.md` with exact evidence after an approved fix.
- One proof artifact per debugging step: command, relevant output, and PASS/FAIL.

## Result classes

Use:

- `RUNTIME_FAILURE_PROVEN`
- `DATA_FAILURE_PROVEN`
- `PIPELINE_FAILURE_PROVEN`
- `DELIVERY_FAILURE_PROVEN`
- `VALID_REJECTION_PROVEN`
- `ALERT_DELIVERED_PROVEN`
- `MIXED_PERIOD`
- `INSUFFICIENT_EVIDENCE`

A period may have more than one class. State exact dates and evidence coverage.

## Required report

```text
BotA audit scope:
Exact repository head:
Runtime host and clock health:
Pairs/timeframes:
Investigation period:

Scheduler/cron:
Watcher:
Provider freshness:
Decision journal:
Rejection gates:
Cooldown/dedup:
Telegram:
Supabase:
Lifecycle closer:

Proven findings:
Inferences:
Not proven:
Data gaps:
Strategy changed:
Production files changed:
Validation performed:
Next smallest proof step:
Approval required:
```

## Invocation

`/bota-reliability-audit $ARGUMENTS`

Without arguments, perform a read-only current-state audit and identify the smallest next proof step. Do not modify strategy or Production autonomously.
