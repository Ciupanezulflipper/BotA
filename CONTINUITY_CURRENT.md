# BotA Current Continuity State

Last updated: 2026-07-22

This is the compact current handoff. Historical detail remains in `CONTINUITY.md`, `ERRORS.md`, `audits/ERROR_LOG.md`, `docs/PHASE4_FUNCTIONAL_RECOVERY_2026-07-22.md`, and issue #9.

## Operating rules

- Reliability and observability only. Strategy, thresholds, pairs, scoring, SL/TP, filters, PR #7, DeepSource, and Supabase signal semantics remain frozen.
- No direct push to `main`.
- Every Termux package displays `audits/ERROR_LOG.md`, prints `ERROR_LOG_REVIEWED=YES` and `CIRCULAR_ERROR_CHECK=PASS`, uses active paths only, and ends with exactly one next action.
- Read-only packages answer one narrow question and remain compact enough to inspect before execution.
- Never combine infrastructure, watcher-log, CSV, cache, Telegram-history, and strategy analysis in one package.
- Never depend on `/proc/uptime` on this Android build.
- Trusted server/provider UTC controls market semantics; monotonic time controls same-boot cadence and health; Android/ship wall time is display-only.

## Phase state

1. Single execution source and cron hygiene — COMPLETE.
2. Runtime survival controls — COMPLETE.
3. Ship-time safety proof — COMPLETE.
4. Reboot and functional recovery proof — COMPLETE, with recurrence finding open.
5. Monday readiness and decision-data collection — IN PROGRESS.

Completed: **4/5**. Remaining: **1/5**.

## Current control plane

A Phase 5 baseline captured a real temporary split:

```text
MANAGER_COUNT=1
MANAGER_PID=12712
OWNED=1/7
RUNNING=7/7
ORPHANED=6
```

A later compact snapshot proved automatic same-boot reconvergence:

```text
BOOT_ID=ae204a40-c3ff-4c4e-abc2-39696b867781
MANAGER_COUNT=1
MANAGER_PID=24052
OWNED=7/7
RUNNING=7/7
ORPHANED=0
```

No V5 rerun, rollback, restart, or runtime mutation was required. Gate A ownership must pass before every later Phase 5 data package.

## Local error-log synchronization

The phone and GitHub copies of `audits/ERROR_LOG.md` are synchronized through E028:

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

## Phase 5 package defects already rejected

The original Phase 5 package was too large and crashed Termux. Its data-path conclusions are invalid because it:

- selected historical 2026-07-14 watcher data as current evidence;
- parsed `FILTER 2026` as `FILTER/2026`;
- compared historical server epochs with 2026-07-22 candles;
- assumed the `alerts.csv` schema before inspecting it;
- counted historical Telegram totals as current behavior.

Do not use those results to judge strategy restrictiveness or signal generation.

## Gate B watcher-output routing — VERIFIED

The watcher service remains healthy and manager-owned:

```text
WATCHER_ROUTING_PREFLIGHT=PASS
MANAGER_PID=24052
WATCHER_RUNSV_PID=24058
WATCHER_RUNSV_PPID=24052
WATCHER_WRAPPER_PID=24075
WATCHER_STATUS=run
```

The service has no runit `log/` subservice. The wrapper and current sleep child both have stdout and stderr connected to `/dev/null`:

```text
PROCESS_FD1=/dev/null
PROCESS_FD2=/dev/null
WATCHER_OUTPUT_ROUTING=DEV_NULL
```

This is not evidence loss by itself. The run script explicitly defines:

```bash
LOG="${ROOT}/logs/cron.signals.log"
log() { printf ... | tee -a "${LOG}"; }
```

Therefore the authoritative watcher evidence candidate is the exact file:

`$HOME/BotA/logs/cron.signals.log`

The earlier mistake was treating historical content from that file as current, not identifying the file itself. Current evidence must be taken only from a small tail and anchored by the latest trusted-server marker.

This routing finding is not classified as E029 because the explicit file-log path is intentional. It becomes an error only if that exact file is absent, not advancing, or lacks current-cycle evidence.

## Compact Phase 5 workflow

1. **Gate A:** one manager, seven manager-owned supervisors, seven running services, zero orphans.
2. **Gate B:** read only a small tail of the exact watcher log and identify the latest trusted-server marker and current EURUSD/GBPUSD outcomes.
3. **Gate C:** print only the exact `alerts.csv` header and last three raw rows.
4. **Gate D:** inspect only current cache timestamps and compare them with the Gate B trusted-server epoch.
5. Combine conclusions outside Termux, not inside one large device package.

## RapidAPI containment

`RAPIDAPI_CALENDAR_KEY` remains declared once and empty in `.env.runtime`. Persistent `.env` is unchanged. Durable source-condition, caching, and call-budget work remain deferred.

## Deferred findings

- durable cause and bounded recovery time for repeated manager replacement/orphaning;
- dead-man time-source and future/negative-age protection;
- stale-reason suppression mismatch;
- canonical crontab verifier/hash mismatch;
- durable calendar guard fix, caching, and call budget;
- Twelve Data budgeting;
- external independent monitoring;
- strategy review only after clean Phase 5 evidence.

## Exactly one next action

Run one compact read-only tail of `$HOME/BotA/logs/cron.signals.log`, after Gate A, and return only current trusted-clock and EURUSD/GBPUSD evidence. Do not inspect CSV or caches in the same package.
