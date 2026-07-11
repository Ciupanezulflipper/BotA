# BotA Operational Weakness Register

## Purpose

- [proven] This register records operational, data-integrity, observability, and forensic weaknesses discovered during the historical replay investigation.
- [proven] It does not authorize strategy, scoring, threshold, pair, timeframe, risk, or fusion changes.
- [proven] A weakness remains open until its safeguard has implementation evidence and test evidence.
- [proven] Missing evidence must remain `UNKNOWN`; it must not be silently converted into `UP`, `DOWN`, success, or failure.

## Severity definitions

- [proven] `CRITICAL`: can silently prevent production evaluation or invalidate the historical conclusion.
- [proven] `HIGH`: can materially distort runtime, data, or decision reconstruction.
- [proven] `MEDIUM`: weakens observability, auditability, or recovery confidence.
- [proven] `LOW`: creates friction or ambiguity but does not independently invalidate results.

---

## OW-001 — Partial crontab configuration loss

- [proven] Severity: `CRITICAL`.
- [proven] Domain: runtime configuration.
- [proven] The production crontab lacked the signal watcher, indicators updater, shadow manager, and supervisor at preserved snapshots `2026-07-08T11:37:37Z` and `2026-07-08T11:41:32Z`.
- [proven] Daily and heartbeat jobs remained present.
- [proven] A running `crond` process therefore did not prove that the BotA production runtime was complete.
- [proven] Impact: the signal pipeline could stop while unrelated cron jobs continued.
- [proven] Required safeguard: canonical crontab manifest and recurring exact-set validation.
- [proven] Required alert: immediate Telegram alert when any mandatory job is missing, duplicated, or changed.
- [proven] Required recovery: idempotent canonical crontab reinstall with post-install verification.
- [proven] Status: `OPEN`.
- [proven] Evidence: `Q5_CRONTAB_RECOVERY_AUDIT.md`, `q5_crontab_recovery_audit.json`.

## OW-002 — Runtime health check was too shallow

- [proven] Severity: `CRITICAL`.
- [proven] Domain: runtime observability.
- [proven] Existing evidence showed that heartbeat or daily activity could continue while the signal pipeline was incomplete.
- [proven] Impact: BotA could appear alive while not evaluating production cycles.
- [proven] Required safeguard: component-level health contract for watcher, updater, supervisor, heartbeat, shadow manager, and canonical crontab integrity.
- [proven] Required state values: `HEALTHY`, `DEGRADED`, `FAILED`, `UNKNOWN`.
- [proven] Required alert: identify the exact failed component rather than only reporting “Bot alive.”
- [proven] Status: `OPEN`.

## OW-003 — No authoritative expected-cycle ledger

- [proven] Severity: `CRITICAL`.
- [proven] Domain: forensic completeness.
- [proven] The investigation had to infer missing execution from independent logs rather than from one authoritative cycle ledger.
- [proven] Impact: silence could mean market closed, runtime failure, data failure, deduplication, rejection, or missing logging.
- [proven] Required safeguard: one immutable record for every expected production evaluation cycle.
- [proven] Required fields:
  - [inferred] scheduled cycle UTC;
  - [inferred] actual start UTC;
  - [inferred] actual end UTC;
  - [inferred] pair;
  - [inferred] timeframe;
  - [inferred] runtime state;
  - [inferred] data state;
  - [inferred] decision state;
  - [inferred] notification state;
  - [inferred] failure reason;
  - [inferred] source commit;
  - [inferred] configuration fingerprint.
- [proven] Status: `OPEN`.

## OW-004 — Decision records were historically incomplete

- [proven] Severity: `CRITICAL`.
- [proven] Domain: decision auditability.
- [proven] Earlier code applied deduplication before writing complete decision records.
- [proven] Impact: rejected, duplicate, or skipped evaluations may not have left a full forensic record.
- [proven] Required safeguard: persist the complete decision record before notification deduplication or delivery suppression.
- [proven] Required distinction:
  - [inferred] evaluation completed;
  - [inferred] decision produced;
  - [inferred] alert eligible;
  - [inferred] alert deduplicated;
  - [inferred] alert delivered;
  - [inferred] alert delivery failed.
- [proven] Status: `OPEN`.

## OW-005 — Runtime state and data usability were conflated

