# BotA Runtime Checkpoint — 2026-07-20

## Purpose

This document records the verified runtime-control-plane, API-quota, crontab, and observability findings discovered during Phase 4 stabilization. It is the detailed evidence source for `CONTINUITY_CURRENT.md`, `AI_START_HERE.md`, and GitHub issue #9.

## Phase status

- Phase 1 — single execution source and cron hygiene: COMPLETE.
- Phase 2 — runtime survival controls: COMPLETE.
- Phase 3 — ship-time safety proof: COMPLETE.
- Phase 4 — reboot and endurance proof: IN PROGRESS.
  - reboot gate: PASS and closed;
  - endurance/control-plane ownership: FAIL and unresolved.
- Phase 5 — Monday readiness/data collection: NOT STARTED.
- Completed: 3/5.
- Remaining: 2/5.

## Scope lock

Do not change during this reliability incident:

- strategy;
- thresholds;
- pairs;
- scoring;
- SL/TP;
- filters;
- PR #7;
- DeepSource work;
- Supabase signal semantics;
- direct pushes to `main`;
- unrelated cleanup or broad refactors.

## Device and runtime facts

- Runtime: Android 16 / Termux 0.118.3.
- Repository checkout: `/data/data/com.termux/files/home/BotA`.
- Shortcut: `~/BotA`.
- Current verified boot ID: `ae204a40-c3ff-4c4e-abc2-39696b867781`.
- Canonical service root: `$PREFIX/var/service`.
- Correct foreground crond form: `crond -n -s`.
- Ship-time wall clock is not authoritative for trading or freshness decisions.

## Control-plane findings

### Initial new-boot snapshot

The fresh boot audit showed:

- one standard manager:
  - PID 25793;
  - PPID 1;
  - command: `runsvdir $PREFIX/var/service`;
- six BotA `runsv` supervisors orphaned under PID 1:
  - `bota-updater`;
  - `bota-watcher`;
  - `bota-closer`;
  - `bota-shadow`;
  - `bota-heartbeat`;
  - `bota-supervisor`;
- one manager-owned `runsv crond`;
- empty `crond/supervise/pid`;
- one old live orphaned `crond -n -s` under PID 1;
- stable runsv PID sets across three samples.

This proved a split-brain layout rather than a transient PID-file race.

### File-gated crond repair

The V2 file-gated repair was staged at:

`audits/p4_control_plane_reconcile_1bd27eb5_49498/RECONCILE_CROND_SPLIT_BRAIN_V2_FILE_APPROVAL.py`

Pinned repair SHA-256:

`15339b92901508b267e26a31638c237fb481f551af87c6bc0a8acb3440a80876`

Persistent log evidence proves the repair executed:

- `APPROVAL_RESULT=ACCEPTED`;
- accepted challenge: `7C4E91`;
- preflight manager PID 25793;
- manager-owned runsv crond PID 29960;
- old orphaned crond PID 29386;
- idle-boundary proof passed;
- `sv -w 5 down crond` passed;
- SIGTERM sent to PID 29386;
- old crond exited;
- first `sv -w 30 up crond` timed out with rc 111;
- automatic availability recovery started;
- recovery `sv -w 15 up crond` passed;
- supervised crond PID 28296 came up;
- recovery rollback finished successfully.

Conclusion:

- the old detached crond was removed;
- one supervised crond was restored;
- the crond split-brain repair must not be rerun;
- the crond rollback must not be run unless a new verified failure explicitly requires it.

### Post-repair control-plane state

The later forensic snapshot showed:

- `STANDARD_MANAGER_COUNT=0`;
- all six BotA `runsv` supervisors orphaned under PID 1;
- `runsv crond` also orphaned under PID 1;
- one live supervised crond PID 28296.

Current structural blocker:

Restore exactly one standard Termux `runsvdir` manager and migrate all seven stable supervisors beneath it without duplicate wrappers, historical replay, or service-state corruption.

## RapidAPI calendar quota incident

### External warning

The Global Economic Calendar API BASIC subscription reached 100% usage. This creates a real overage or blocking risk depending on the provider's plan behavior.

This is separate from Twelve Data usage. Telegram reported Twelve Data at 600/800 credits.

### Proven active caller

The active caller chain is:

```text
bota-watcher runit service
  -> tools/signal_watcher_pro.sh --once every 900 seconds
  -> tools/calendar_guard.py once per pair path
  -> TradingEconomics guest source
  -> RapidAPI fallback when TradingEconomics returns no events
```

The watcher source contains a misleading comment saying the calendar guard is disabled, but the condition is logically always true whenever `calendar_guard.py` exists:

```bash
if [[ -f "${TOOLS}/calendar_guard.py" && -n "${RAPIDAPI_CALENDAR_KEY:-}" ]] || [[ -f "${TOOLS}/calendar_guard.py" ]]; then
```

