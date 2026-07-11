# BotA Operational Safeguard Plan

## Objective

- [proven] The objective is not to guarantee profitability.
- [proven] The objective is to ensure that BotA's silence, rejection, signal, and failure states are distinguishable and evidence-backed.
- [proven] Safeguards must not silently change strategy behavior.

## Priority 0 — Mandatory before strategy conclusions

### SG-001 Canonical runtime manifest

- [inferred] Maintain a machine-readable list of all mandatory runtime jobs.
- [inferred] Validate exact command, cadence, timezone, environment source, and output destination.
- [inferred] Detect missing, duplicated, unauthorized, or modified entries.
- [inferred] Fail state: `RUNTIME_CONFIGURATION_INVALID`.

### SG-002 Component heartbeat contract

- [inferred] Each mandatory component writes its own structured heartbeat.
- [inferred] Heartbeats must include UTC timestamp, source commit, configuration hash, process result, and last successful work time.
- [inferred] A generic system heartbeat cannot substitute for component heartbeats.

### SG-003 Expected-cycle ledger

- [inferred] Create one record for every scheduled M15 production cycle.
- [inferred] A cycle must terminate in exactly one primary state:
  - [inferred] `OPERABLE`;
  - [inferred] `RUNTIME_DOWN`;
  - [inferred] `DATA_UNUSABLE`;
  - [inferred] `UNKNOWN`.
- [inferred] Decision results must be recorded separately from operability.

### SG-004 Persist decision before deduplication

- [inferred] Store the complete decision and reasons before notification suppression.
- [inferred] Deduplication affects delivery only, not the forensic record.

### SG-005 Updater completion records

- [inferred] Updater logs must be timestamped JSON Lines.
- [inferred] Success requires explicit completion for every required pair and timeframe.
- [inferred] A crontab entry or process start is insufficient.

### SG-006 Recovery verification gate

- [inferred] Recovery is complete only when:
  - [inferred] canonical crontab validates;
  - [inferred] supervisor executes;
  - [inferred] updater completes required caches;
  - [inferred] watcher completes a cycle;
  - [inferred] heartbeat records success;
  - [inferred] Telegram or durable local alert confirms recovery.
- [inferred] Until all checks pass, state remains `DEGRADED` or `UNKNOWN`.

## Priority 1 — Required for trustworthy replay

### SG-007 Raw-first market-data preservation

- [proven] Preserve provider response before parsing or validation.
- [inferred] Record request parameters, provider, response hash, retrieval time, and validation outcome.

### SG-008 Point-in-time availability enforcement

- [proven] Every candle or context record requires `available_at_utc`.
- [proven] Replay cycles must not consume future-known data.

### SG-009 Provider reconciliation

- [inferred] Compare the primary historical source with an independent source.
- [inferred] Record mismatches, missing candles, duplicates, timestamp differences, and price tolerances.

### SG-010 Production/replay parity tests

- [inferred] Execute production decision functions against fixed fixtures.
- [inferred] Replay must match production ordering, gates, scoring, and failure semantics.
- [inferred] A parity failure blocks strategy conclusions.

## Priority 2 — Reliability hardening

### SG-011 Independent operational alerting

- [inferred] Queue local alerts durably when Telegram is unavailable.
- [inferred] Send recovery summaries after connectivity returns.

### SG-012 Boot and lifecycle validation

- [inferred] On boot, verify Termux services, wake lock, crond, canonical crontab, storage, network, and environment files.
- [inferred] Do not report BotA healthy until component verification completes.

### SG-013 Structured recovery journal

- [inferred] Every repair records before state, action, after state, hashes, verification results, and UTC time.

### SG-014 Log retention and integrity

- [inferred] Rotate logs predictably.
- [inferred] Preserve manifests and hashes.
- [inferred] Never delete the only evidence of a critical failure before a verified snapshot exists.

## Implementation order

1. [inferred] Canonical runtime manifest validator.
2. [inferred] Component-specific heartbeat and status schema.
3. [inferred] Expected-cycle ledger.
4. [inferred] Persist-before-dedup decision logging.
5. [inferred] Updater structured completion events.
6. [inferred] Recovery verification gate.
7. [inferred] Data integrity and replay parity gates.
8. [inferred] Lifecycle and retention hardening.

## Non-goals

- [proven] No strategy thresholds will be loosened.
- [proven] No pair or timeframe scope will be changed.
- [proven] No scoring, fusion, risk, or notification eligibility semantics will be changed.
- [proven] No historical `UNKNOWN` interval will be rewritten as `DOWN` without additional evidence.
