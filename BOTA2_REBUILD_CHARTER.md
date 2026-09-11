# BotA2 Clean Rebuild Charter

Recorded: 2026-09-11

## Decision

Build BotA2 in parallel from a clean architecture. Do not continue expanding legacy BotA complexity by default.

Legacy BotA remains evidence/reference only unless an explicit rollback or runtime-proof action is authorized.

## Goal

Within a bounded 3-day engineering sprint, produce a VPS-native shadow signal system for:

- EURUSD
- GBPUSD
- USDJPY
- M15 decision cadence
- H1/H4/D1 context

The 3-day target is a technically correct, observable, replayable shadow bot. It is not a claim that the strategy has a profitable edge after three days.

## Non-negotiable architecture

1. Linux VPS first. No Android/Termux production execution authority.
2. One systemd service and one Python process authority.
3. Python-first implementation. Shell only for tiny deployment wrappers when unavoidable.
4. Immutable application release plus one explicit mutable data root.
5. One typed configuration object; no hidden environment precedence.
6. Closed-candle decisions only.
7. Every pair-cycle produces exactly one structured decision record.
8. Every decision records provider, candle identity, feature inputs, score components, filters, outcome, release SHA and config fingerprint.
9. Append-only event ledger is authoritative for runtime evidence.
10. Telegram and downstream publication use idempotent delivery identities and durable intent/outcome state.
11. No strategy tuning while measurement integrity is being proven.
12. No live-money trading.

## What BotA2 may reuse

Reuse knowledge, tests, datasets and validated semantics; do not blindly reuse runtime architecture.

Candidate reusable knowledge:

- three-pair scope;
- M15/H1/H4/D1 feature semantics;
- Policy-B hypothesis (`score >= 70`, `ADX < 30`) as a frozen research candidate, not proven edge;
- pair-aware pip sizing;
- trusted server UTC;
- historical/replay datasets and outcome records where provenance is valid;
- delivery idempotency lessons;
- failure patterns from BotA audits.

## What BotA2 must not inherit

- runit/runsvdir;
- cron as execution authority;
- watchdog forests;
- multiple restart authorities;
- code root used as mutable state root;
- CSV schema drift as authoritative state;
- parsing human logs to infer decisions;
- phone wall-clock dependence;
- silent `|| true` around measurement-critical operations;
- broad catch-and-continue behavior on data/scoring failures;
- false-green health based only on process existence.

## Day 1 — deterministic core

Deliver:

- package skeleton and typed config;
- provider interface;
- candle normalization;
- feature/indicator layer;
- deterministic strategy interface;
- three-pair decision engine;
- structured decision schema;
- unit tests using fixed fixtures;
- replay command that has no network side effects.

Exit gate:

`same fixture + same config + same release => byte-equivalent decision payload excluding generated IDs/timestamps`.

## Day 2 — measurement and delivery

Deliver:

- append-only SQLite or JSONL event ledger with explicit schema version;
- run/cycle/decision IDs;
- provider and candle provenance;
- outcome resolver contract;
- Telegram delivery state machine: intent -> sent / definite_failure / unknown_outcome;
- duplicate-send prevention;
- runtime health based on useful progress, not PID existence;
- historical replay over available validated dataset;
- baseline metrics: decision count, accepted count, coverage, expectancy inputs.

Exit gate:

No unexplained missing pair-cycle decisions in a deterministic replay window.

## Day 3 — VPS shadow deployment

Deliver:

- systemd unit;
- immutable release directory;
- mutable data directory;
- transactional exact-SHA deployment;
- restart/reboot recovery;
- singleton proof;
- market-open natural cycle for all three pairs;
- no-side-effect/shadow mode by default;
- optional Telegram only after decision/delivery proof;
- one operator report containing runtime identity, pair-cycle coverage, data quality and signal counts.

Exit gate:

A fresh open-market cycle must show for all three pairs:

- valid candle identity;
- nonzero/valid market price where applicable;
- valid ATR/volatility inputs;
- deterministic score/filter result;
- explicit HOLD/BUY/SELL outcome;
- no missing-indicator fallback masquerading as a strategy decision.

## Performance truth

BotA2 is not considered successful because it stays online or emits signals.

Separate gates:

- ENGINEERING_VALIDATED: runtime and measurement integrity proven.
- STRATEGY_VALIDATED: positive net expectancy after realistic costs on a predefined confirmatory sample.

Until the second gate passes:

`BOTA2_EDGE_STATUS=UNVALIDATED`

## 3-day success definition

At the end of the sprint, the correct outcome is one of two states:

### A. Valid measurement system

BotA2 runs continuously, produces complete three-pair evidence, and gives us trustworthy data to test the strategy.

### B. Strategy rejected quickly

Replay/live-shadow evidence shows no usable edge. Stop without spending months hardening a losing strategy.

Both are better outcomes than another long cycle of infrastructure repair without decision-quality evidence.
