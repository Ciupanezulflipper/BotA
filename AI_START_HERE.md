# BotA AI Start Here

Last updated: 2026-07-22

Read this before proposing BotA commands, code, cron, service, strategy, or deployment changes.

## Evidence and scope rules

Classify material claims as VERIFIED, ASSUMED, or UNKNOWN. Do not promote a failed acceptance criterion because adjacent behavior worked, and do not fail a healthy recovery because process IDs changed.

Current work is Phase 5 observability and decision-data collection. Do not change strategy, thresholds, pairs, scoring, SL/TP, filters, PR #7, DeepSource, Supabase signal semantics, or `main` directly.

Every Termux package must:

1. display `$HOME/BotA/audits/ERROR_LOG.md`;
2. print `ERROR_LOG_REVIEWED=YES`;
3. print `CIRCULAR_ERROR_CHECK=PASS`;
4. use compact active-path checks;
5. avoid supervise FIFOs and broad historical scans;
6. avoid top-level exits that close Termux;
7. avoid blocking interactive approval;
8. separate staging, approval, mutation, rollback, and verification;
9. end with exactly one next action.

Additional mandatory rules:

- do not use `/proc/uptime` on this Android build;
- changed PIDs are restart events, not failures by themselves;
- use trusted server/provider UTC for market semantics;
- use monotonic time for same-boot cadence and health;
- Android/ship wall time is display-only;
- when one correctly owned service child is absent, take one targeted bounded recovery sample before proposing mutation;
- do not rerun V5 or a broad seven-service repair while one-manager ownership remains healthy;
- read-only packages must answer one narrow question and remain compact enough to inspect visually;
- never combine infrastructure, watcher logs, CSV, cache JSON, Telegram history, and strategy conclusions in one Termux package.

## Phase state

1. Single execution source and cron hygiene — COMPLETE.
2. Runtime survival controls — COMPLETE.
3. Ship-time safety proof — COMPLETE.
4. Reboot and functional recovery proof — COMPLETE, with recurrence finding open.
5. Monday readiness and decision-data collection — IN PROGRESS.

Completed: **4/5**. Remaining: **1/5**.

## Current control plane

The first Phase 5 package captured a temporary split:

```text
MANAGER_COUNT=1
MANAGER_PID=12712
OWNED=1/7
RUNNING=7/7
ORPHANED=6
```

A later compact snapshot proved automatic reconvergence on the same boot:

```text
BOOT_ID=ae204a40-c3ff-4c4e-abc2-39696b867781
MANAGER_COUNT=1
MANAGER_PID=24052
PHASE4_OWNERSHIP_SNAPSHOT=PASS
OWNED=7/7
RUNNING=7/7
ORPHANED=0
```

Current supervisor ownership at that snapshot:

- updater `24057 -> 24052`;
- watcher `24058 -> 24052`;
- closer `24059 -> 24052`;
- shadow `24060 -> 24052`;
- heartbeat `24065 -> 24052`;
- supervisor `24066 -> 24052`;
- crond `24056 -> 24052`.

The split was real but temporary. Do not erase the recurrence and do not keep Phase 5 blocked after verified 7/7 reconvergence. Gate A ownership must pass before every later Phase 5 package.

## Local error-log state

The phone and GitHub copies of `audits/ERROR_LOG.md` are synchronized.

Verified:

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

`$HOME/BotA/audits/local_error_log_sync_e016_e028/ERROR_LOG.before.md`

Rollback is available but not required.

## Phase 5 package defects that must not recur

- the original package was too large and crashed Termux;
- it selected historical July 14 watcher output as current evidence;
- generic regex parsed `FILTER 2026` as `FILTER/2026`;
- historical server epochs were compared with July 22 candles;
- `alerts.csv` schema was assumed before inspection;
- historical Telegram totals were presented as current.

Those data-path conclusions are invalid and may not be used to judge the strategy.

## Efficient Phase 5 workflow

### Gate A — control-plane snapshot

Verify one manager, seven manager-owned runsv supervisors, seven running services, and zero orphans. Stop if it fails.

### Gate B — current watcher evidence only

Inspect only the active watcher service output. Require a recent trusted-server marker. Do not search all logs and do not choose the file with the most markers.

### Gate C — CSV schema only

Print the exact `logs/alerts.csv` header and last three raw rows. Do not parse persistence yet.

### Gate D — cache timestamps only

Inspect current EURUSD/GBPUSD M15 cache timestamps separately and compare them only with the recent trusted-server epoch from Gate B.

Combine the conclusions in analysis, not in a single giant device package.

## RapidAPI incident

The calendar fallback leak remains blocked at runtime:

- `RAPIDAPI_CALENDAR_KEY` is declared once and empty in `.env.runtime`;
- future watcher cycles cannot use the RapidAPI fallback;
- persistent `.env` is unchanged.

The durable source-condition fix, caching, daily call budget, and Twelve Data quota work remain deferred.

## Deferred findings

- durable root cause and bounded recovery time for repeated manager replacement/orphaning;
- dead-man time-source and future/negative-age protection;
- stale-reason suppression mismatch;
- canonical crontab verification/hash mismatch;
- durable calendar source condition and caching;
- Twelve Data budgeting;
- external independent dead-man monitoring;
- strategy review only after clean Phase 5 evidence.

## Files to read

- `CONTINUITY_CURRENT.md`
- `audits/ERROR_LOG.md`
- `ERRORS.md`
- `docs/PHASE4_FUNCTIONAL_RECOVERY_2026-07-22.md`
- `docs/RUNTIME_HANDOFF_V5_RESULT_2026-07-20.md`
- GitHub issue #9
- draft PR #10

## Exactly one next action

Run one compact read-only current-watcher-service evidence check. Do not inspect CSV or caches in that package.