- [proven] Severity: `HIGH`.
- [proven] Domain: classification.
- [proven] A running watcher does not prove that required market data was present, fresh, or point-in-time valid.
- [proven] Required safeguard: separate runtime state from data state.
- [proven] Required cycle classifications:
  - [inferred] `OPERABLE`;
  - [inferred] `RUNTIME_DOWN`;
  - [inferred] `DATA_UNUSABLE`;
  - [inferred] `UNKNOWN`.
- [proven] Status: `PARTIALLY IMPLEMENTED`.
- [proven] Existing audit modules: `runtime_epochs.py`, `cycle_operability.py`.

## OW-006 — Missing evidence could be mistaken for downtime

- [proven] Severity: `HIGH`.
- [proven] Domain: forensic reasoning.
- [proven] The long June 22 to July 8 watcher-family gap does not prove continuous downtime across the entire interval.
- [proven] Required safeguard: uncovered periods default to `UNKNOWN`.
- [proven] Required rule: only explicit evidence can create `UP` or `DOWN` epochs.
- [proven] Status: `PARTIALLY IMPLEMENTED`.
- [proven] Evidence: `Q5_FORENSIC_FINDING.md`, `CANONICAL_RUNTIME_EVIDENCE.json` when committed.

## OW-007 — Updater execution lacked timestamped success evidence

- [proven] Severity: `HIGH`.
- [proven] Domain: data pipeline observability.
- [proven] The restored updater crontab entry did not provide timestamped proof of the first successful updater execution.
- [proven] The strict audit found `0` strict timestamped successes, `0` strict timestamped failures, and `7,266` untimed execution-like lines.
- [proven] Impact: configuration presence could be mistaken for successful cache refresh.
- [proven] Required safeguard: structured updater start and completion records with UTC timestamps.
- [proven] Required fields:
  - [inferred] pair;
  - [inferred] timeframe;
  - [inferred] provider;
  - [inferred] requested range;
  - [inferred] final candle timestamp;
  - [inferred] rows written;
  - [inferred] freshness result;
  - [inferred] execution result;
  - [inferred] error code.
- [proven] Status: `OPEN`.

## OW-008 — Logs were not uniformly structured

- [proven] Severity: `HIGH`.
- [proven] Domain: observability.
- [proven] Multiple logs required broad regular-expression searches and produced false-positive matches.
- [proven] The initial updater recovery search incorrectly selected supervisor evidence as updater success.
- [proven] Required safeguard: JSON Lines event schema for every critical component.
- [proven] Required common fields:
  - [inferred] `event_time_utc`;
  - [inferred] `component`;
  - [inferred] `event_type`;
  - [inferred] `status`;
  - [inferred] `cycle_id`;
  - [inferred] `run_id`;
  - [inferred] `source_commit`;
  - [inferred] `details`.
- [proven] Status: `OPEN`.

## OW-009 — Log timestamps were sometimes absent or ambiguous

- [proven] Severity: `HIGH`.
- [proven] Domain: forensic chronology.
- [proven] Thousands of updater-related lines lacked timestamps suitable for boundary reconstruction.
- [proven] Required safeguard: every operational line must carry an explicit timezone-aware UTC timestamp.
- [proven] Required rule: local device time must not be the only stored timestamp.
- [proven] Status: `OPEN`.

## OW-010 — Clock drift and fallback clock behavior weakened confidence

- [proven] Severity: `HIGH`.
- [proven] Domain: time integrity.
- [proven] Captured daily-gate records included `DRIFT_WARN`, `SERVER_CLOCK_UNAVAILABLE`, and `FALLBACK_LAST_GOOD`.
- [proven] Impact: cycle timing, freshness, session gates, and report windows can be misclassified.
- [proven] Required safeguard: independent clock-health state with explicit maximum tolerated drift.
- [proven] Required rule: critical evaluations fail closed when time integrity exceeds the approved limit.
- [proven] Required alert: clock degradation and fallback-clock use.
- [proven] Status: `OPEN`.

## OW-011 — Recovery evidence did not prove full service restoration

- [proven] Severity: `HIGH`.
- [proven] Domain: recovery verification.
- [proven] Crontab restoration proved configuration presence, not successful execution of every restored job.
- [proven] Watcher and supervisor execution were located after restoration.
- [not proven] The first successful updater execution was not located.
- [proven] Required safeguard: recovery gate that verifies every mandatory component before declaring BotA recovered.
- [proven] Status: `OPEN`.

## OW-012 — No canonical configuration fingerprint in runtime records

