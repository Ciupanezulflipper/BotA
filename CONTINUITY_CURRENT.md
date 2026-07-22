# BotA Current Continuity State

Last updated: 2026-07-22

This is the compact current handoff. Historical detail remains in `CONTINUITY.md`. Phase 4 closure evidence is recorded in `docs/PHASE4_FUNCTIONAL_RECOVERY_2026-07-22.md`. A later Phase 5 baseline exposed a temporary split control plane, and the subsequent compact ownership snapshot proved automatic reconvergence.

## Operating rules

- Reliability and observability only. Strategy, thresholds, pairs, scoring, SL/TP, filters, PR #7, DeepSource, and Supabase signal semantics remain frozen.
- No direct push to `main`.
- Every Termux package displays `audits/ERROR_LOG.md`, prints `ERROR_LOG_REVIEWED=YES` and `CIRCULAR_ERROR_CHECK=PASS`, uses active paths only, and ends with exactly one next action.
- Mutations require separate staging, approval, execution, rollback, and independent verification.
- Never depend on `/proc/uptime` on this Android build.
- Ship/Android wall time is display-only. Use trusted server/provider UTC for market semantics and monotonic time for same-boot cadence and health.
- Read-only Termux packages must answer one narrow question and remain compact enough to inspect visually before execution. Do not combine infrastructure, log parsing, CSV parsing, cache parsing, and strategy evidence in one package.

## Phase state

1. Single execution source and cron hygiene — COMPLETE.
2. Runtime survival controls — COMPLETE.
3. Ship-time safety proof — COMPLETE.
4. Reboot and functional recovery proof — COMPLETE, with recurrence finding open.
5. Monday readiness and decision-data collection — IN PROGRESS.

Completed: **4/5**. Remaining: **1/5**.

## Latest control-plane sequence

The first Phase 5 baseline captured a real transient split:

```text
MANAGER_COUNT=1
MANAGER_PID=12712
OWNED=1/7
RUNNING=7/7
WRAPPER_CHAIN=7/7
ORPHANED=6
```

A subsequent compact ownership snapshot showed automatic reconvergence on the same boot:

```text
BOOT_ID=ae204a40-c3ff-4c4e-abc2-39696b867781
MANAGER_COUNT=1
MANAGER_PID=24052
MANAGER_PPID=1
PHASE4_OWNERSHIP_SNAPSHOT=PASS
OWNED=7/7
RUNNING=7/7
ORPHANED=0
```

Current service ownership:

- updater runsv PID `24057`, PPID `24052`;
- watcher runsv PID `24058`, PPID `24052`;
- closer runsv PID `24059`, PPID `24052`;
- shadow runsv PID `24060`, PPID `24052`;
- heartbeat runsv PID `24065`, PPID `24052`;
- supervisor runsv PID `24066`, PPID `24052`;
- crond runsv PID `24056`, PPID `24052`.

Interpretation:

- the split was real, not a parser artifact;
- the control plane later converged automatically to one manager with all seven supervisors;
- no runtime mutation, V5 rerun, or rollback was required;
- Phase 5 may proceed only through compact Gate A checks before each data-path package;
- durable root cause and recovery-latency instrumentation remain open findings, but they do not block the current healthy snapshot.

## Phase 5 baseline package defects

The original Phase 5 baseline was too large and crashed Termux. Its data-path conclusions are not authoritative because it mixed too many concerns and contained parser defects.

Verified defects:

- selected historical `logs/cron.signals.log` cycles from 2026-07-14 while cache candles were from 2026-07-22;
- generic regex misread `FILTER 2026` as `FILTER/2026`;
- cache ages became negative;
- `alerts.csv` schema assumptions were not validated;
- historical Telegram totals were treated as current;
- infrastructure, logs, CSV, cache JSON, and Telegram analysis were combined in one oversized process.

Do not use those results to judge strategy restrictiveness or signal generation.

## Correct Phase 5 workflow

### Gate A — compact ownership snapshot

Before each Phase 5 data package, verify one manager, seven manager-owned runsv supervisors, seven running services, and zero orphans. If this fails, stop.

### Gate B — current watcher evidence only

Inspect only the active watcher service output and require a recent trusted-server marker. Do not search for the log with the most marker strings.

### Gate C — CSV schema only

Print only the exact `alerts.csv` header and last three raw rows before designing any parser.

### Gate D — cache timestamps only

Inspect current cache timestamps separately, using the trusted server epoch from Gate B.

Combine conclusions in analysis, not in one giant Termux package.

## Local error-log synchronization

The phone copy and GitHub copy of `audits/ERROR_LOG.md` are synchronized.

Verified execution markers:

```text
LOCAL_ERROR_LOG_SYNC=PASS
LOCAL_ERROR_LOG_INDEPENDENT_VERIFY=PASS
LOCAL_ERROR_LOG_BLOB=a64143e153511bf43d19607f3521073f693ee0cc
ERROR_RANGE_PRESENT=E022_THROUGH_E028
BACKUP_PRESENT=YES
RUNTIME_SERVICES_CHANGED=NO
STRATEGY_CHANGED=NO
ROLLBACK_REQUIRED=NO
```

Backup:

`/data/data/com.termux/files/home/BotA/audits/local_error_log_sync_e016_e028/ERROR_LOG.before.md`

Rollback script remains available but is not required.

## RapidAPI quota mitigation

The runtime containment remains verified:

- `RAPIDAPI_CALENDAR_KEY` is declared once and empty in `.env.runtime`;
- RapidAPI fallback remains disabled;
- persistent `.env` remains unchanged.

## Deferred findings

- durable root cause and bounded recovery time for repeated manager replacement/orphaning;
- dead-man time-source and negative/future-age protection;
- stale-reason suppression mismatch;
- canonical crontab verifier/hash mismatch;
- durable calendar guard fix, caching, and call budget;
- Twelve Data budgeting;
- external independent monitoring;
- strategy/threshold review only after clean Phase 5 evidence.

## Exactly one next action

Run one compact read-only current-watcher-service evidence check. Do not inspect CSV or caches in the same package.