Therefore the second clause bypasses the intended key/enable gate.

Additional proof:

- `.env` contains one non-empty `RAPIDAPI_CALENDAR_KEY` declaration;
- `.env.runtime` contains one non-empty declaration;
- recent `cron.signals.log` lines show:
  - `CLEAR: EURUSD safe via rapidapi`;
  - `CLEAR: GBPUSD safe via rapidapi`;
- no active cron line directly calls the calendar guard; the active runit watcher is the caller.

The calendar guard fails open when both providers are unavailable, so blanking the runtime key does not intentionally block all trading. The durable source fix still needs review and testing.

### Immediate runtime-only mitigation

A reversible mitigation was staged at:

`audits/p4_rapidapi_runtime_disable_ae204a40`

Artifacts:

- `DISABLE_RAPIDAPI_CALENDAR_RUNTIME_V1.sh`
  - SHA-256: `29fa5f954a1c4db3438753712d49dc355293c1991099bda713a090203fd67dbb`;
- `ROLLBACK_RAPIDAPI_CALENDAR_RUNTIME_V1.sh`
  - SHA-256: `c4d3efbc90c92dc3866fd0ce8d95052ba34f2f75f6f41f74ebe61237fc0d0bb5`;
- expected `.env.runtime` SHA-256:
  - `794b160586e670d08e6a2c9dd0756b57c08b0f7e719005f1d15918df8ac79f48`;
- expected `.env.runtime` mode: `600`.

Planned effect:

- blank only `RAPIDAPI_CALENDAR_KEY` in `.env.runtime`;
- preserve `.env` unchanged;
- create a mode-600 backup;
- replace `.env.runtime` atomically;
- do not restart services;
- make no API call.

Reason no restart is required:

The runit watcher sources `.env.runtime` on each cycle.

Current evidence boundary:

The user supplied the approval-file creation command, but no returned output yet proves that the approval file was created or that the disable script executed. Do not claim the runtime key is disabled until explicit output proves it.

## Crontab findings

Live crontab SHA-256:

`2fbbf08b8611ae22ecfc08f9d41a078a6a3437fe1ecfcd6ba931f2f1c99b9a68`

Daily Proof reported:

- canonical crontab verification: FAIL;
- hash match: NO.

Observed live structure:

- former watcher, updater, shadow, closer, heartbeat, and supervisor cron entries are commented with `#MIGRATED_TO_RUNIT`;
- no duplicate active execution was proven from those commented lines;
- Daily Proof remains active;
- runtime-health push remains active every five minutes;
- dividend scanner block remains active and separate.

Canonical verification must be rerun after control-plane stabilization. Do not blindly reinstall cron before reconciling current intended runit/cron ownership.

## Telegram and health-truth findings

Observed transitions included:

- `updater_stale`;
- `shadow_stale`;
- dead-man stale;
- later recovery;
- repeated degradation after recovery.

These alerts cannot all be treated as authoritative because the current supervisor still relies partly on wall-clock/file-mtime freshness. Quiet successful cycles can appear stale, and a restart can touch logs and create a false recovery.

Known deferred suppression defect:

- emitted names use forms such as `watcher_stale`, `updater_stale`, and `shadow_stale`;
- the existing suppression regex expects names such as `watcher_log_stale`;
- intended ship-mode suppression is therefore ineffective.

Do not use Telegram recovery alone as proof that the control plane is healthy.

## Workflow and safety corrections

Every Termux package must:

1. display `audits/ERROR_LOG.md` first;
2. print `ERROR_LOG_REVIEWED=YES`;
3. print `CIRCULAR_ERROR_CHECK=PASS`;
4. use active paths only;
5. avoid recursive scans through runit supervise FIFOs;
6. avoid top-level `exit` that closes the user's Termux shell;
7. avoid interactive approval waits;
8. separate staging, approval, and mutation execution;
9. use compact output and avoid repeating broad audits without contradictory evidence;
10. finish with one next action.

## Ordered next steps

1. Prove the RapidAPI disable approval file exists.
2. Execute the already-staged runtime-only RapidAPI disable.
3. Verify the runtime key is empty without making an API request.
4. Reconcile the missing standard `runsvdir` manager and seven orphaned supervisors.
5. Run bounded PID/parentage stability checks and continue the endurance gate.
6. Repair the calendar invocation condition and add caching/call-budget controls on a reviewed source branch.
7. Re-run canonical crontab verification.
8. Repair health-transition truth and stale-reason suppression separately.
9. Address Twelve Data call budgeting separately.

## Deferred findings

- root cause of repeated standard-manager death;
- full seven-service manager reconciliation;
- calendar caching and per-day call budget;
- calendar failure/429 observability;
- canonical crontab mismatch;
- health model based on monotonic useful progress;
- stale-reason suppression mismatch;
- Twelve Data quota budgeting;
- external independent dead-man monitoring.