- [inferred] Severity: `HIGH`.
- [inferred] Domain: configuration integrity.
- [inferred] Without a stored configuration fingerprint, a cycle cannot independently prove which crontab, environment, thresholds, pair scope, or runtime files were active.
- [inferred] Required safeguard: hash canonical runtime configuration and attach the hash to every cycle record.
- [inferred] Status: `OPEN`.

## OW-013 — Raw evidence preservation was not automatic

- [proven] Severity: `HIGH`.
- [proven] Domain: evidence integrity.
- [proven] The investigation required a dedicated collector to copy, redact, hash, and manifest runtime evidence.
- [inferred] Required safeguard: automatic rotating forensic snapshots after critical failures and recoveries.
- [inferred] Required retention: preserve manifests, hashes, configuration, process state, and relevant logs.
- [proven] Status: `PARTIALLY IMPLEMENTED`.
- [proven] Existing collector: `tools/collect_termux_runtime_evidence.sh`.

## OW-014 — Broad keyword analysis can create false conclusions

- [proven] Severity: `MEDIUM`.
- [proven] Domain: audit methodology.
- [proven] Broad keyword matching generated an updater false positive and inflated candidate counts.
- [proven] Required safeguard: source-specific schemas and strict event predicates.
- [proven] Required rule: keyword hits are candidates, not conclusions.
- [proven] Status: `OPEN`.

## OW-015 — Production and replay parity is not yet fully proven

- [not proven] Severity: `CRITICAL`.
- [not proven] Domain: replay fidelity.
- [not proven] Exact production scoring, fusion ordering, and all provider extraction behavior have not yet been proven equivalent in the historical replay.
- [proven] Required safeguard: executable parity tests using production fixtures and known decision records.
- [proven] Required rule: no strategy conclusion until parity passes.
- [proven] Status: `OPEN`.

## OW-016 — Full historical market-data integrity is not yet proven

- [not proven] Severity: `CRITICAL`.
- [not proven] Domain: historical data.
- [not proven] Full-window acquisition and independent provider reconciliation are not complete.
- [proven] Required safeguard: raw-first acquisition, immutable source payloads, coverage reports, candle-gap checks, duplicate checks, and independent reconciliation.
- [proven] Required rule: incomplete or irreconcilable data becomes `DATA_UNUSABLE` or `UNKNOWN`.
- [proven] Status: `OPEN`.

## OW-017 — Point-in-time availability can be violated by later-known data

- [proven] Severity: `CRITICAL`.
- [proven] Domain: look-ahead prevention.
- [proven] D1 and other higher-timeframe data require explicit provider availability times rather than candle labels alone.
- [proven] Required safeguard: every replay input must carry an `available_at_utc` value.
- [proven] Required rule: a cycle may consume only data available at or before that cycle.
- [proven] Status: `PARTIALLY IMPLEMENTED`.

## OW-018 — Provider failure semantics need explicit preservation

- [inferred] Severity: `HIGH`.
- [inferred] Domain: market-data reliability.
- [inferred] Provider rotation or fallback can conceal which provider failed, returned stale data, or changed response shape.
- [inferred] Required safeguard: preserve provider attempts, response status, validation result, fallback reason, and selected source.
- [inferred] Status: `OPEN`.

## OW-019 — Operational alerts may share failure dependencies

- [suspected] Severity: `HIGH`.
- [suspected] Domain: alerting.
- [suspected] If Telegram delivery depends on the same runtime or credentials as the failed component, a failure alert may also fail.
- [suspected] Required safeguard: local durable failure queue and independent next-start recovery notification.
- [suspected] Status: `OPEN`.

## OW-020 — Android and Termux lifecycle risks remain

- [inferred] Severity: `HIGH`.
- [inferred] Domain: hosting platform.
- [inferred] Android process killing, battery optimization, reboot behavior, storage pressure, network loss, and Termux service state can interrupt BotA.
- [inferred] Required safeguard:
  - [inferred] boot validation;
  - [inferred] wake-lock verification;
  - [inferred] battery-optimization exemption verification;
  - [inferred] storage threshold alert;
  - [inferred] process watchdog;
  - [inferred] network reachability state;
  - [inferred] restart verification.
- [inferred] Status: `OPEN`.

## OW-021 — Silent log truncation or rotation could erase evidence

