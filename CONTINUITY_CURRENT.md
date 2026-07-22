# BotA Current Continuity State

Last updated: 2026-07-22

This is the compact current handoff. Historical detail remains in `CONTINUITY.md`, `ERRORS.md`, `audits/ERROR_LOG.md`, `docs/PHASE4_FUNCTIONAL_RECOVERY_2026-07-22.md`, `docs/PHASE5_WATCHER_ROUTING_2026-07-22.md`, and issue #9.

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
4. Reboot and functional recovery proof — **REOPENED BY REPEATED MANAGER LOSS**.
5. Monday readiness and decision-data collection — **BLOCKED**.

Completed: **3/5**. Remaining: **2/5**.

## Control-plane sequence

A Phase 5 baseline first captured a temporary split:

```text
MANAGER_COUNT=1
MANAGER_PID=12712
OWNED=1/7
RUNNING=7/7
ORPHANED=6
```

A later compact snapshot proved same-boot reconvergence:

```text
MANAGER_COUNT=1
MANAGER_PID=24052
OWNED=7/7
RUNNING=7/7
ORPHANED=0
```

The next Gate A check then captured a more severe recurrence:

```text
PHASE5_GATE_A=FAIL
MANAGER_COUNT=0
MANAGER_PID=NONE
OWNED=0/7
RUNNING=6/7
ORPHANED=6
PHASE5_CURRENT_WATCHER_LOG=BLOCKED_OWNERSHIP
RUNTIME_MUTATION_PERFORMED=NO
```

Interpretation:

- the standard `runsvdir $PREFIX/var/service` manager disappeared again during the same boot;
- six surviving `runsv` supervisors are orphaned under PID 1;
- one of seven required services is no longer running;
- this is a real control-plane availability failure, not a watcher-log parser issue;
- Phase 5 must stop before reading logs, CSV, caches, Telegram history, or strategy evidence;
- do not rerun V5 or mutate until one compact resample identifies whether the manager self-recovers and which service is absent/down.

This recurrence is tracked as **E029 — standard manager disappeared after 7/7 reconvergence**. GitHub continuity is updated now. The phone-local `audits/ERROR_LOG.md` remains synchronized only through E028 and must receive E029 later through a separate staged mutation after control-plane stabilization.

## Watcher output routing — VERIFIED BEFORE THE REGRESSION

Before manager loss, the watcher service was manager-owned and running:

```text
WATCHER_ROUTING_PREFLIGHT=PASS
MANAGER_PID=24052
WATCHER_RUNSV_PID=24058
WATCHER_RUNSV_PPID=24052
WATCHER_WRAPPER_PID=24075
```

The service has no runit `log/` subservice. Wrapper stdout/stderr route to `/dev/null`, while the run script explicitly appends service evidence to:

`$HOME/BotA/logs/cron.signals.log`

This routing fact remains valid, but current log reading is blocked until Gate A ownership passes again.

## Local error-log state

The phone and GitHub copies were previously synchronized through E028:

```text
LOCAL_ERROR_LOG_SYNC=PASS
LOCAL_ERROR_LOG_INDEPENDENT_VERIFY=PASS
LOCAL_ERROR_LOG_BLOB=a64143e153511bf43d19607f3521073f693ee0cc
ERROR_RANGE_PRESENT=E022_THROUGH_E028
```

After E029, current state is:

- GitHub continuity: updated through E029;
- GitHub `audits/ERROR_LOG.md`: E029 update pending;
- phone-local `audits/ERROR_LOG.md`: through E028;
- local synchronization must not be mixed with the active manager-loss diagnostic.

## Rejected Phase 5 package conclusions

The oversized Phase 5 package crashed Termux and mixed historical/current evidence. Its log, CSV, cache-age, Telegram-count, and strategy conclusions remain invalid.

## Deferred findings

- durable cause and bounded recovery time for repeated manager replacement/orphaning;
- exact identity of the seventh missing/down service in the current snapshot;
- dead-man time-source and future/negative-age protection;
- stale-reason suppression mismatch;
- canonical crontab verifier/hash mismatch;
- durable calendar guard fix, caching, and call budget;
- Twelve Data budgeting;
- external independent monitoring;
- strategy review only after clean Phase 5 evidence.

## Exactly one next action

Run one compact read-only control-plane resample that reports all `runsvdir` processes, each required service's runsv PID/PPID and `sv status`, and identifies the missing/down service. Do not inspect watcher logs, CSV, or caches.
