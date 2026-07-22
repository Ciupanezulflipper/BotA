# BotA Current Continuity State

Last updated: 2026-07-22

This is the compact current handoff. Historical detail remains in `CONTINUITY.md`. Phase 4 closure evidence is recorded in `docs/PHASE4_FUNCTIONAL_RECOVERY_2026-07-22.md`, but a later Phase 5 baseline exposed a new control-plane regression that reopens Phase 4.

## Operating rules

- Reliability and observability only. Strategy, thresholds, pairs, scoring, SL/TP, filters, PR #7, DeepSource, and Supabase signal semantics remain frozen.
- No direct push to `main`.
- Every Termux package displays `audits/ERROR_LOG.md`, prints `ERROR_LOG_REVIEWED=YES` and `CIRCULAR_ERROR_CHECK=PASS`, uses active paths only, and ends with exactly one next action.
- Mutations require separate staging, approval, execution, rollback, and independent verification.
- Never depend on `/proc/uptime` on this Android build.
- Ship/Android wall time is display-only. Use trusted server/provider UTC for market semantics and monotonic time for same-boot cadence and health.
- Read-only Termux packages must now be compact enough to inspect visually before execution: target under roughly 80 shell lines and one narrow question. Do not combine infrastructure, log parsing, CSV parsing, cache parsing, and strategy evidence in one package.

## Phase state

1. Single execution source and cron hygiene — COMPLETE.
2. Runtime survival controls — COMPLETE.
3. Ship-time safety proof — COMPLETE.
4. Reboot and functional recovery proof — **REOPENED BY REGRESSION**.
5. Monday readiness and decision-data collection — **BLOCKED**.

Completed: **3/5**. Remaining: **2/5**.

## Latest verified regression

The first Phase 5 baseline produced:

```text
PHASE5_DECISION_BASELINE=FAIL_INFRA
MANAGER_COUNT=1
MANAGER_PID=12712
OWNED=1/7
RUNNING=7/7
WRAPPER_CHAIN=7/7
ORPHANED=6
CROND_SUPERVISED=YES
RAPIDAPI_DISABLED=YES
```

Interpretation:

- one new standard manager exists;
- only `bota-updater` is owned by that manager;
- watcher, closer, shadow, heartbeat, supervisor, and crond supervisors are alive under PID 1;
- all seven wrappers still run, so `sv status` alone looks healthy;
- the control plane has again degraded into one manager plus six orphaned supervisors;
- Phase 5 evidence cannot be trusted until ownership is repaired durably.

This is a recurrence of the earlier dead-manager/orphaned-supervisor failure mode. It proves that the prior functional Phase 4 PASS was not durable enough to advance permanently.

## Phase 5 package defects

The Phase 5 baseline itself was too large and crashed Termux. Its data-path conclusions are not authoritative because the package mixed too many concerns and contained parser defects.

Verified parser/audit defects:

- selected `logs/cron.signals.log`, whose parsed cycles were from 2026-07-14 while current cache candles were from 2026-07-22;
- generic pair/timeframe regex misread log tags such as `FILTER 2026` as `FILTER/2026`;
- every cycle therefore appeared to miss `EURUSD/M15` and `GBPUSD/M15`;
- cache ages became negative because old server epochs were compared with current candles;
- `alerts.csv` header/schema assumptions were wrong for the existing file, so `ALERTS_COLUMNS_OK=NO` and persistence `0/12` are not trustworthy;
- historical Telegram counts (`dedup:1683`, `sent:16`) were mixed into a current baseline;
- infrastructure, logs, CSV, cache JSON, and Telegram analysis were combined into one oversized process.

Do not use these Phase 5 parser results to judge strategy restrictiveness or signal generation.

## Correct next workflow

### Gate A — compact ownership snapshot

Only verify:

- boot ID;
- manager PID;
- exact seven runsv PIDs and PPIDs;
- orphan count;
- seven `sv status` results.

### Gate B — ownership repair design

If the same `1/7 owned, 6 orphaned` state persists, design a durable manager-reconciliation mechanism. Do not rerun V5 blindly and do not touch strategy.

### Gate C — Phase 5 restart

Only after one manager owns all seven supervisors again:

1. inspect the current watcher service log only;
2. inspect `alerts.csv` header and last 10 rows only;
3. inspect current cache timestamps only;
4. combine conclusions in analysis, not in one giant Termux script.

## RapidAPI quota mitigation

The runtime containment remains verified:

- `RAPIDAPI_CALENDAR_KEY` is declared once and empty in `.env.runtime`;
- RapidAPI fallback remains disabled;
- persistent `.env` remains unchanged.

## Deferred findings

- durable root cause and prevention for repeated standard-manager replacement;
- dead-man time-source and negative/future-age protection;
- stale-reason suppression mismatch;
- canonical crontab verifier/hash mismatch;
- durable calendar guard fix, caching, and call budget;
- Twelve Data budgeting;
- external independent dead-man monitoring;
- strategy/threshold review only after clean Phase 5 evidence.

## Exactly one next action

Run one compact read-only control-plane ownership snapshot. Do not rerun the Phase 5 data parser and do not mutate runtime state yet.