- [suspected] Severity: `MEDIUM`.
- [suspected] Domain: evidence retention.
- [suspected] Long-running flat files can be truncated, overwritten, or grow without controlled retention.
- [suspected] Required safeguard: controlled rotation with hash-chained manifests and retention policy.
- [suspected] Status: `OPEN`.

## OW-022 — Recovery actions lacked one authoritative audit trail

- [proven] Severity: `MEDIUM`.
- [proven] Domain: change management.
- [proven] Multiple July 8 backup and canonical-install files were required to reconstruct the recovery sequence.
- [proven] Required safeguard: one structured recovery transaction record containing before hash, after hash, actions, verifier results, and operator.
- [proven] Status: `OPEN`.

## OW-023 — Component success can be inferred from another component

- [proven] Severity: `HIGH`.
- [proven] Domain: evidence isolation.
- [proven] Supervisor evidence was initially misidentified as updater success.
- [proven] Required safeguard: only a component's own structured completion event can prove its successful execution.
- [proven] Status: `OPEN`.

## OW-024 — Strategy diagnosis can be attempted before operational diagnosis

- [proven] Severity: `CRITICAL`.
- [proven] Domain: decision governance.
- [proven] Low signal volume can originate from runtime failure, unusable data, valid rejection, or strategy behavior.
- [proven] Required safeguard: mandatory diagnostic decision matrix before any strategy change.
- [proven] Status: `OPEN`.

## OW-025 — No explicit stop-depth rule previously existed

- [proven] Severity: `MEDIUM`.
- [proven] Domain: audit efficiency.
- [proven] Repeated broad searches created diminishing returns and false-positive risk.
- [proven] Required safeguard: stop forensic expansion when:
  - [inferred] the failure class is established;
  - [inferred] defensible boundaries are recorded;
  - [inferred] unresolved intervals are explicitly `UNKNOWN`;
  - [inferred] operational safeguards are defined;
  - [inferred] further evidence is unavailable or would not alter the decision category.
- [proven] Status: `CLOSED BY POLICY`.

## OW-026 — Termux restart recovery was not automatically verified

- [proven] Severity: `CRITICAL`.
- [proven] Domain: Android and Termux lifecycle.
- [proven] A Termux restart closed all active shell sessions.
- [proven] The canonical crontab survived the restart.
- [proven] The scheduler resumed as `crond`, and scheduled supervisor execution was subsequently proven.
- [proven] Existing process detection initially produced a false negative.
- [inferred] Required safeguard: a post-boot gate must verify the scheduler process, canonical crontab hash, supervisor cycle, updater completion, watcher cycle, clock integrity, and alerting health.
- [proven] Status: `OPEN`.

## OW-027 — Device clock was unsafe by approximately two hours

- [proven] Severity: `CRITICAL`.
- [proven] Domain: time integrity.
- [proven] Three independent HTTP date sources agreed within seconds.
- [proven] Local device time was approximately `7,267` seconds behind their median time.
- [proven] BotA correctly entered `DEGRADED` mode for `local_clock_drift`.
- [proven] Impact: candle freshness, scheduling, session gates, logs, and replay boundaries can be misclassified.
- [inferred] Required safeguard: post-boot independent clock verification and fail-closed operation above the approved drift threshold.
- [proven] Status: `OPEN — DEVICE SETTING REPAIR REQUIRED`.

## OW-028 — Heartbeat used an obsolete credential path

- [proven] Severity: `HIGH`.
- [proven] Domain: operational alerting.
- [proven] `tools/heartbeat.sh` expected `config/tele.env`.
- [proven] That file was absent.
- [proven] Valid Telegram variable names existed in `.env.runtime`.
- [proven] The heartbeat logged an hourly missing-environment failure.
- [proven] Required safeguard: source the canonical `.env.runtime` file and fail closed without printing secret values.
- [proven] Audit-branch repair status: `READY FOR CI`.
- [not proven] Production repair status: not deployed.

## OW-029 — Runtime-health diagnosis used the wrong output file

- [proven] Severity: `HIGH`.
- [proven] Domain: diagnostic correctness.
- [proven] The empty wrapper log appeared stale.
- [proven] The authoritative runtime-health log was fresh and repeatedly recorded HTTP `200` and `RESULT=PASS rc=0`.
- [proven] Impact: a healthy component was incorrectly classified as needing repair.
- [proven] Required safeguard: every component must declare its authoritative success artifact.
- [proven] Status: `OPEN`.
