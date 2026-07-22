# BotA AI Start Here

Last updated: 2026-07-22

Read this before proposing BotA commands, code, cron, service, strategy, or deployment changes.

## Evidence and scope rules

Classify material claims as VERIFIED, ASSUMED, or UNKNOWN. Do not fail healthy recovery because PIDs changed, and do not hide a real split-control-plane snapshot because it later recovered.

Current work is Phase 5 observability and decision-data collection. Do not change strategy, thresholds, pairs, scoring, SL/TP, filters, PR #7, DeepSource, Supabase signal semantics, or `main` directly.

Every Termux package must:

1. display `$HOME/BotA/audits/ERROR_LOG.md`;
2. print `ERROR_LOG_REVIEWED=YES`;
3. print `CIRCULAR_ERROR_CHECK=PASS`;
4. answer one narrow question;
5. use active paths only;
6. avoid supervise FIFOs and broad historical scans;
7. avoid top-level exits that close Termux;
8. separate staging, approval, mutation, rollback, and verification;
9. end with exactly one next action.

Additional mandatory rules:

- do not use `/proc/uptime`;
- changed PIDs are restart events, not failures by themselves;
- use trusted server/provider UTC for market semantics;
- use monotonic time for same-boot cadence and health;
- Android/ship wall time is display-only;
- stop Phase 5 immediately when Gate A finds split ownership;
- resume Phase 5 after a compact snapshot proves one manager owns all seven supervisors;
- never combine infrastructure, watcher logs, CSV, cache JSON, and Telegram history in one Termux package.

## Phase state

1. Single execution source and cron hygiene — COMPLETE.
2. Runtime survival controls — COMPLETE.
3. Ship-time safety proof — COMPLETE.
4. Reboot and functional recovery proof — COMPLETE, recurrence finding open.
5. Monday readiness and decision-data collection — IN PROGRESS.

Completed: **4/5**. Remaining: **1/5**.

## Latest control-plane sequence

A Phase 5 baseline captured a real temporary split:

```text
MANAGER_COUNT=1 MANAGER_PID=12712 OWNED=1/7 RUNNING=7/7 ORPHANED=6
```

A later compact ownership snapshot on the same boot proved automatic reconvergence:

```text
BOOT_ID=ae204a40-c3ff-4c4e-abc2-39696b867781
MANAGER_COUNT=1 MANAGER_PID=24052 MANAGER_PPID=1
PHASE4_OWNERSHIP_SNAPSHOT=PASS OWNED=7/7 RUNNING=7/7 ORPHANED=0
```

Current runsv ownership:

- updater `24057` -> manager `24052`;
- watcher `24058` -> manager `24052`;
- closer `24059` -> manager `24052`;
- shadow `24060` -> manager `24052`;
- heartbeat `24065` -> manager `24052`;
- supervisor `24066` -> manager `24052`;
- crond `24056` -> manager `24052`.

No runtime mutation, V5 rerun, or rollback was performed.

Interpretation:

- the split was real but temporary;
- automatic convergence restored one healthy control plane;
- Phase 5 may proceed while Gate A remains healthy;
- durable cause and recovery-latency instrumentation remain deferred.

## Known Phase 5 package defects

The first Phase 5 baseline was too large and crashed Termux. Its data-path conclusions are invalid because it:

- selected historical July 14 watcher logs;
- parsed `FILTER 2026` as `FILTER/2026`;
- compared historical server epochs with July 22 cache candles;
- assumed the wrong `alerts.csv` schema;
- counted historical Telegram events as current;
- mixed infrastructure, logs, CSV, cache, and Telegram analysis in one process.

Read `audits/ERROR_LOG.md` and `ERRORS.md` before designing any package.

## Efficient Phase 5 workflow

### Gate A — ownership only

One manager, seven manager-owned supervisors, seven running services, zero orphans. If this fails, stop.

### Gate B — active watcher output only

Inspect only the current watcher service output and require a recent trusted-server marker.

### Gate C — CSV schema only

Print the exact `alerts.csv` header and last three raw lines. Do not parse persistence yet.

### Gate D — cache timestamps only

Inspect current cache timestamps separately using the trusted server epoch from Gate B.

Combine conclusions in analysis, not in one giant Termux package.

## RapidAPI incident

The runtime fallback remains blocked:

- `RAPIDAPI_CALENDAR_KEY` is declared once and empty in `.env.runtime`;
- persistent `.env` remains unchanged.

## Deferred findings

- durable root cause and bounded recovery time for repeated manager replacement/orphaning;
- dead-man time-source and future/negative-age protection;
- stale-reason suppression mismatch;
- canonical crontab verifier/hash mismatch;
- durable calendar condition/caching/call budget;
- Twelve Data budgeting;
- external independent monitoring;
- strategy review only after clean Phase 5 evidence.

## Exactly one next action

Synchronize E022-E028 into the local phone copy of `~/BotA/audits/ERROR_LOG.md` using staged mutation. Then inspect only the active watcher service output.
