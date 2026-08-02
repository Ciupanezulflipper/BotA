# BotA Current Repair Handoff — 2026-08-02

Status: repository repairs in progress; phone deployment not performed.

This file supersedes earlier readiness claims for work completed on 2026-08-02. Historical incident detail remains in `audits/INCIDENT_2026-08-01_VALIDATION_FAILURE.md`, `ERRORS.md`, `audits/ERROR_LOG.md`, and issue #9.

## Scope lock

Reliability, observability, data integrity, and notification correctness only.

Do not change merely to create more signals:

- strategy logic;
- score or ADX thresholds;
- pair scope;
- H1/D1 confirmation or veto rules;
- SL/TP or risk/reward logic;
- dedup semantics;
- Supabase signal lifecycle semantics.

## Production truth

The one-week validation ending 2026-08-01 failed. During that period, BotA experienced control-plane ownership regressions, service-count loss, repository/runtime divergence, canonical-crontab failure, provider-budget ambiguity, and notification defects.

At the final rollback verification on the phone:

```text
manager_count=1
owned=7/7
running=7/7
orphaned=0
control_plane_rc=0
automatic_recovery=disabled
```

That was a point-in-time rollback state, not a completed production validation. The phone checkout has not been deployed from the repaired GitHub `main` during the 2026-08-02 repository work.

## Repairs merged on 2026-08-02

### PR #26 — canonical production-validation truth

- corrected the August 1 incident record;
- superseded stale July readiness claims;
- quarantined the contaminated PR #24 handoff;
- recorded that broad data discovery was complete and must not be repeated.

Merge commit:

```text
78d9d6bceea5741867f718631ef00fc07c5d804d
```

### PR #28 — D1 indicator timeframe validation

Root cause: the updater configured `D1`, but `build_indicators.py::tf_minutes()` recognized only `M*` and `H*`, causing every D1 bundle to fail as `tf_mismatch` with `tf_actual_min=0.0`.

Repair:

- map `D1` and `1D` to 1440 minutes;
- retain fail-closed rejection for mislabeled intraday data;
- add regression coverage for weekday daily candles and weekend gaps.

Merge commit:

```text
e09662d4b54faf6592d628d145a2fbce803cbd07
```

### PR #30 — cache-only technical status formatter

Repair:

- removed hidden provider calls from status formatting;
- read only canonical local indicator caches;
- validated pair, timeframe, bundle state, and finite numeric values;
- exposed missing/invalid timeframes explicitly;
- preserved valid zero values;
- replaced internal `Vote` and `/9` wording with user-facing trend labels;
- stated that the output is technical context, not a trade entry;
- removed device UTC and raw API-budget output.

Merge commit:

```text
2e7e02bce8ccc3c1d0b70f403c0e616d8a3b4be9
```

### PR #31 — market-gated Telegram status delivery

Repair:

- run the trusted market gate before formatting or delivery;
- fail closed when market state or trusted time cannot be established;
- use one isolated temporary workspace per invocation;
- avoid recursive cleanup;
- add dry-run validation;
- use bounded Telegram transport;
- retain curl exit code, HTTP status, stderr, and response diagnostics.

Merge commit:

```text
bfd6f26acc1d0197e04d16bd8ec58be840fe893c
```

### PR #32 — heartbeat delivery state and retry control

Repair:

- moved heartbeat delivery into a testable Python controller;
- kept the shell heartbeat as a thin wrapper;
- log local runtime evidence every invocation;
- separate Telegram reachability from trading eligibility;
- parse Telegram configuration as data without shell execution;
- prevent concurrent delivery with a nonblocking file lock;
- persist state atomically;
- suppress successful delivery for one hour;
- apply exponential failure backoff from five minutes to one hour;
- reset persisted cadence using kernel boot identity when available, with monotonic rollback fallback;
- pin transport to Telegram's fixed host;
- bound timeout, response size, diagnostics, counters, and log lines;
- preserve URL, HTTP, timeout, invalid-JSON, and rejection details;
- add dry-run and force-send controls;
- add focused mocked transport and state tests.

No real Telegram call was made during repository validation.

## Superseded branches and PRs

Do not merge or deploy:

- PR #24 — contaminated preservation branch;
- PR #27 — pre-documentation-main D1 branch;
- PR #29 — combined formatter/sender experiment superseded by PRs #30 and #31.

## What remains unresolved

### 1. Supervisor clock semantics

Current repository behavior still needs a separate repair:

- trading and market-session decisions must remain fail-closed when trusted server UTC is unavailable;
- a transient server-clock lookup failure alone must not classify an otherwise healthy process/control plane as fully malfunctioning;
- runtime health must expose market-clock availability separately from process/pipeline health;
- local ship-time drift must remain informational when trusted server UTC is available.

Do not combine this with heartbeat delivery or strategy work.

### 2. Phone deployment and repository divergence

The repaired GitHub `main` has not been applied to the phone in this workstream.

Before deployment:

1. identify the phone branch, exact HEAD, and every local modification;
2. preserve phone-only changes without resetting or overwriting them;
3. compare the phone files with repaired `main`;
4. deploy one isolated package at a time with backup and rollback;
5. independently verify behavior after each package.

### 3. Production runtime validation

After safe deployment, production acceptance still requires:

- control-plane ownership remains healthy over time;
- canonical crontab and active execution sources agree;
- updater/watcher progress is fresh during an open market session;
- D1 bundles are valid on the phone;
- status messages create no hidden provider calls;
- heartbeat retry state behaves as designed;
- the next eligible ACTIVE signal completes Telegram, Supabase, closer, and CLOSED/CANCELLED lifecycle proof.

## Execution rules

- no direct push to `main`;
- no broad rediscovery of files, logs, caches, and history already collected on 2026-08-02;
- no migration executor, finalizer, watchdog, or continuous guard while automatic recovery is intentionally disabled;
- no `/proc/uptime` dependency;
- trusted server/provider UTC controls market semantics;
- monotonic time controls same-boot cadence;
- one narrow question or mutation per package;
- read-only discovery before mutation;
- full-file replacement only;
- backup, rollback, and independent verification for phone mutations.

## Repository-work acceptance status

```text
RUNTIME_MUTATION_PERFORMED=NO
PHONE_DEPLOYMENT_PERFORMED=NO
REAL_PROVIDER_CALLS_PERFORMED=NO
REAL_TELEGRAM_CALLS_PERFORMED=NO
STRATEGY_CHANGED=NO
DIRECT_MAIN_PUSH=NO
```

## Exactly one next repository action

Repair `tools/bota_supervisor.sh` clock-health semantics on a fresh branch from current `main`, with focused behavioral tests. Preserve fail-closed trading while separating market-clock availability from runtime process/pipeline health.
